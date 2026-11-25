"""Explicit, no-install PostgreSQL narrative QA on an owned internal Docker network."""
import json
import os
import subprocess
import time
import uuid
from pathlib import Path


def main():
    candidate = Path(__file__).resolve().parents[3]
    identity = uuid.uuid4().hex[:8]
    network, pg = 'deksi-ai-pg-' + identity, 'deksi-ai-pg-' + identity + '-db'
    database, user = 'dksi_cand_pg_' + identity, 'dksi_test_' + identity
    owned = []

    def call(*args, check=True):
        result = subprocess.run(args, capture_output=True, text=True)
        if check and result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result

    try:
        call('docker', 'image', 'inspect', 'deksi-qa-bab65d906565-backend:latest', 'postgres:17-alpine')
        call('docker', 'network', 'create', '--internal', network)
        owned.append(('network', network))
        call('docker', 'run', '-d', '--rm', '--name', pg, '--network', network,
             '--network-alias', 'candidate-pg', '--tmpfs', '/var/lib/postgresql/data:rw,size=256m',
             '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', '-e', 'POSTGRES_DB=' + database,
             '-e', 'POSTGRES_USER=' + user, '--pull=never', 'postgres:17-alpine')
        owned.append(('container', pg))
        for _ in range(80):
            if call('docker', 'exec', pg, 'pg_isready', '-U', user, '-d', database, check=False).returncode == 0:
                break
            time.sleep(.25)
        else:
            raise RuntimeError('Owned PostgreSQL did not become ready')
        command = ['docker', 'run', '--rm', '--pull=never', '--network', network, '--read-only',
            '--tmpfs', '/tmp:rw,size=128m', '-e', 'HERMES_TEST_SCRATCH=/tmp',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'DJANGO_SETTINGS_MODULE=backend.test_settings_candidate_pg',
            '-e', 'DEKSI_CANDIDATE_PG_OPT_IN=DEKSI_CANDIDATE_PG_TEST_ONLY',
            '-e', 'DEKSI_CANDIDATE_PG_HOST=candidate-pg', '-e', 'DEKSI_CANDIDATE_PG_PORT=5432',
            '-e', 'DEKSI_CANDIDATE_PG_NAME=' + database, '-e', 'DEKSI_CANDIDATE_PG_USER=' + user,
            '-e', 'DEKSI_CANDIDATE_PG_PASSWORD=synthetic-fixture-only',
            '-v', candidate.as_posix() + '/backend:/app/backend:ro', '-w', '/app/backend',
            'deksi-qa-bab65d906565-backend:latest', 'python', 'manage.py', 'test',
            'indicators.tests.test_ai_narrative_postgres', '--verbosity', '2']
        result = call(*command, check=False)
        print(result.stdout)
        print(result.stderr)
        if result.returncode:
            return result.returncode
        print('PASS: disposable PostgreSQL narrative QA; no provider connection or host DB port')
        return 0
    finally:
        outcomes = []
        for kind, name in reversed(owned):
            args = ('docker', 'network', 'rm', name) if kind == 'network' else ('docker', 'rm', '-f', name)
            result = call(*args, check=False)
            outcomes.append({'kind': kind, 'name': name, 'cleanupExit': result.returncode})
        print('Cleanup:', json.dumps(outcomes))
        if any(item['cleanupExit'] != 0 for item in outcomes):
            raise RuntimeError('Owned QA cleanup requires inspection')


if __name__ == '__main__':
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    raise SystemExit(main())
