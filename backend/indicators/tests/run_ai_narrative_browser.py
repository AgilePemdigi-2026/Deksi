"""Owned browser integration runner: real frontend/backend, synthetic DB and HTTP model transport."""
import argparse
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--dependencies', required=True)
    options = parser.parse_args()
    candidate = Path(__file__).resolve().parents[3]
    name = 'deksi-ai-browser-' + uuid.uuid4().hex[:8]
    environment = os.environ.copy()
    environment['DEKSI_AI_BROWSER_PASSWORD'] = secrets.token_urlsafe(32)

    def call(*args, check=True):
        result = subprocess.run(args, capture_output=True, text=True, env=environment)
        if check and result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result

    owned = False
    try:
        call('docker', 'image', 'inspect', 'deksi-qa-bab65d906565-backend:latest')
        call('docker', 'run', '-d', '--name', name, '--pull=never', '--read-only',
            '-p', '127.0.0.1::8080', '--tmpfs', '/tmp:rw,size=128m',
            '-e', 'HERMES_TEST_SCRATCH=/tmp', '-e', 'DEKSI_AI_BROWSER_TEST=1',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'DEKSI_AI_BROWSER_PASSWORD',
            '-e', 'DEKSI_TEST_DATABASE=/tmp/deksi-ai-browser-fixture/test.sqlite3',
            '-v', candidate.as_posix() + '/backend:/app/backend:ro', '-w', '/app/backend',
            'deksi-qa-bab65d906565-backend:latest', 'python', '-m',
            'indicators.tests.ai_narrative_browser_server')
        owned = True
        port = call('docker', 'port', name, '8080/tcp').stdout.strip().rsplit(':', 1)[1]
        origin = 'http://127.0.0.1:' + port
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(100):
            try:
                with opener.open(origin + '/api/__ai-fixture/health/', timeout=1) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(.2)
        else:
            raise RuntimeError('Synthetic backend did not become ready')
        environment['DEKSI_AI_TEST_BACKEND'] = origin
        result = subprocess.run(['python', '-B', 'frontend/tests/run_ai_narrative_frontend.py',
            '--mode', 'browser', '--dependencies', options.dependencies], cwd=candidate, env=environment)
        if result.returncode:
            logs = call('docker', 'logs', name, check=False)
            print('Synthetic backend diagnostics:', logs.stdout, logs.stderr)
        return result.returncode
    except Exception:
        if owned:
            logs = call('docker', 'logs', name, check=False)
            print('Synthetic fixture startup diagnostics:', logs.stdout, logs.stderr)
        raise
    finally:
        if owned:
            removed = call('docker', 'rm', '-f', name, check=False)
            if removed.returncode:
                raise RuntimeError('Owned browser backend cleanup failed')
            print('Owned browser backend removed; database and RAW were tmpfs only.')


if __name__ == '__main__':
    raise SystemExit(main())
