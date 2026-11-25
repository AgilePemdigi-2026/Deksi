"""Run selected engine QA with disposable SQLite, no credentials or provider access."""
import argparse
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('labels', nargs='*', default=['indicators.tests.test_economic_engine'])
    args = parser.parse_args()
    if not args.scratch.is_absolute() or not args.scratch.is_dir():
        parser.error('An existing absolute permitted scratch directory is required')
    backend = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend))
    os.chdir(backend)
    previous_temp = tempfile.tempdir
    owned_path = None
    failures = 1
    try:
        with tempfile.TemporaryDirectory(prefix='deksi-economic-qa-', dir=args.scratch) as directory:
            owned_path = Path(directory)
            for name in ('TMPDIR', 'TMP', 'TEMP', 'HERMES_TEST_SCRATCH'):
                os.environ[name] = directory
            tempfile.tempdir = directory
            os.environ.pop('DJANGO_SETTINGS_MODULE', None)
            os.environ['DEKSI_TEST_DATABASE'] = ':memory:'
            os.environ['DEKSI_TEST_RAW_ROOT'] = str(owned_path / 'raw')
            base = importlib.import_module('backend.test_settings_indicators')
            options = {key: getattr(base, key) for key in dir(base) if key.isupper()}
            options.update(INSTALLED_APPS=[*base.INSTALLED_APPS, 'admin_auth'],
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
                DEKSI_RAW_DIR=owned_path / 'raw', DEKSI_SCRAPING_DIR=str(owned_path / 'scraping'))
            import django
            from django.conf import settings
            from django.test.runner import DiscoverRunner
            settings.configure(**options)
            with patch('socket.socket.connect', side_effect=AssertionError('No live network in engine QA')):
                django.setup()
                failures = DiscoverRunner(verbosity=1, interactive=False).run_tests(args.labels)
    finally:
        tempfile.tempdir = previous_temp
        cleaned = owned_path is None or not owned_path.exists()
        print(json.dumps({'disposableDatabase': True, 'temporaryDirectoryRemoved': cleaned,
            'failures': failures, 'providerCallsAllowed': False}), flush=True)
        if not cleaned:
            raise RuntimeError('Owned fixture cleanup failed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
