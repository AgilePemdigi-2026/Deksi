"""Focused tests for isolated sync-history model/service/view behavior."""
import json
from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from indicators import bps, fiscal
from indicators.models import DataUpdateLog, Source
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import create_sync_run, finalize_sync_run
from indicators.sync_history_views import admin_sync_history


class SyncHistoryTests(TestCase):

    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="history-staff", is_staff=True)
        self.nonstaff = get_user_model().objects.create_user(username="history-user", is_staff=False)
        self.source = Source.objects.create(
            source_id="SYNC_TEST", source_name="Synthetic source", institution="Synthetic",
            primary_url="https://example.test/",
        )
        self.factory = RequestFactory()

    def request(self, query="", user=None):
        request = self.factory.get("/api/admin/sync-history/" + query)
        request.user = user or self.staff
        return admin_sync_history(request)

    def test_create_finalize_statuses_and_redacted_messages(self):
        run = create_sync_run(source=self.source, actor=self.staff)
        self.assertEqual(run.status, SyncRun.Status.RUNNING)
        self.assertIsNone(run.item_count)
        self.assertEqual(run.source_id_snapshot, "SYNC_TEST")
        self.assertEqual(run.source_name_snapshot, "Synthetic source")
        done = finalize_sync_run(run, success=True, item_count=4)
        failed = finalize_sync_run(create_sync_run(), success=False, item_count=None)
        self.assertEqual(done.status, "success")
        self.assertEqual(done.item_count, 4)
        self.assertEqual(failed.status, "failed")
        self.assertIsNone(failed.item_count)
        self.assertNotIn("Traceback", failed.safe_message)
        self.assertNotIn("password", failed.safe_message.lower())

    def test_permissions_filters_pagination_and_nulls(self):
        denied = self.request(user=self.nonstaff)
        self.assertEqual(denied.status_code, 403)
        first = create_sync_run(source=self.source, started_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
        finalize_sync_run(first, success=True, item_count=2)
        second = create_sync_run(started_at=datetime(2025, 1, 2, tzinfo=timezone.utc))
        response = self.request("?page=1&pageSize=1&status=running")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["pagination"], {"page": 1, "pageSize": 1, "total": 1, "hasNext": False})
        self.assertIsNone(payload["items"][0]["sourceId"])
        self.assertIsNone(payload["items"][0]["finishedAt"])
        self.assertIsNone(payload["items"][0]["actor"])
        self.assertIsNone(payload["items"][0]["itemCount"])
        self.assertIsNone(payload["items"][0]["message"])
        source_response = self.request("?sourceId=SYNC_TEST")
        self.assertEqual(json.loads(source_response.content)["pagination"]["total"], 1)
        self.assertEqual(str(second.pk), payload["items"][0]["id"])

    def test_validation_and_legacy_log_is_not_included(self):
        DataUpdateLog.objects.create(source="legacy only", message="must not appear")
        for query in ("?page=0", "?pageSize=101", "?page=x", "?status=other", "?page=1&page=2", "?unknown=1"):
            with self.subTest(query=query):
                self.assertEqual(self.request(query).status_code, 400)
        response = self.request()
        self.assertEqual(json.loads(response.content)["pagination"]["total"], 0)
        self.assertEqual(json.loads(response.content)["items"], [])

    def test_api_requires_staff_and_rejects_extreme_page(self):
        self.assertEqual(self.client.get("/api/admin/sync-history/").status_code, 401)
        self.client.force_login(self.nonstaff)
        self.assertEqual(self.client.get("/api/admin/sync-history/").status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/api/admin/sync-history/?page=99999999999999999999").status_code, 400)

    def test_source_delete_preserves_snapshot(self):
        run = create_sync_run(source=self.source)
        self.source.delete()
        run.refresh_from_db()
        self.assertIsNone(run.source_id)
        self.assertEqual(run.source_id_snapshot, "SYNC_TEST")
        self.assertEqual(run.source_name_snapshot, "Synthetic source")

    def test_bps_run_records_success_and_failure_without_provider(self):
        with patch.object(bps, "BPS_SERIES", []):
            bps.sync_bps_indicators()
        run = SyncRun.objects.get(source_id_snapshot="BPS")
        self.assertEqual(run.status, "success")
        self.assertIsNone(run.item_count)
        self.assertIsNotNone(run.finished_at)
        with patch.object(bps, "BPS_SERIES", [{}]), \
             patch.object(bps, "_get_or_create_indicator", side_effect=RuntimeError("secret error")):
            with self.assertRaises(RuntimeError):
                bps.sync_bps_indicators()
        failed = SyncRun.objects.filter(status="failed").get()
        self.assertNotIn("secret error", failed.safe_message)

    def test_kemenkeu_records_failure_without_raw_provider_error(self):
        with patch("indicators.fiscal.kemenkeu.fetch_and_parse", side_effect=RuntimeError("private-provider-value")):
            with self.assertRaises(RuntimeError):
                fiscal.ingest_kita_pdf_url("https://example.test/report.pdf")
        run = SyncRun.objects.get(source_id_snapshot="KEMENKEU")
        self.assertEqual(run.status, "failed")
        self.assertNotIn("private-provider-value", run.safe_message)
