"""Loopback-only synthetic fixture server; never part of production URLs/settings."""
import argparse
import importlib
import json
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server


class FixtureServer(WSGIServer):
    request_queue_size = 64


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--state-dir', required=True, type=Path)
    args = parser.parse_args()
    scratch, state = args.scratch.resolve(), args.state_dir.resolve()
    if state == scratch or not state.is_relative_to(scratch):
        parser.error('State must be task-owned under the permitted scratch directory')
    state.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    os.chdir(Path(__file__).resolve().parents[2])
    old_temp = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='deksi-engine-http-', dir=scratch) as directory:
        owned = Path(directory)
        for key in ('TMPDIR', 'TMP', 'TEMP', 'HERMES_TEST_SCRATCH'):
            os.environ[key] = directory
        tempfile.tempdir = directory
        try:
            os.environ.pop('DJANGO_SETTINGS_MODULE', None)
            os.environ['DEKSI_TEST_DATABASE'] = ':memory:'
            os.environ['DEKSI_TEST_RAW_ROOT'] = str(owned / 'raw')
            baseline = importlib.import_module('backend.test_settings_indicators')
            options = {key: getattr(baseline, key) for key in dir(baseline) if key.isupper()}
            options.update(INSTALLED_APPS=[*baseline.INSTALLED_APPS, 'admin_auth'],
                DEKSI_RAW_DIR=owned / 'raw', DEKSI_SCRAPING_DIR=str(owned / 'scraping'))
            from django.conf import settings
            settings.configure(**options)
            with patch('socket.socket.connect', side_effect=AssertionError('No outbound network in fixture server')):
                import django
                django.setup()
                from django.core.management import call_command
                from django.core.wsgi import get_wsgi_application
                from django.db import connections
                from django.test import Client
                from indicators.tests.test_economic_engine import EconomicEngineTests
                call_command('migrate', interactive=False, verbosity=0)
                fixture = EconomicEngineTests()
                fixture.setUp()
                try:
                    fixture.source.source_name = fixture.source.institution = 'SYNTHETIC QA ONLY'
                    fixture.source.primary_url = 'https://example.test'
                    fixture.source.save(update_fields=['source_name', 'institution', 'primary_url'])
                    values = {'pdb_nominal': '1000', 'pmtb_nominal': '300', 'konsumsi_rumah_tangga': '550'}
                    rows = {code: fixture.row(code, value) for code, value in values.items()}
                    original_raw = {code: row.raw_file_id for code, row in rows.items()}
                    mode = 'ready'
                    (state / 'fixture.json').write_text(json.dumps(Client().get('/api/economic-engine/gdp/').json()), encoding='utf-8')
                    application = get_wsgi_application()

                    def respond(start_response, body, status='200 OK'):
                        data = json.dumps(body).encode()
                        start_response(status, [('Content-Type', 'application/json'), ('Cache-Control', 'no-store'),
                            ('Content-Length', str(len(data)))])
                        return [data]

                    def app(environ, start_response):
                        nonlocal mode
                        path = environ.get('PATH_INFO', '')
                        if path == '/__engine_qa/mode':
                            choice = parse_qs(environ.get('QUERY_STRING', '')).get('name', [''])[0]
                            if choice not in {'ready', 'zero', 'changed', 'raw-missing', 'pending', 'empty', 'error', 'malformed'}:
                                return respond(start_response, {'error': 'Unknown synthetic mode'}, '400 Bad Request')
                            for code, row in rows.items():
                                row.value, row.raw_file_id, row.validation_status = Decimal(values[code]), original_raw[code], 'published'
                                row.save(update_fields=['value', 'raw_file', 'validation_status'])
                            component = rows['pmtb_nominal']
                            if choice in {'zero', 'changed'}:
                                component.value = Decimal('0' if choice == 'zero' else '310')
                                component.save(update_fields=['value'])
                                fixture.bind_raw(component)
                            elif choice == 'raw-missing':
                                component.raw_file_id = None
                                component.save(update_fields=['raw_file'])
                            elif choice in {'pending', 'empty'}:
                                row = rows['pdb_nominal'] if choice == 'empty' else component
                                row.validation_status = 'pending'
                                row.save(update_fields=['validation_status'])
                            mode = choice
                            return respond(start_response, {'mode': mode, 'synthetic': True})
                        if path == '/api/economic-engine/gdp/' and mode == 'error':
                            return respond(start_response, {'error': 'Synthetic HTTP failure'}, '503 Service Unavailable')
                        if path == '/api/economic-engine/gdp/' and mode == 'malformed':
                            body = Client().get(path).json()
                            body['metrics']['pmtb_share']['available'] = 'malformed test value'
                            return respond(start_response, body)
                        return application(environ, start_response)

                    with make_server('127.0.0.1', 0, app, server_class=FixtureServer, handler_class=QuietHandler) as server:
                        server.timeout = 0.2
                        (state / 'backend.json').write_text(json.dumps({'port': server.server_port, 'synthetic': True}), encoding='utf-8')
                        print(json.dumps({'port': server.server_port, 'synthetic': True}), flush=True)
                        while not (state / 'stop').exists():
                            server.handle_request()
                finally:
                    fixture.doCleanups()
                    connections.close_all()
        finally:
            tempfile.tempdir = old_temp
    (state / 'backend-cleanup.json').write_text(json.dumps({'ownedDirectoryRemoved': not owned.exists(),
        'database': 'disposable in-memory SQLite', 'providerCallsAllowed': False}), encoding='utf-8')


if __name__ == '__main__':
    main()
