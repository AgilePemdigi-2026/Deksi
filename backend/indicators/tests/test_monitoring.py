"""Feature 19: monitoring admin memakai data aktual."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from indicators.models import Source
from indicators.sync_history_model import SyncRun


class MonitoringTests(TestCase):
    def setUp(self):
        um = get_user_model()
        self.admin = um.objects.create_user(username="mon-admin", password="x", is_staff=True)
        self.client = Client()
        self.client.force_login(self.admin)
        self.src = Source.objects.create(
            source_id="BPS", source_name="Badan Pusat Statistik",
            institution="BPS", primary_url="https://bps.go.id",
        )
        SyncRun.objects.create(
            source=self.src, source_id_snapshot="BPS",
            source_name_snapshot="Badan Pusat Statistik",
            status=SyncRun.Status.SUCCESS,
            started_at=timezone.now(), finished_at=timezone.now(), item_count=5,
        )

    def test_summary_reflects_db(self):
        r = self.client.get("/api/admin/monitoring/summary/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["totalSources"], 1)
        self.assertEqual(d["activeSources"], 1)
        self.assertEqual(d["syncSuccess"], 1)

    def test_sources_and_history(self):
        r = self.client.get("/api/admin/monitoring/sources/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["sources"]), 1)
        r = self.client.get("/api/admin/monitoring/history/?page=1&pageSize=10")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 1)

    def test_unauth_rejected(self):
        c = Client()
        r = c.get("/api/admin/monitoring/summary/")
        self.assertEqual(r.status_code, 401)
