"""Real React forms + isolated Django DB; recovery links only cross stdin IPC."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.environ["DEKSI_AUTH_BACKEND_ROOT"])
    os.environ["DJANGO_SETTINGS_MODULE"] = "backend.test_settings_reset"
    import django
    django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import LiveServerTestCase, override_settings


class ResetFormIntegrationTests(LiveServerTestCase):
    host = "127.0.0.1"

    @classmethod
    def setUpClass(cls):
        with socket.socket() as available:
            available.bind((cls.host, 0))
            cls.frontend_port = available.getsockname()[1]
        origin = f"http://{cls.host}:{cls.frontend_port}"
        cls.origins = override_settings(
            CORS_ALLOWED_ORIGINS=[origin], CSRF_TRUSTED_ORIGINS=[origin],
            ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN=origin,
        )
        cls.origins.enable()
        try:
            super().setUpClass()
        except Exception:
            cls.origins.disable()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.origins.disable()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="integration-admin", email="admin@example.test", is_staff=True,
            password="SYNTHETIC-before-reset-fixture-731!",
        )

    def run_browser(self, scenario):
        self.assertEqual(settings.DATABASES["default"]["NAME"].split("?")[0], "file:memorydb_default")
        environment = dict(os.environ, DEKSI_AUTH_BACKEND_URL=self.live_server_url,
                           DEKSI_AUTH_FE_PORT=str(self.frontend_port), DEKSI_RESET_SCENARIO=scenario)
        output = Path(environment["DEKSI_RESET_ARTIFACTS"])
        output.mkdir(parents=True, exist_ok=True)
        with subprocess.Popen(
            [environment["DEKSI_AUTH_NODE"], str(Path(__file__).with_name("reset.integration.mjs"))],
            cwd=Path(__file__).parent.parent, env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
        ) as child:
            try:
                for line in child.stdout:
                    # Do not retain arbitrary child output or raw email/capabilities.
                    if line.strip() != '{"command":"outbox"}':
                        continue
                    emails = getattr(mail, "outbox", [])
                    link = None
                    if scenario == "flow" and emails:
                        candidates = re.findall(r"https?://[^\s]+", emails[-1].body)
                        self.assertEqual(len(candidates), 1)
                        link = candidates[0]
                        self.assertTrue(link.startswith(settings.ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN + "/admin/reset-password#"))
                    child.stdin.write(json.dumps({"count": len(emails), "link": link}) + "\n")
                    child.stdin.flush()
                code = child.wait(timeout=120)
                stderr = child.stderr.read()
                (output / f"{scenario}-driver.log").write_text(stderr, encoding="utf-8")
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
        receipt = json.loads((output / f"{scenario}-receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0, receipt.get("failure"))
        self.assertFalse(receipt.get("failure"))
        self.assertTrue(receipt["profileRemoved"])
        self.assertEqual(receipt["runtimeErrors"], [])

    def test_real_request_reset_and_login_forms(self):
        self.run_browser("flow")
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("SYNTHETIC-before-reset-fixture-731!"))
        self.assertTrue(self.user.check_password("  SYNTHETIC-after-reset-fixture-947!  "))
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(ADMIN_PASSWORD_RESET_ENABLED=False)
    def test_disabled_backend_cannot_become_synthetic_success(self):
        self.run_browser("disabled")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("SYNTHETIC-before-reset-fixture-731!"))
        self.assertEqual(len(getattr(mail, "outbox", [])), 0)


if __name__ == "__main__":
    from django.test.utils import get_runner
    raise SystemExit(bool(get_runner(settings)(verbosity=2, interactive=False).run_tests([
        os.environ.get("DEKSI_RESET_TEST_LABEL", "reset_integration")
    ])))
