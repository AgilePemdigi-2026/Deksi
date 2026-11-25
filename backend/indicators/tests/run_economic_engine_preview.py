"""Read-only, one-hour loopback preview of the archived real BPS sample."""
import argparse
import hashlib
import importlib
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server


class PreviewServer(WSGIServer):
    request_queue_size = 64


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--capture-dir', type=Path, required=True)
    parser.add_argument('--narrative-dir', type=Path)
    parser.add_argument('--engine-snapshot', type=Path)
    args = parser.parse_args()
    scratch, state, capture = args.scratch.resolve(), args.state_dir.resolve(), args.capture_dir.resolve()
    backend = Path(__file__).resolve().parents[2]
    if state == scratch or not state.is_relative_to(scratch) or not scratch.is_dir():
        parser.error('An owned state directory under permitted scratch is required')
    expected_parent = (backend / 'docs/bps-economic-inputs').resolve()
    if capture.parent != expected_parent or not capture.name.startswith('live-q1-2025-'):
        parser.error('Use the approved archived Q1 2025 capture, not an arbitrary input path')
    state.mkdir(exist_ok=False)
    source = json.loads((capture / 'selected-inputs.json').read_text(encoding='utf-8'))
    prior = json.loads((capture / 'evaluation-receipt.json').read_text(encoding='utf-8'))
    if prior['status'] != 'passed_single_real_quarter_technical_validation':
        parser.error('The source capture has not passed its original technical evaluation')
    points = {row['code']: row for row in source['observations']}
    if set(points) != {'pdb_nominal', 'pmtb_nominal', 'konsumsi_rumah_tangga'}:
        parser.error('Exactly the three approved GDP inputs are required')
    content = {}
    for code, point in points.items():
        expected_name = f'excerpt-{code}.json'
        if point['excerpt'] != expected_name:
            parser.error('Unexpected excerpt path')
        file = (capture / expected_name).resolve()
        if not file.is_relative_to(capture):
            parser.error('Excerpt escapes capture directory')
        content[code] = file.read_bytes()
        if hashlib.sha256(content[code]).hexdigest() != point['excerptSha256']:
            parser.error('Archived excerpt no longer matches its captured checksum')
    sys.path.insert(0, str(backend))
    saved_packet, narrative_payload, saved_review_time = None, None, None
    if args.narrative_dir or args.engine_snapshot:
        if not (args.narrative_dir and args.engine_snapshot):
            parser.error('Narrative directory and exact engine snapshot must be supplied together')
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        saved_packet, narrative_payload, saved_review_time = load_preview_narrative(
            args.narrative_dir.resolve(), args.engine_snapshot.resolve())
    os.chdir(backend)
    previous_temp = tempfile.tempdir
    owned = None
    try:
        with tempfile.TemporaryDirectory(prefix='deksi-real-preview-raw-', dir=scratch) as directory:
            owned = Path(directory)
            for name in ('TMPDIR', 'TMP', 'TEMP', 'HERMES_TEST_SCRATCH'):
                os.environ[name] = directory
            tempfile.tempdir = directory
            os.environ.pop('DJANGO_SETTINGS_MODULE', None)
            os.environ['DEKSI_TEST_DATABASE'] = ':memory:'
            os.environ['DEKSI_TEST_RAW_ROOT'] = str(owned / 'raw')
            baseline = importlib.import_module('backend.test_settings_indicators')
            options = {name: getattr(baseline, name) for name in dir(baseline) if name.isupper()}
            options.update(INSTALLED_APPS=[*baseline.INSTALLED_APPS, 'admin_auth'],
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
                BPS_API_KEY='', DEKSI_RAW_DIR=owned / 'raw', DEKSI_SCRAPING_DIR=str(owned / 'scraping'))
            from django.conf import settings
            settings.configure(**options)
            with patch('socket.socket.connect', side_effect=AssertionError('Preview has no outbound network')):
                import django
                django.setup()
                from django.core.management import call_command
                from django.core.wsgi import get_wsgi_application
                from django.db import connections
                from django.test import Client
                from django.utils import timezone as django_timezone
                from indicators import bps
                from indicators.storage import save_raw
                from indicators.tests.test_economic_engine import EconomicEngineTests
                call_command('migrate', interactive=False, verbosity=0)
                fixture = EconomicEngineTests()
                fixture.setUp()
                try:
                    for name, value in bps.BPS_SOURCE_DEFAULTS.items():
                        setattr(fixture.source, name, value)
                    fixture.source.save(update_fields=list(bps.BPS_SOURCE_DEFAULTS))
                    fixture.reviewer.is_active = False
                    fixture.reviewer.username = 'preview-only-not-human-approval'
                    fixture.reviewer.save(update_fields=['is_active', 'username'])
                    rows = []
                    for code, point in points.items():
                        raw, _ = save_raw(fixture.source, content[code], f'captured-bps-q1-2025-{code}.json')
                        raw.retrieved_at = datetime.fromisoformat(source['retrievedAt'])
                        raw.save(update_fields=['retrieved_at'])
                        indicator = fixture.indicators[code]
                        indicator.name = bps.BPS_ECONOMIC_SERIES[code]['name']
                        indicator.save(update_fields=['name'])
                        rows.append(fixture.row(code, point['value'], raw_file=raw, publication_date=None,
                            validation_status='pending', reviewed_by=None, reviewed_at=None))
                    client = Client()
                    endpoint = '/api/economic-engine/gdp/?quarter=2025-03-31'
                    assert all(not metric['available'] for metric in client.get(endpoint).json()['metrics'].values())
                    # Replay only the original SIMULATED review clock, never record human approval.
                    reviewed_at = datetime.fromisoformat(saved_review_time) if saved_review_time else django_timezone.now()
                    for row in rows:
                        row.validation_status, row.reviewed_by, row.reviewed_at = 'published', fixture.reviewer, reviewed_at
                        row.save(update_fields=['validation_status', 'reviewed_by', 'reviewed_at'])
                    packet = client.get(endpoint).json()
                    if saved_packet is not None and packet != saved_packet:
                        raise ValueError('Reconstructed engine differs from the narrative snapshot; refusing stale prose')
                    for metric_id, expected in prior['resultsPercent'].items():
                        metric = packet['metrics'][metric_id]
                        assert metric['available'] and metric['value'] == expected
                        assert metric['revisionStatus'] == 'unknown' and 'angka dapat direvisi' in metric['revisionNote']
                    context = {'realSourceNumbers': True, 'workflowStateSimulated': True, 'humanApproval': False,
                        'productionPublication': False, 'quarter': 'Q1 2025', 'capturedAt': source['retrievedAt'],
                        'catalogueNote': 'Katalog capture: data 2025 angka sangat sementara.',
                        'scope': 'Local preview only; other dashboard indicators can be unavailable.',
                        'hasNarrativePreview': narrative_payload is not None,
                        'expiresAt': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
                    (state / 'preview-api-packet.json').write_text(json.dumps({'previewContext': context, 'enginePacket': packet}, indent=2), encoding='utf-8')
                    application = get_wsgi_application()

                    def respond(start_response, payload, status='200 OK'):
                        body = json.dumps(payload).encode()
                        start_response(status, [('Content-Type', 'application/json'), ('Cache-Control', 'no-store'),
                            ('Content-Length', str(len(body)))])
                        return [body]

                    def app(environ, start_response):
                        path = environ.get('PATH_INFO', '')
                        if environ.get('REQUEST_METHOD') not in {'GET', 'HEAD'}:
                            return respond(start_response, {'error': 'This isolated preview is read-only'}, '405 Method Not Allowed')
                        if path == '/api/preview-context/':
                            return respond(start_response, context)
                        if path == '/api/preview-engine-narrative/' and narrative_payload is not None:
                            return respond(start_response, narrative_payload)
                        if not (path.startswith('/api/indicators/') or path in {
                                '/api/economic-engine/gdp/', '/api/economic-engine/trade/', '/api/feedback/categories/'}):
                            return respond(start_response, {'error': 'Route outside preview scope'}, '404 Not Found')
                        return application(environ, start_response)

                    with make_server('127.0.0.1', 0, app, server_class=PreviewServer, handler_class=QuietHandler) as server:
                        server.timeout = 0.2
                        runtime = {**context, 'backendOrigin': f'http://127.0.0.1:{server.server_port}', 'pid': os.getpid()}
                        (state / 'backend-runtime.json').write_text(json.dumps(runtime, indent=2), encoding='utf-8')
                        print(json.dumps(runtime), flush=True)
                        deadline = time.monotonic() + 3600
                        while time.monotonic() < deadline and not (state / 'stop').exists():
                            server.handle_request()
                finally:
                    fixture.doCleanups()
                    connections.close_all()
    finally:
        tempfile.tempdir = previous_temp
        (state / 'cleanup.json').write_text(json.dumps({'ownedRawDirectoryRemoved': owned is None or not owned.exists(),
            'database': 'disposable in-memory SQLite'}), encoding='utf-8')


if __name__ == '__main__':
    main()
