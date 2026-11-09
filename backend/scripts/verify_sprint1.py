"""Worktree-local verification: existing interpreter, disposable data, loopback only."""

import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
SCRATCH = Path("C:/Users/Pongo/AppData/Local/hermes/cache/scratch")
PYTHON = Path("E:/Deksi-Team/.hermes/worktrees/feature-1-login-be/backend/.venv/Scripts/python.exe")
PORT = 55947
LINT_PATHS = [
    "admin_auth",
    "backend/settings.py",
    "backend/urls.py",
    "backend/test_settings_auth.py",
    "backend/test_settings_reset.py",
    "backend/test_settings_reset_concurrency.py",
    "backend/test_settings_sprint1.py",
    "indicators/admin.py",
    "indicators/models.py",
    "indicators/urls.py",
    "indicators/dashboard_views.py",
    "indicators/feedback_model.py",
    "indicators/feedback_views.py",
    "indicators/migrations/0006_merge_dashboard_feedback.py",
    "indicators/tests/test_dashboard_api.py",
    "indicators/tests/test_dashboard_feedback.py",
    "indicators/tests/test_dashboard_http.py",
    "indicators/tests/test_dashboard_migrations.py",
    "indicators/tests/test_sprint1_integration.py",
    "scripts/verify_sprint1.py",
]


def configure(raw):
    if (BACKEND / ".env").exists():
        raise RuntimeError("Verification must not load a worktree .env")
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise RuntimeError("Use the existing approved project interpreter")
    for key in ("PYTHONPATH", "PYTHONHOME", "DJANGO_SETTINGS_MODULE", "CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"):
        os.environ.pop(key, None)
    os.environ.update(
        SECRET_KEY="synthetic-only-sprint1-integration-key",
        DEBUG="False",
        BPS_API_KEY="",
        BPS_API_BASE_URL="https://example.test/no-provider",
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
        DJANGO_SETTINGS_MODULE="backend.test_settings_sprint1",
        HERMES_TEST_SCRATCH=str(SCRATCH),
        DEKSI_TEST_DATABASE=":memory:",
        DEKSI_TEST_RAW_ROOT=str(raw),
    )
    os.chdir(BACKEND)


def run(*args):
    return subprocess.run([str(PYTHON), "-B", *args], cwd=BACKEND, check=False).returncode


def main(mode):
    with tempfile.TemporaryDirectory(prefix="sprint1-unified-verify-", dir=SCRATCH) as raw:
        configure(raw)
        if mode == "bootstrap":
            for module in ("django", "axes", "corsheaders", "environ", "ruff"):
                if importlib.util.find_spec(module) is None:
                    raise RuntimeError(f"Existing dependency unavailable: {module}")
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", PORT))
            return run("-m", "pip", "check")
        if mode == "build":
            commands = [
                ["-m", "ruff", "check", *LINT_PATHS],
                [
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "admin_auth",
                    "backend/test_settings_sprint1.py",
                    "indicators/tests/test_sprint1_integration.py",
                    "scripts/verify_sprint1.py",
                ],
                ["manage.py", "check"],
                ["manage.py", "makemigrations", "--check", "--dry-run"],
            ]
            for command in commands:
                result = run(*command)
                if result:
                    return result
            return 0
        if mode == "test":
            result = run("manage.py", "test", "admin_auth.tests", "indicators.tests", "--noinput", "-v", "2")
            if result:
                return result
            with tempfile.TemporaryDirectory(prefix="sprint1-unified-concurrency-", dir=SCRATCH) as directory:
                os.environ["DEKSI_RESET_TEST_DB"] = str(Path(directory) / "reset-concurrency-canonical.sqlite3")
                return run(
                    "manage.py",
                    "test",
                    "admin_auth.tests.reset_concurrency",
                    "--settings=backend.test_settings_reset_concurrency",
                    "--noinput",
                    "-v",
                    "2",
                )
        if mode == "start":
            sys.path.insert(0, str(BACKEND))
            from wsgiref.simple_server import make_server

            import django

            django.setup()
            from django.core.management import call_command
            from django.core.wsgi import get_wsgi_application
            from django.db import connections

            if connections["default"].settings_dict["NAME"] != ":memory:":
                raise RuntimeError("Startup must use only an in-process memory database")
            call_command("migrate", interactive=False, verbosity=0)
            with make_server("127.0.0.1", PORT, get_wsgi_application()) as server:
                timer = threading.Timer(20, server.shutdown)
                timer.daemon = True
                timer.start()
                print(f"DEKSI_VERIFY_PID={os.getpid()}", flush=True)
                try:
                    server.serve_forever(poll_interval=0.1)
                finally:
                    timer.cancel()
                    connections.close_all()
            print("DEKSI_VERIFY_STOPPED", flush=True)
            return 0
        raise ValueError("Expected bootstrap, build, test or start")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
