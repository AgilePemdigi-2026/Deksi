import os
import subprocess
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import LiveServerTestCase

from indicators import bps
from indicators.models import ObservationCandidate
from indicators.resync_model import ResyncJob
from indicators.resync_worker import process_one
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import create_sync_run, finalize_sync_run


class ResyncBrowserE2ETests(LiveServerTestCase):
    def test_browser_real_backend_postgres_worker_success_and_recovery(self):
        if connection.vendor != "postgresql":
            self.skipTest("This browser test requires disposable PostgreSQL")
        frontend = os.environ.get("DEKSI_FRONTEND_TEST_ROOT")
        if not frontend:
            self.skipTest("DEKSI_FRONTEND_TEST_ROOT is required")
        source = bps._get_or_create_source()
        user = get_user_model().objects.create_user(username="resync-fixture-admin", is_staff=True)
        user.set_password("synthetic-browser-fixture-password")
        user.save()
        finalize_sync_run(create_sync_run(source=source, actor=user), success=True)
        series = {"code": "resync_browser_synthetic", "var_id": 987, "name": "Synthetic",
                  "category": "Synthetic", "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
                  "frequency": "annual", "data_type": "level", "subperiods": {1: 1}}
        point = {"observation_date": date(2020, 12, 31), "period_label": "2020", "frequency": "annual",
                 "data_type": "level", "value": Decimal("6"), "unit": "%"}
        env = os.environ.copy()
        env.update(DEKSI_TEST_BACKEND=self.live_server_url, DEKSI_TEST_USER="resync-fixture-admin",
                   DEKSI_TEST_PASS="synthetic-browser-fixture-password")
        process = subprocess.Popen(["node", str(Path(frontend) / "tests/resync-e2e.browser.mjs")],
                                   cwd=frontend, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for index in range(2):
                deadline = time.monotonic() + 45
                while not ResyncJob.objects.filter(status="queued").exists():
                    if process.poll() is not None:
                        out, err = process.communicate()
                        self.fail(f"Browser stopped before request {index + 1}: {out} {err}")
                    if time.monotonic() >= deadline:
                        self.fail(f"Browser did not queue request {index + 1}")
                    time.sleep(0.1)
                if index == 0:
                    with patch.object(bps, "BPS_SERIES", [series]), \
                            patch.object(bps, "fetch_series", return_value=[point]):
                        process_one()
                else:
                    with patch.object(bps, "_sync_bps_started", side_effect=SystemExit("synthetic crash")):
                        with self.assertRaises(SystemExit):
                            process_one()
            out, err = process.communicate(timeout=90)
            self.assertEqual(process.returncode, 0, out + err)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        statuses = list(ResyncJob.objects.order_by("pk").values_list("status", flat=True))
        self.assertEqual(statuses, ["success", "unknown"])
        self.assertEqual(ObservationCandidate.objects.count(), 1)
        self.assertEqual(SyncRun.objects.filter(status="unknown").count(), 1)
        self.assertEqual(ResyncJob.objects.get(status="unknown").resolved_by, user)
