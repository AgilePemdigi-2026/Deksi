import json
import uuid
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import Client, TestCase
from django.utils import timezone

from indicators.models import (
    BulkCandidateReview,
    DataUpdateLog,
    Indicator,
    Observation,
    ObservationCandidate,
    RawFile,
    Source,
    SourceRevision,
)
from indicators.resync_model import ResyncJob
from indicators.schedule_model import ScheduleAudit, ScheduleConfig
from indicators.source_admin_views import _record_revision
from indicators.source_status import InactiveSourceError
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import begin_sync_run


class SourceArchiveDeleteTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-source-admin", is_staff=True)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.csrf = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.source = Source.objects.create(
            source_id="SYNTHETIC_A", source_name="Sumber sintetis", institution="Uji",
            primary_url="https://example.test/", acquisition_method="file_xlsx",
            data_format="xlsx", frequency="monthly",
        )
        _record_revision(self.source, SourceRevision.Action.CREATE, {}, self.user)

    def post(self, action, data=None, csrf=True):
        return self.client.post(
            f"/api/admin/sources/{self.source.source_id}/{action}/",
            data=json.dumps(data if data is not None else {"expectedRevision": 1}),
            content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": self.csrf} if csrf else {}),
        )

    def test_archive_retains_source_and_creates_revision(self):
        response = self.post("archive")
        self.assertEqual(response.status_code, 200, response.content)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, "archived")
        self.assertEqual(self.source.revisions.count(), 2)

    def test_delete_empty_source_removes_its_revision(self):
        response = self.post("delete")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Source.objects.filter(pk=self.source.pk).exists())
        self.assertFalse(SourceRevision.objects.filter(source_id=self.source.pk).exists())

    def test_write_requires_csrf(self):
        for action in ("archive", "delete"):
            with self.subTest(action=action):
                self.assertEqual(self.post(action, csrf=False).status_code, 403)
        self.assertTrue(Source.objects.filter(pk=self.source.pk).exists())

    def test_nonstaff_and_anonymous_rejected(self):
        self.client.force_login(get_user_model().objects.create_user(username="synthetic-nonstaff"))
        for action in ("archive", "restore", "delete"):
            self.assertEqual(self.post(action).status_code, 403)
        self.client.logout()
        for action in ("archive", "restore", "delete"):
            self.assertIn(self.post(action).status_code, (401, 403))

    def test_stale_and_invalid_revisions_are_rejected(self):
        for action in ("archive", "delete"):
            self.assertEqual(self.post(action, {"expectedRevision": 0}).status_code, 409)
            for value in (None, True, -1, "1"):
                self.assertEqual(self.post(action, {"expectedRevision": value}).status_code, 400)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, "active")

    def test_archive_is_blocked_by_running_sync_or_queued_job(self):
        for kind in ("run", "job"):
            with self.subTest(kind=kind), transaction.atomic():
                if kind == "run":
                    SyncRun.objects.create(source=self.source, status="running", started_at=timezone.now())
                else:
                    ResyncJob.objects.create(source=self.source, request_key=uuid.uuid4())
                self.assertEqual(self.post("archive").status_code, 409)
                self.source.refresh_from_db()
                self.assertEqual(self.source.status, "active")
                transaction.set_rollback(True)

    def test_archive_blocks_new_sync_and_restore_remains_inactive(self):
        ScheduleConfig.objects.create(source=self.source, enabled=True, next_run=timezone.now())
        self.assertEqual(self.post("archive").status_code, 200)
        self.assertNotIn(self.source.source_id, self.client.get("/api/admin/schedules/").content.decode())
        self.assertNotIn(self.source.source_id, self.client.get("/api/admin/schedules/next/").content.decode())
        self.assertTrue(ScheduleConfig.objects.filter(source=self.source, enabled=True).exists())
        with self.assertRaises(InactiveSourceError):
            begin_sync_run(source=self.source)
        self.assertEqual(self.post("restore", {"expectedRevision": 2}).status_code, 200)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, "inactive")
        self.assertEqual(self.source.revisions.count(), 3)

    def test_archive_hides_catalogue_but_preserves_public_history(self):
        indicator = Indicator.objects.create(code="SYN_TEST", name="SYN", category="TEST", unit="%")
        observation = Observation.objects.create(
            source=self.source, indicator=indicator, observation_date=date(2024, 1, 1),
            period_label="2024", frequency="annual", data_type="level", value="1", unit="%",
            validation_status="published", reviewed_by=self.user, reviewed_at=timezone.now(),
        )
        self.assertEqual(self.post("archive").status_code, 200)
        self.assertTrue(Observation.objects.filter(pk=observation.pk, source=self.source).exists())
        from indicators.views import ordered_sources, published_observations
        self.assertNotIn(self.source, ordered_sources())
        self.assertTrue(published_observations(indicator).filter(pk=observation.pk).exists())

    def test_delete_rejects_each_relation_and_snapshot(self):
        indicator = Indicator.objects.create(code="SYN_TEST", name="SYN", category="TEST", unit="%")
        cases = {
            "raw": lambda: RawFile.objects.create(source=self.source, document_name="test", checksum_sha256="a" * 64),
            "observation": lambda: Observation.objects.create(
                source=self.source, indicator=indicator, observation_date=date(2024, 1, 1),
                period_label="2024", frequency="annual", data_type="level", value="1", unit="%",
            ),
            "candidate": lambda: ObservationCandidate.objects.create(
                source=self.source, indicator=indicator, payload={}, base_snapshot={}, fingerprint="b" * 64,
            ),
            "bulk": lambda: BulkCandidateReview.objects.create(
                source=self.source, reviewer=self.user, expires_at=timezone.now(),
            ),
            "job": lambda: ResyncJob.objects.create(source=self.source, request_key=uuid.uuid4(), status="success"),
            "schedule": lambda: ScheduleConfig.objects.create(source=self.source),
            "run": lambda: SyncRun.objects.create(source=self.source, status="success", started_at=timezone.now()),
            "run_snapshot": lambda: SyncRun.objects.create(
                source_id_snapshot=self.source.source_id, status="success", started_at=timezone.now(),
            ),
            "schedule_snapshot": lambda: ScheduleAudit.objects.create(source_id_snapshot=self.source.source_id),
            "legacy_log": lambda: DataUpdateLog.objects.create(source=self.source.institution),
        }
        for kind, create in cases.items():
            with self.subTest(kind=kind), transaction.atomic():
                item = create()
                self.assertEqual(self.post("delete").status_code, 409, kind)
                self.assertTrue(Source.objects.filter(pk=self.source.pk).exists())
                self.assertTrue(type(item).objects.filter(pk=item.pk).exists())
                transaction.set_rollback(True)

    def test_known_import_master_cannot_be_deleted(self):
        self.source = Source.objects.get(source_id="BPS")
        version = self.source.revisions.order_by("-version").values_list("version", flat=True).first() or 0
        self.assertEqual(self.post("delete", {"expectedRevision": version}).status_code, 409)
