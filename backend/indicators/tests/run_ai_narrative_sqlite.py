"""Explicit offline backend QA: existing interpreter, disposable SQLite, no app server."""
import argparse
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

TEST_LABELS = (
    'indicators.tests.test_ai_narrative',
    'indicators.tests.test_ai_narrative_provider',
    'indicators.tests.test_ai_facts',
    'indicators.tests.test_detail_api',
    'indicators.tests.test_source_trace',
    'indicators.tests.test_dashboard_api',
    'indicators.tests.test_raw_storage',
    'indicators.tests.test_exact_value.ExactValueTests',
    'indicators.tests.test_bps_economic_inputs_contract',
    'indicators.tests.test_candidate_review_api',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--scratch', required=True, type=Path)
    args = parser.parse_args()
    if not args.scratch.is_absolute() or not args.scratch.is_dir():
        parser.error('--scratch must be an existing absolute permitted directory')
    backend = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend))
    os.chdir(backend)
    previous_temp = tempfile.tempdir
    work = None
    failures = 1
    try:
        with tempfile.TemporaryDirectory(prefix='deksi-ai-sqlite-', dir=args.scratch.resolve()) as owned:
            work = Path(owned)
            for name in ('TMPDIR', 'TEMP', 'TMP', 'HERMES_TEST_SCRATCH'):
                os.environ[name] = owned
            os.environ['DEKSI_TEST_DATABASE'] = ':memory:'
            os.environ['DEKSI_TEST_RAW_ROOT'] = str(work / 'raw')
            os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
            os.environ.pop('DJANGO_SETTINGS_MODULE', None)
            tempfile.tempdir = owned
            base = importlib.import_module('backend.test_settings_indicators')
            options = {key: getattr(base, key) for key in dir(base) if key.isupper()}
            options.update(
                INSTALLED_APPS=[*base.INSTALLED_APPS, 'admin_auth'],
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
                DEKSI_RAW_DIR=work / 'raw', DEKSI_SCRAPING_DIR=str(work / 'scraping'),
                DEKSI_AI_NARRATIVES_ENABLED=False,
            )
            import django
            from django.conf import settings
            from django.test.runner import DiscoverRunner
            if settings.configured:
                raise RuntimeError('Refusing an already configured application process')
            settings.configure(**options)
            # Python-layer guard, not an OS sandbox; test providers use explicit fake transports.
            with patch('socket.socket.connect', side_effect=AssertionError('Live network forbidden in offline QA')):
                django.setup()
                failures = DiscoverRunner(verbosity=1, interactive=False).run_tests(TEST_LABELS)
    finally:
        tempfile.tempdir = previous_temp
        cleaned = work is None or not work.exists()
        print(json.dumps({'kind': 'isolated_sqlite_test', 'failures': failures,
            'interpreter': sys.executable, 'temporaryDirectoryRemoved': cleaned,
            'providerCallsAllowed': False, 'applicationServerStarted': False}), flush=True)
        if not cleaned:
            raise RuntimeError('Owned test directory cleanup failed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
