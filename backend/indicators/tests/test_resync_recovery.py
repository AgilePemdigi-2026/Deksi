import json
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase

from indicators import bps
from indicators.models import ObservationCandidate
from indicators.resync_model import ResyncJob
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import create_sync_run


class ResyncRecoveryTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="recovery-admin", is_staff=True)
        self.client.force_login(self.staff)
        self.source = bps._get_or_create_source()
        self.job = ResyncJob.objects.create(source=self.source, requested_by=self.staff, request_key=uuid.uuid4())

    def reconcile(self, **payload):
        return self.client.post(f"/api/admin/resync-jobs/{self.job.pk}/reconcile/",
                                data=json.dumps(payload), content_type="application/json")

    def test_staff_can_record_review_as_unknown_without_fabricating_outcome(self):
        self.job.run = create_sync_run(source=self.source, actor=self.staff)
        self.job.status = "running"
        self.job.save(update_fields=["run", "status"])
        response = self.reconcile(confirmed=True, reason="Pemeriksaan manual telah dilakukan")
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "unknown")
        self.assertEqual(self.job.run.status, "unknown")
        self.assertEqual(self.job.resolved_by, self.staff)
        self.assertIsNotNone(self.job.resolved_at)
        self.assertIsNone(self.job.finished_at)
        self.assertIsNone(self.job.run.finished_at)
        self.assertEqual(self.job.resolution_reason, "Pemeriksaan manual telah dilakukan")
        status = self.client.get(f"/api/admin/resync-jobs/{self.job.pk}/").json()
        self.assertEqual(status["resolvedBy"], self.staff.username)
        self.assertEqual(status["resolutionReason"], self.job.resolution_reason)
        self.assertEqual(self.reconcile(confirmed=True, reason="Pemeriksaan kedua dilakukan").status_code, 409)

    def test_requires_staff_confirmation_and_csrf(self):
        self.job.run = create_sync_run(source=self.source, actor=self.staff)
        self.job.status = "running"
        self.job.save(update_fields=["run", "status"])
        self.assertEqual(self.reconcile(confirmed=False, reason="Pemeriksaan manual telah dilakukan").status_code, 400)
        self.assertEqual(self.reconcile(confirmed=True, reason="pendek").status_code, 400)
        user = get_user_model().objects.create_user(username="nonstaff-recovery")
        self.client.force_login(user)
        self.assertEqual(self.reconcile(confirmed=True, reason="Pemeriksaan manual telah dilakukan").status_code, 403)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        response = csrf_client.post(f"/api/admin/resync-jobs/{self.job.pk}/reconcile/",
            data=json.dumps({"confirmed": True, "reason": "Pemeriksaan manual telah dilakukan"}),
            content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "running")

    def test_history_exposes_job_identity_separately_from_run_identity(self):
        create_sync_run(source=self.source, actor=self.staff)
        self.job.run = create_sync_run(source=self.source, actor=self.staff)
        self.job.status = "running"
        self.job.save(update_fields=["run", "status"])
        self.assertNotEqual(self.job.pk, self.job.run_id)
        rows = self.client.get("/api/admin/sync-history/").json()["items"]
        row = next(item for item in rows if item["id"] == str(self.job.run_id))
        self.assertEqual(row["resyncJobId"], str(self.job.pk))
        self.assertIsNone(row["resolvedBy"])

    def test_reconciliation_fences_a_worker_that_returns_after_manual_review(self):
        series = {"code": "resync_fenced", "var_id": 123, "name": "Synthetic", "category": "Synthetic",
                  "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
                  "frequency": "annual", "data_type": "level", "subperiods": {1: 1}}
        point = {"observation_date": date(2020, 12, 31), "period_label": "2020", "frequency": "annual",
                 "data_type": "level", "value": Decimal("6"), "unit": "%"}

        def fetch(*args, **kwargs):
            response = self.reconcile(confirmed=True, reason="Pemeriksaan manual telah dilakukan")
            self.assertEqual(response.status_code, 200)
            return [point]

        with patch.object(bps, "BPS_SERIES", [series]), patch.object(bps, "fetch_series", side_effect=fetch):
            call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "unknown")
        self.assertEqual(self.job.run.status, "unknown")
        self.assertEqual(self.job.resolved_by, self.staff)
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertEqual(SyncRun.objects.count(), 1)
