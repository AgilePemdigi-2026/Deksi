from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase

from indicators import bps, fiscal
from indicators.models import DataUpdateLog, Source, SourceRevision


class SourceStatusReviewTests(TestCase):
    def test_status_only_preserves_changes_made_after_initial_lookup(self):
        source = Source.objects.create(source_id="RACE", source_name="Old", institution="Fixture", primary_url="https://example.test/")
        stale = Source.objects.get(pk=source.pk)
        Source.objects.filter(pk=source.pk).update(source_name="New")
        user = get_user_model().objects.create_user(username="review-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        with patch("indicators.source_admin_views._get_staff_source", return_value=(stale, None)):
            response = client.patch(
                "/api/admin/sources/RACE/update/", '{"status":"inactive","expectedRevision":0}',
                content_type="application/json", HTTP_X_CSRFTOKEN=token,
            )
        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        self.assertEqual(source.source_name, "New")
        revision = SourceRevision.objects.get(source=source)
        self.assertEqual(revision.before["sourceName"], "New")

    def test_inactive_bps_command_is_skipped_without_failure_log(self):
        source = bps._get_or_create_source()
        source.status = "inactive"
        source.save(update_fields=["status"])
        before = DataUpdateLog.objects.count()
        output = StringIO()
        with patch("indicators.bps.fetch_series", side_effect=AssertionError("unexpected provider access")):
            call_command("sync_bps", stdout=output)
        self.assertEqual(DataUpdateLog.objects.count(), before)
        self.assertIn("tidak aktif", output.getvalue().lower())

    def test_metadata_edit_records_revision_not_data_update(self):
        source = Source.objects.create(
            source_id="META", source_name="Old", institution="Fixture", primary_url="https://example.test/",
            acquisition_method="file_xlsx", data_format="xlsx", frequency="monthly",
        )
        user = get_user_model().objects.create_user(username="metadata-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        before = DataUpdateLog.objects.count()
        response = client.patch(
            "/api/admin/sources/META/update/", '{"sourceName":"New","expectedRevision":0}',
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SourceRevision.objects.filter(source=source).exists())
        self.assertEqual(DataUpdateLog.objects.count(), before)

    def test_stale_form_revision_is_rejected_without_overwriting_source(self):
        source = Source.objects.create(
            source_id="STALE", source_name="Old", institution="Fixture",
            primary_url="https://example.test/", acquisition_method="file_xlsx",
            data_format="xlsx", frequency="monthly",
        )
        user = get_user_model().objects.create_user(username="stale-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        first = client.patch(
            "/api/admin/sources/STALE/update/", '{"status":"inactive","expectedRevision":0}',
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(first.status_code, 200)
        second = client.patch(
            "/api/admin/sources/STALE/update/",
            '{"expectedRevision":0,"sourceName":"Edited","status":"active"}',
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(second.status_code, 409)
        source.refresh_from_db()
        self.assertEqual((source.source_name, source.status), ("Old", "inactive"))

    def test_kemenkeu_deactivated_after_command_start_is_not_recorded_as_failure(self):
        source = fiscal.get_kemenkeu_source()
        before = DataUpdateLog.objects.count()

        def deactivate(*args, **kwargs):
            Source.objects.filter(pk=source.pk).update(status="inactive")
            return fiscal.ingest_kita_pdf_bytes(b"test", "fixture.pdf")

        with patch("indicators.fiscal.ingest_kita_pdf_url", side_effect=deactivate):
            call_command("fetch_kemenkeu", urls=["https://example.test/fixture.pdf"], stdout=StringIO())
        self.assertEqual(DataUpdateLog.objects.count(), before)
