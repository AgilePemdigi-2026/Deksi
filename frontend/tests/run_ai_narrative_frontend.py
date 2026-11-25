"""No-install frontend QA in an owned copy with read-only use of existing dependencies."""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--mode', required=True, choices=['unit', 'checks', 'browser'])
    parser.add_argument('--dependencies', required=True)
    options = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    scratch = Path(os.environ['HERMES_TEST_SCRATCH']).resolve()
    dependencies = Path(options.dependencies).resolve()
    if not (dependencies / 'vite' / 'package.json').is_file() or not scratch.is_dir():
        raise RuntimeError('Existing compatible dependencies and approved scratch are required; no install attempted')
    with tempfile.TemporaryDirectory(prefix='deksi-ai-frontend-', dir=scratch) as directory:
        target = Path(directory) / 'frontend'
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('node_modules', 'dist', '.artifacts', '.env*'))
        junction = target / 'node_modules'
        if os.name == 'nt':
            subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(dependencies)],
                           check=True, capture_output=True)
        else:
            junction.symlink_to(dependencies, target_is_directory=True)
        env = {key: value for key, value in os.environ.items() if not key.startswith('VITE_')}
        env.update(NODE_OPTIONS='', npm_config_offline='true', COREPACK_ENABLE_NETWORK='0',
                   npm_config_audit='false', npm_config_update_notifier='false')
        try:
            if options.mode == 'unit':
                commands = [['node', '--test', 'tests/ai-narratives-client.test.mjs']]
            elif options.mode == 'checks':
                commands = [['node', 'node_modules/oxlint/bin/oxlint'],
                            ['node', 'node_modules/typescript/bin/tsc', '-b'],
                            ['node', 'node_modules/vite/bin/vite.js', 'build', '--configLoader', 'runner']]
            else:
                commands = [['node', 'tests/ai-narrative-real.browser.mjs']]
            for command in commands:
                result = subprocess.run(command, cwd=target, env=env)
                if result.returncode:
                    return result.returncode
            return 0
        finally:
            if junction.is_junction() if os.name == 'nt' else junction.is_symlink():
                junction.rmdir() if os.name == 'nt' else junction.unlink()
    # TemporaryDirectory removes only the copy after detaching the dependency junction.


if __name__ == '__main__':
    raise SystemExit(main())
