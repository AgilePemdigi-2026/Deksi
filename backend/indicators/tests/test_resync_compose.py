import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase


class ResyncComposeTests(TestCase):
    def test_worker_uses_existing_backend_image_and_waits_for_migrations(self):
        project = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory(prefix="deksi-f14-compose-", dir=os.environ["HERMES_TEST_SCRATCH"]) as tmp:
            envfile = Path(tmp) / "synthetic.env"
            envfile.write_text("SECRET_KEY=synthetic\nALLOWED_HOSTS=example.test\nPOSTGRES_PASSWORD=synthetic\n"
                               "BPS_API_KEY=synthetic\n", encoding="utf-8")
            env = os.environ.copy()
            for name in list(env):
                if name in {"SECRET_KEY", "ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS"} or name.startswith(
                    ("POSTGRES_", "BPS_", "COMPOSE_")
                ):
                    env.pop(name)
            result = subprocess.run(["docker", "compose", "--env-file", str(envfile), "-f",
                                     str(project / "docker-compose.prod.yml"), "config", "--format", "json"],
                                    capture_output=True, text=True, check=True, env=env)
        services = json.loads(result.stdout)["services"]
        worker = services["resync-worker"]
        self.assertIn("process_resync", " ".join(worker["command"]))
        self.assertEqual(worker["depends_on"]["backend"]["condition"], "service_healthy")
        self.assertEqual(worker["environment"]["POSTGRES_HOST"], "db")
        self.assertEqual(worker["environment"]["BPS_API_KEY"], "synthetic")
