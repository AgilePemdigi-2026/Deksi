"""Feature 27: restore default aman, beraudit, tanpa ubah formula/data."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from indicators.models import DataUpdateLog, Observation
from indicators.notification_model import NotificationAudit, NotificationPreference


class ConfigRestoreTests(TestCase):
    def setUp(self):
        um = get_user_model()
        self.admin = um.objects.create_user(username="restore-admin", password="x", is_staff=True)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_restore_notifications_to_defaults(self):
        NotificationPreference.objects.create(kind="sync_failed", enabled=False, version=5)
        r = self.client.post("/api/admin/config/restore/",
            data=json.dumps({"domains": ["notifications"]}),
            content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "Konfigurasi dikembalikan ke pengaturan awal")
        pref = NotificationPreference.objects.get(kind="sync_failed")
        self.assertTrue(pref.enabled)
        self.assertGreater(pref.version, 5)
        self.assertTrue(NotificationAudit.objects.filter(
            kind="sync_failed", reason="restore-default").exists())

    def test_cancel_semantics_invalid_domain_rejected(self):
        r = self.client.post("/api/admin/config/restore/",
            data=json.dumps({"domains": ["core_formula"]}),
            content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_unsupported_domains_reported_not_invented(self):
        r = self.client.post("/api/admin/config/restore/",
            data=json.dumps({"domains": ["schedules", "thresholds"]}),
            content_type="application/json")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        statuses = {i["status"] for items in results.values() for i in items}
        self.assertTrue(statuses <= {"restored", "restored-empty", "skipped-unsupported"})

    def test_restore_does_not_touch_data_or_logs(self):
        obs_count = Observation.objects.count()
        log_count = DataUpdateLog.objects.count()
        self.client.post("/api/admin/config/restore/",
            data=json.dumps({"domains": ["notifications"]}),
            content_type="application/json")
        self.assertEqual(Observation.objects.count(), obs_count)
        self.assertEqual(DataUpdateLog.objects.count(), log_count)

    def test_unauth_rejected(self):
        r = Client().post("/api/admin/config/restore/",
            data=json.dumps({}), content_type="application/json")
        self.assertEqual(r.status_code, 401)
