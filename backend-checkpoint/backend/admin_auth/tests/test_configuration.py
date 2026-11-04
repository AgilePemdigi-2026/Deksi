import json
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class AuthConfigurationTests(SimpleTestCase):
    def read_configuration(self, debug):
        environment = dict(
            os.environ,
            DEBUG=str(debug),
            SECRET_KEY="test-only-auth-config-fixture",
            BPS_API_KEY="",
            BPS_API_BASE_URL="",
        )
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment.pop("DJANGO_SETTINGS_MODULE", None)
        code = (
            "import json;from backend import settings as s;"
            "keys=['CORS_ALLOWED_ORIGINS','CSRF_TRUSTED_ORIGINS',"
            "'SESSION_COOKIE_SECURE','CSRF_COOKIE_SECURE'];"
            "print(json.dumps({k:getattr(s,k,None) for k in keys}))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_development_configuration_explicitly_allows_reviewed_frontend(self):
        config = self.read_configuration(True)
        self.assertIn("http://127.0.0.1:62942", config["CORS_ALLOWED_ORIGINS"])
        self.assertIn("http://127.0.0.1:62942", config["CSRF_TRUSTED_ORIGINS"])

    def test_nondebug_cookie_defaults_require_https(self):
        config = self.read_configuration(False)
        self.assertIs(config["SESSION_COOKIE_SECURE"], True)
        self.assertIs(config["CSRF_COOKIE_SECURE"], True)
