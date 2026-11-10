import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import RequestFactory, TransactionTestCase, skipUnlessDBFeature

from indicators import bps
from indicators.models import ObservationCandidate, Source
from indicators.resync_model import ResyncJob
from indicators.resync_views import reconcile_resync, request_resync
from indicators.resync_worker import claim_next_job, process_one
from indicators.source_status import ActiveSyncError
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import begin_sync_run


@skipUnlessDBFeature("has_select_for_update")
class ResyncPostgresConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.user = get_user_model().objects.create_user(username="race-admin", is_staff=True)
        self.source = Source.objects.create(
            source_id="BPS", source_name="Synthetic BPS", institution="Synthetic",
            primary_url="https://example.test/",
        )

    def race(self, left, right):
        barrier = threading.Barrier(2, timeout=10)

        def run(fn):
            close_old_connections()
            try:
                barrier.wait()
                return fn()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, fn) for fn in (left, right)]
            return [future.result(timeout=20) for future in futures]

    def submit(self, key):
        request = RequestFactory().post(
            "/api/admin/sources/BPS/resync/", json.dumps({"requestId": str(key)}),
            content_type="application/json",
        )
        request.user = self.user
        response = request_resync(request, "BPS")
        return response.status_code, json.loads(response.content)

    def test_different_keys_create_only_one_active_job(self):
        first, second = uuid.uuid4(), uuid.uuid4()
        outcomes = self.race(lambda: self.submit(first), lambda: self.submit(second))
        self.assertEqual(sorted(result[0] for result in outcomes), [202, 409])
        self.assertEqual(ResyncJob.objects.count(), 1)

    def test_same_key_returns_same_job_to_both_requests(self):
        key = uuid.uuid4()
        outcomes = self.race(lambda: self.submit(key), lambda: self.submit(key))
        self.assertEqual([result[0] for result in outcomes], [202, 202])
        self.assertEqual(outcomes[0][1]["id"], outcomes[1][1]["id"])
        self.assertEqual(ResyncJob.objects.count(), 1)

    def test_two_workers_claim_only_one_run(self):
        ResyncJob.objects.create(source=self.source, requested_by=self.user, request_key=uuid.uuid4())
        outcomes = self.race(claim_next_job, claim_next_job)
        self.assertEqual(sum(job is not None for job in outcomes), 1)
        self.assertEqual(SyncRun.objects.count(), 1)
        self.assertEqual(ResyncJob.objects.get().run_id, SyncRun.objects.get().pk)

    def test_existing_sync_and_enqueue_cannot_both_start(self):
        key = uuid.uuid4()

        def start():
            try:
                begin_sync_run(source=self.source)
                return "started"
            except ActiveSyncError:
                return "blocked"

        request, start_result = self.race(lambda: self.submit(key), start)
        self.assertIn((request[0], start_result), [(202, "blocked"), (409, "started")])
        self.assertEqual(ResyncJob.objects.count() + SyncRun.objects.count(), 1)

    def test_reconciled_worker_cannot_write_after_new_job_is_queued(self):
        for key, value in bps.BPS_SOURCE_DEFAULTS.items():
            setattr(self.source, key, value)
        self.source.save()
        job = ResyncJob.objects.create(source=self.source, requested_by=self.user, request_key=uuid.uuid4())
        series = {"code": "postgres_fence", "var_id": 123, "name": "Synthetic", "category": "Synthetic",
                  "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
                  "frequency": "annual", "data_type": "level", "subperiods": {1: 1}}
        point = {"observation_date": date(2020, 12, 31), "period_label": "2020", "frequency": "annual",
                 "data_type": "level", "value": Decimal("6"), "unit": "%"}
        fetching = threading.Event()
        resume = threading.Event()

        def fetch(*args, **kwargs):
            fetching.set()
            if not resume.wait(15):
                raise TimeoutError("Timed out waiting for synthetic recovery")
            return [point]

        def work():
            close_old_connections()
            try:
                return process_one()
            finally:
                close_old_connections()

        with patch.object(bps, "BPS_SERIES", [series]), patch.object(bps, "fetch_series", side_effect=fetch):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(work)
                try:
                    self.assertTrue(fetching.wait(15))
                    request = RequestFactory().post("/", json.dumps({"confirmed": True,
                        "reason": "Pemeriksaan manual telah dilakukan"}), content_type="application/json")
                    request.user = self.user
                    self.assertEqual(reconcile_resync(request, job.pk).status_code, 200)
                    self.assertEqual(self.submit(uuid.uuid4())[0], 202)
                finally:
                    resume.set()
                future.result(timeout=15)
        job.refresh_from_db()
        self.assertEqual(job.status, "unknown")
        self.assertEqual(job.run.status, "unknown")
        self.assertFalse(ObservationCandidate.objects.exists())
