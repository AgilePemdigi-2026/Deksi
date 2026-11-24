"""Run only the owned disposable browser/PostgreSQL integration test."""
import json
import os
import secrets
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

candidate = Path(__file__).resolve().parents[2]
scratch = Path(os.environ['HERMES_TEST_SCRATCH']).resolve()
assert scratch.is_dir(), 'Scratch directory must already exist'
os.environ['DEKSI_SYNTHETIC_PASSWORD'] = secrets.token_urlsafe(32)
name = 'deksi-online-browser-' + uuid.uuid4().hex[:8]
network, pg, backend = name + '-net', name + '-pg', name + '-be'
image = 'deksi-qa-bab65d906565-backend:latest'

def call(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError('Command failed: ' + args[0] + '\n' + result.stdout + result.stderr)
    return result

created = []
try:
    # Docker must not auto-pull or install anything for this bounded test.
    call('docker', 'image', 'inspect', image, 'postgres:17-alpine')
    # Docker Desktop does not publish host ports from an internal-only bridge.
    # Only backend loopback is published; the test rejects external HTTP transport.
    call('docker', 'network', 'create', network)
    created.append(network)
    with tempfile.TemporaryDirectory(prefix='deksi-online-browser-evidence-', dir=scratch) as evidence:
        call('docker', 'run', '-d', '--rm', '--name', pg, '--network', network,
             '--tmpfs', '/var/lib/postgresql/data:rw,size=256m',
             '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', '-e', 'POSTGRES_DB=online_test', 'postgres:17-alpine')
        created.append(pg)
        for _ in range(40):
            if call('docker', 'exec', pg, 'pg_isready', '-U', 'postgres', '-d', 'online_test', check=False).returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError('Disposable PostgreSQL did not become ready')
        call('docker', 'run', '-d', '--name', backend, '--network', network,
             '-p', '127.0.0.1::8080', '--read-only', '--tmpfs', '/tmp:rw,size=128m',
             '--mount', f'type=bind,source={candidate.as_posix()}/backend/indicators,target=/app/backend/indicators,readonly',
             '--mount', f'type=bind,source={candidate.as_posix()}/backend/backend,target=/app/backend/backend,readonly',
             '--mount', f'type=bind,source={Path(evidence).as_posix()},target=/evidence',
             '-e', f'DATABASE_URL=postgresql://postgres@{pg}:5432/online_test',
             '-e', 'HERMES_TEST_SCRATCH=/tmp', '-e', 'PYTHONDONTWRITEBYTECODE=1',
             '-e', 'DEKSI_BROWSER_INTEGRATION=1', '-e', 'DEKSI_SYNTHETIC_PASSWORD',
             image, 'python', 'manage.py', 'test', 'indicators.tests.test_online_browser', '-v', '1')
        created.append(backend)
        for _ in range(160):
            if (Path(evidence) / 'online-browser-ready.json').exists():
                break
            state = json.loads(call('docker', 'inspect', '--format', '{{json .State}}', backend).stdout)
            if not state['Running']:
                raise RuntimeError('Backend test stopped before ready: ' + call('docker', 'logs', backend).stdout)
            time.sleep(.25)
        else:
            raise RuntimeError('Backend test readiness deadline expired')
        port = call('docker', 'port', backend, '8080/tcp').stdout.strip().rsplit(':', 1)[1]
        env = os.environ.copy()
        env['HERMES_TEST_SCRATCH'] = scratch.as_posix()
        env['DEKSI_DISPOSABLE_BACKEND'] = 'http://127.0.0.1:' + port
        node = subprocess.run(['node', 'tests/online-real.browser.mjs'], cwd=candidate / 'frontend',
                              env=env, capture_output=True, text=True, timeout=110)
        print(node.stdout, node.stderr)
        if node.returncode:
            logs = call('docker', 'logs', backend)
            print('Backend failure diagnostics:', logs.stdout, logs.stderr)
            raise RuntimeError('Browser integration failed; node exit=' + str(node.returncode))
        exit_code = int(call('docker', 'wait', backend).stdout.strip())
        logs = call('docker', 'logs', backend)
        print(logs.stdout, logs.stderr)
        assert exit_code == 0, 'Backend integration test exit=' + str(exit_code)
        print('Integration runner PASS, backend exit=0, browser exit=0')
finally:
    for resource in reversed(created):
        if resource == network:
            call('docker', 'network', 'rm', resource, check=False)
        else:
            call('docker', 'rm', '-f', resource, check=False)
    print('Owned integration resources cleanup attempted:', created)
