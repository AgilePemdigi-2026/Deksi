"""Feature 26: preferensi tersimpan, pemicu mengikuti konfigurasi, audit tercatat."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from indicators.models import Source
from indicators.notification_model import (
    NotificationAudit,
    NotificationEvent,
    NotificationPreference,
)
from indicators.notification_service import should_notify
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import finalize_sync_run


class NotificationTests(TestCase):
    def setUp(self):
        um = get_user_model()
        self.admin = um.objects.create_user(username="notif-admin", password="x", is_staff=True)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_defaults_without_rows(self):
        self.assertTrue(should_notify(NotificationPreference.Kind.SYNC_FAILED))
        self.assertFalse(should_notify(NotificationPreference.Kind.THRESHOLD_EXCEEDED))

    def test_toggle_persist_and_audit(self):
        r = self.client.put("/api/admin/notifications/sync_failed/",
            data=json.dumps({"enabled": False}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(NotificationPreference.objects.get(kind="sync_failed").enabled)
        self.assertEqual(NotificationAudit.objects.filter(kind="sync_failed").count(), 1)
        self.assertFalse(should_notify("sync_failed"))

    def test_invalid_kind_and_payload_rejected(self):
        r = self.client.put("/api/admin/notifications/sms/",
            data=json.dumps({"enabled": True}), content_type="application/json")
        self.assertEqual(r.status_code, 404)
        r = self.client.put("/api/admin/notifications/sync_failed/",
            data=json.dumps({"enabled": "yes"}), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_sync_failure_logged_and_notified_per_preference(self):
        src = Source.objects.create(source_id="NOTIFTEST", source_name="BPS",
            institution="BPS", primary_url="https://bps.go.id")
        run = SyncRun.objects.create(source=src, source_id_snapshot="BPS",
            source_name_snapshot="BPS", status=SyncRun.Status.RUNNING,
            started_at=timezone.now())
        finalize_sync_run(run, success=False)
        ev = NotificationEvent.objects.filter(kind="sync_failed").first()
        self.assertIsNotNone(ev)
        self.assertTrue(ev.notified)
        # Matikan preferensi: event tetap tercatat, notified False.
        NotificationPreference.objects.create(kind="sync_failed", enabled=False)
        run2 = SyncRun.objects.create(source=src, source_id_snapshot="BPS",
            source_name_snapshot="BPS", status=SyncRun.Status.RUNNING,
            started_at=timezone.now())
        finalize_sync_run(run2, success=False)
        ev2 = NotificationEvent.objects.order_by("-id").first()
        self.assertFalse(ev2.notified)
        self.assertEqual(NotificationEvent.objects.count(), 2)

    def test_unauth_rejected(self):
        r = Client().get("/api/admin/notifications/")
        self.assertEqual(r.status_code, 401)

    def test_list_shows_supported_kinds(self):
        r = self.client.get("/api/admin/notifications/")
        self.assertEqual(r.status_code, 200)
        kinds = {n["kind"] for n in r.json()["notifications"]}
        self.assertEqual(kinds, {"sync_failed", "threshold_exceeded", "validation_failed"})
