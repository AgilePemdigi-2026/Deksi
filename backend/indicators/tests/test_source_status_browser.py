import os
import subprocess
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase

from indicators.models import DataUpdateLog, Source, SourceRevision
from indicators.sync_history_service import create_sync_run, finalize_sync_run


class SourceStatusBrowserTests(LiveServerTestCase):
    def test_admin_can_deactivate_and_reactivate_legacy_source_through_real_browser(self):
        frontend = os.environ.get("DEKSI_FRONTEND_TEST_ROOT")
        if not frontend:
            self.skipTest("DEKSI_FRONTEND_TEST_ROOT must point to the isolated frontend copy")
        source = Source.objects.create(
            source_id="BROWSER_FIXTURE", source_name="Browser Fixture", institution="Fixture",
            primary_url="https://example.test/",
        )
        user = get_user_model().objects.create_user(username="browser-fixture-admin", is_staff=True)
        user.set_password("synthetic-browser-test-password")
        user.save()
        run = create_sync_run(source=source)
        finalize_sync_run(run, success=True)
        before = DataUpdateLog.objects.count()
        env = os.environ.copy()
        env.update(DEKSI_TEST_BACKEND=self.live_server_url, DEKSI_TEST_USER="browser-fixture-admin",
                   DEKSI_TEST_PASS="synthetic-browser-test-password")
        result = subprocess.run(
            ["node", str(Path(frontend) / "tests/admin-source-e2e.browser.mjs")],
            cwd=frontend, env=env, capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source.refresh_from_db()
        self.assertEqual(source.status, "active")
        self.assertEqual(source.acquisition_method, "")
        self.assertEqual(SourceRevision.objects.filter(source=source).count(), 4)
        self.assertEqual(DataUpdateLog.objects.count(), before)
