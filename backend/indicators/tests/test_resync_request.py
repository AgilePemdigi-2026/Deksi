import json
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from indicators.models import Source
from indicators.resync_model import ResyncJob
from indicators.sync_history_service import begin_sync_run, create_sync_run


class ResyncRequestTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="resync-staff", is_staff=True)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.staff)
        self.csrf = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.source = Source.objects.create(
            source_id="BPS", source_name="Synthetic BPS", institution="Synthetic",
            primary_url="https://example.test/",
        )

    def test_staff_request_is_queued_without_contacting_provider(self):
        from unittest.mock import patch

        token = str(uuid.uuid4())
        with patch("indicators.bps.fetch_series", side_effect=AssertionError("unexpected provider call")):
            response = self.client.post(
                "/api/admin/sources/BPS/resync/", json.dumps({"requestId": token}),
                content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf,
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "queued")
        self.assertIsNotNone(response.json()["id"])

    def post(self, source="BPS", data=None):
        return self.client.post(
            f"/api/admin/sources/{source}/resync/", json.dumps(data or {"requestId": str(uuid.uuid4())}),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf,
        )

    def test_same_request_key_is_idempotent_and_other_key_conflicts(self):
        data = {"requestId": str(uuid.uuid4())}
        first, again, other = self.post(data=data), self.post(data=data), self.post()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(again.status_code, 202)
        self.assertEqual(first.json()["id"], again.json()["id"])
        self.assertEqual(other.status_code, 409)
        self.assertEqual(ResyncJob.objects.count(), 1)

    def test_existing_active_run_prevents_queue(self):
        create_sync_run(source=self.source)
        self.assertEqual(self.post().status_code, 409)
        self.assertFalse(ResyncJob.objects.exists())

    def test_queued_request_blocks_other_sync_entry_points(self):
        self.assertEqual(self.post().status_code, 202)
        with self.assertRaises(ValidationError):
            begin_sync_run(source=self.source)

    def test_staff_can_read_queued_status_but_nonstaff_cannot(self):
        job_id = self.post().json()["id"]
        url = f"/api/admin/resync-jobs/{job_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "queued")
        self.assertIsNone(response.json()["runId"])
        self.assertNotIn("requestId", response.json())
        nonstaff = get_user_model().objects.create_user(username="status-nonstaff", is_staff=False)
        self.client.force_login(nonstaff)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_can_discover_queued_job_after_lost_response_or_refresh(self):
        accepted = self.post().json()
        response = self.client.get("/api/admin/sources/BPS/resync-active/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["id"], accepted["id"])
        self.assertEqual(response.json()["job"]["status"], "queued")
        self.assertNotIn("requestId", response.json()["job"])
        self.client.logout()
        self.assertEqual(self.client.get("/api/admin/sources/BPS/resync-active/").status_code, 401)

    def test_nonstaff_anonymous_and_missing_csrf_are_rejected(self):
        nonstaff = get_user_model().objects.create_user(username="resync-nonstaff", is_staff=False)
        self.client.force_login(nonstaff)
        self.csrf = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.assertEqual(self.post().status_code, 403)
        self.client.logout()
        self.csrf = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.assertEqual(self.post().status_code, 401)
        self.client.force_login(self.staff)
        response = self.client.post("/api/admin/sources/BPS/resync/", json.dumps({"requestId": str(uuid.uuid4())}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_inactive_unsupported_and_injected_fields_are_rejected(self):
        self.source.status = Source.SourceStatus.INACTIVE
        self.source.save(update_fields=["status"])
        self.assertEqual(self.post().status_code, 409)
        unsupported = Source.objects.create(source_id="BI", source_name="BI", institution="Synthetic",
                                            primary_url="https://example.test/")
        self.assertEqual(self.post(source=unsupported.source_id).status_code, 400)
        response = self.post(data={"requestId": str(uuid.uuid4()), "url": "https://example.test/"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ResyncJob.objects.exists())
