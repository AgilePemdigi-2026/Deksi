"""Feature 23: jadwal valid, invalid ditolak, audit tercatat."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from indicators.models import Source
from indicators.schedule_model import ScheduleAudit, ScheduleConfig


class ScheduleTests(TestCase):
    def setUp(self):
        um = get_user_model()
        self.admin = um.objects.create_user(username="sched-admin", password="x", is_staff=True)
        self.client = Client()
        self.client.force_login(self.admin)
        self.src = Source.objects.create(
            source_id="BPS", source_name="BPS", institution="BPS",
            primary_url="https://bps.go.id",
        )

    def test_valid_save_and_audit(self):
        r = self.client.put(
            "/api/admin/schedules/BPS/",
            data=json.dumps({"intervalDays": 30, "runTime": "02:00", "enabled": True}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("Konfigurasi tersimpan", r.json()["message"])
        self.assertEqual(ScheduleConfig.objects.count(), 1)
        self.assertEqual(ScheduleAudit.objects.count(), 1)
        self.src.refresh_from_db()
        self.assertIn("30 hari", self.src.update_schedule)

    def test_invalid_interval_rejected_and_old_kept(self):
        self.client.put("/api/admin/schedules/BPS/",
            data=json.dumps({"intervalDays": 30, "enabled": True}),
            content_type="application/json")
        r = self.client.put("/api/admin/schedules/BPS/",
            data=json.dumps({"intervalDays": 0, "enabled": True}),
            content_type="application/json")
        self.assertEqual(r.status_code, 400)
        cfg = ScheduleConfig.objects.get(source=self.src)
        self.assertEqual(cfg.interval_days, 30)

    def test_invalid_time_format(self):
        r = self.client.put("/api/admin/schedules/BPS/",
            data=json.dumps({"intervalDays": 7, "runTime": "25:99", "enabled": True}),
            content_type="application/json")
        self.assertEqual(r.status_code, 400)
