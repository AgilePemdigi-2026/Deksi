"""Run the actual React form against Django's isolated in-memory test server."""
import os
import json
from pathlib import Path
import socket
import subprocess
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.environ["DEKSI_AUTH_BACKEND_ROOT"])
    os.environ["DJANGO_SETTINGS_MODULE"] = "backend.test_settings_auth"
    import django
    django.setup()

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase, override_settings
from django.core.signals import got_request_exception


class LoginFormIntegrationTests(LiveServerTestCase):
    host = "127.0.0.1"

    @classmethod
    def setUpClass(cls):
        # Django caches trusted origins in the live middleware instance.
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            cls.frontend_port = available.getsockname()[1]
        super().setUpClass()

    def setUp(self):
        get_user_model().objects.create_user(
            username="integration-admin", email="admin@example.test",
            password="SYNTHETIC-integration-fixture-only-731!", is_staff=True,
        )

    def run_browser(self, scenario):
        port = self.frontend_port
        origin = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update(DEKSI_AUTH_BACKEND_URL=self.live_server_url,
                           DEKSI_AUTH_FE_PORT=str(port), DEKSI_AUTH_SCENARIO=scenario)
        server_errors = []
        def record_error(sender, request, **kwargs):
            error = sys.exc_info()[1]
            server_errors.append({"path": request.path_info, "exception_type": type(error).__name__,
                                  "sqlite_lock": "locked" in str(error).lower()})
        got_request_exception.connect(record_error, weak=False)
        try:
            with override_settings(CORS_ALLOWED_ORIGINS=[origin], CSRF_TRUSTED_ORIGINS=[origin]):
                result = subprocess.run(
                    [environment["DEKSI_AUTH_NODE"], str(Path(__file__).with_name("login.integration.mjs"))],
                    cwd=Path(__file__).parent.parent, env=environment,
                    capture_output=True, text=True, timeout=180,
                )
        finally:
            got_request_exception.disconnect(record_error)
        output = Path(environment["DEKSI_AUTH_ARTIFACTS"])
        output.mkdir(parents=True, exist_ok=True)
        (output / f"{scenario}-server-errors.json").write_text(json.dumps(server_errors), encoding="utf-8")
        (output / f"{scenario}-process.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-1800:])

    def test_actual_login_button_creates_admin_session(self):
        self.run_browser("login")

    def test_reload_restores_session_and_logout_button_invalidates_it(self):
        self.run_browser("logout")

    def test_real_form_denials_csrf_recovery_and_lockout(self):
        for username, flags in [("integration-member", {"is_staff": False}),
                                ("integration-inactive", {"is_staff": True, "is_active": False})]:
            get_user_model().objects.create_user(username=username,
                password="SYNTHETIC-integration-fixture-only-731!", **flags)
        self.run_browser("denials")

    def test_duplicate_submit_sends_only_one_login_request(self):
        self.run_browser("duplicate")


if __name__ == "__main__":
    from django.conf import settings
    from django.test.utils import get_runner
    raise SystemExit(bool(get_runner(settings)(verbosity=2, interactive=False).run_tests([os.environ.get("DEKSI_AUTH_TEST_LABEL", "login_integration")])))
