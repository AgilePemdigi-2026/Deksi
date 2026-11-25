"""Start the real dashboard + archived Gemini answer on loopback for at most one hour.

No installation, provider calls, credential reads or production database access.
"""
import argparse
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def wait_json(path, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding='utf-8'))
        if process.poll() is not None:
            raise RuntimeError('Preview child stopped before readiness; inspect its local log')
        time.sleep(0.1)
    raise RuntimeError('Preview child readiness deadline exceeded')


def check_http(origin, route):
    from urllib.parse import urlsplit
    url = urlsplit(origin)
    if url.scheme != 'http' or url.hostname != '127.0.0.1':
        raise ValueError('Loopback HTTP required')
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=15)
    try:
        connection.request('GET', route)
        response = connection.getresponse()
        content = response.read()
        if response.status != 200:
            raise RuntimeError('Preview HTTP readiness failed')
        return content
    finally:
        connection.close()


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--scratch', type=Path, default=Path('C:/Users/Pongo/AppData/Local/hermes/cache/scratch'))
    parser.add_argument('--dependencies', type=Path, default=Path('E:/DEKSI/Deksi-admin-monitoring-jadwal-final/frontend/node_modules'))
    parser.add_argument('--saved-result', type=Path, default=root / 'backend/indicators/tests/fixtures/gemini_engine_preview')
    args = parser.parse_args()
    scratch, dependencies = args.scratch.resolve(), args.dependencies.resolve()
    if not scratch.is_dir():
        parser.error('Existing permitted scratch directory is required')
    node = shutil.which('node')
    if node is None:
        parser.error('Existing Node.js is required; this launcher never installs packages')
    required = ('.bin', '@types', '@vitejs', 'vite', 'typescript', 'oxlint', 'react', 'react-dom', 'recharts')
    if any(not (dependencies / name).is_dir() for name in required):
        parser.error('Existing frontend dependency set missing; no installation attempted')
    capture = root / 'backend/docs/bps-economic-inputs/live-q1-2025-20261124T184632Z-f208b5b5'
    snapshot = root / 'backend/docs/bps-economic-inputs/ui-readability-batch2-20261125/real-preview-engine-packet.json'
    if not capture.is_dir() or not snapshot.is_file() or not args.saved_result.is_dir():
        parser.error('Archived BPS capture, engine snapshot and saved Gemini result are required')
    owned = Path(tempfile.mkdtemp(prefix='deksi-gemini-dashboard-', dir=scratch))
    frontend = owned / 'frontend'
    shutil.copytree(root / 'frontend', frontend,
                    ignore=shutil.ignore_patterns('node_modules', '.git', '.env*', '.artifacts', 'dist', '*.tsbuildinfo'))
    (frontend / 'node_modules').mkdir()
    for name in required:
        target = frontend / 'node_modules' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(target), str(dependencies / name)],
                       capture_output=True, check=True)
    state = owned / 'state'
    environment = dict(os.environ)
    for name in list(environment):
        if name.endswith(('_API_KEY', '_TOKEN', '_PASSWORD')) or name in {'DATABASE_URL', 'DJANGO_SETTINGS_MODULE'}:
            environment.pop(name, None)
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8',
                       HERMES_TEST_SCRATCH=str(scratch), ENGINE_PREVIEW_STATE=str(state))
    children, streams = [], []
    try:
        for name in ('backend', 'frontend'):
            streams.append((owned / (name + '.log')).open('w', encoding='utf-8'))
        backend = subprocess.Popen([sys.executable, '-B', str(root / 'backend/indicators/tests/run_economic_engine_preview.py'),
            '--scratch', str(scratch), '--state-dir', str(state), '--capture-dir', str(capture),
            '--narrative-dir', str(args.saved_result.resolve()), '--engine-snapshot', str(snapshot)],
            cwd=root / 'backend', env=environment, stdin=subprocess.DEVNULL, stdout=streams[0], stderr=subprocess.STDOUT)
        children.append(backend)
        backend_runtime = wait_json(state / 'backend-runtime.json', backend)
        assert backend_runtime['hasNarrativePreview'] is True
        ui = subprocess.Popen([node, str(frontend / 'tests/economic-engine.preview.mjs')],
            cwd=frontend, env=environment, stdin=subprocess.DEVNULL, stdout=streams[1], stderr=subprocess.STDOUT)
        children.append(ui)
        runtime = wait_json(state / 'frontend-runtime.json', ui)
        origin = runtime['frontendOrigin']
        assert json.loads(check_http(origin, '/api/preview-context/'))['hasNarrativePreview'] is True
        narrative = json.loads(check_http(origin, '/api/preview-engine-narrative/'))
        assert narrative['status'] == 'draft_preview' and narrative['humanApproval'] is False
        assert b'<html' in check_http(origin, '/').lower()
        runtime.update(launcherPid=os.getpid(), ownedRoot=str(owned), frontendCopy=str(frontend),
                       stateDirectory=str(state), newProviderCalls=0, newDependenciesInstalled=False)
        runtime_file = root / 'backend/docs/bps-economic-inputs/gemini-dashboard-preview-20261125/current-runtime.json'
        runtime_file.parent.mkdir(parents=True, exist_ok=True)
        runtime_file.write_text(json.dumps(runtime, indent=2), encoding='utf-8')
        print('GEMINI_DASHBOARD_READY ' + json.dumps(runtime), flush=True)
        deadline = time.monotonic() + 3610
        while time.monotonic() < deadline and all(child.poll() is None for child in children):
            time.sleep(0.5)
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, AssertionError, RuntimeError, subprocess.SubprocessError):
        print('PREVIEW_FAILED Inspect logs in ' + str(owned), flush=True)
        return 1
    finally:
        if state.is_dir():
            (state / 'stop').write_text('stop', encoding='utf-8')
        for child in reversed(children):
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(timeout=5)
        for stream in streams:
            stream.close()
        print('PREVIEW_STOPPED ' + str(owned), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
