from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase

from indicators import fiscal
from indicators.models import DataUpdateLog, RawFile, Source


class SourceStatusExtraTests(TestCase):
    def test_inactive_kemenkeu_stops_local_pdf_before_parsing(self):
        source = fiscal.get_kemenkeu_source()
        source.status = "inactive"
        source.save(update_fields=["status"])
        with patch("indicators.fiscal.kemenkeu.pdf_to_text", side_effect=AssertionError("inactive PDF parsed")):
            with self.assertRaises(ValidationError):
                fiscal.ingest_kita_pdf_bytes(b"not a real PDF", "fixture.pdf")

    def test_non_staff_cannot_change_source_status(self):
        source = Source.objects.create(source_id="DENIED", source_name="Denied", institution="Fixture",
                                       primary_url="https://example.test/", acquisition_method="file_xlsx",
                                       data_format="xlsx", frequency="monthly")
        user = get_user_model().objects.create_user(username="ordinary", is_staff=False)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.patch("/api/admin/sources/DENIED/update/", '{"status":"inactive"}',
                                content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 403)
        source.refresh_from_db()
        self.assertEqual(source.status, "active")

    def test_status_change_preserves_existing_raw_record(self):
        source = Source.objects.create(source_id="FIXTURE", source_name="Fixture", institution="Fixture",
                                       primary_url="https://example.test/", acquisition_method="file_xlsx",
                                       data_format="xlsx", frequency="monthly")
        raw = RawFile.objects.create(source=source, document_name="old.pdf", checksum_sha256="a" * 64)
        user = get_user_model().objects.create_user(username="fixture-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.patch("/api/admin/sources/FIXTURE/update/", '{"status":"inactive","expectedRevision":0}',
                                content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RawFile.objects.filter(pk=raw.pk, source=source).exists())

    def test_combined_status_edit_does_not_record_data_update(self):
        source = Source.objects.create(source_id="MIXED", source_name="Original", institution="Fixture",
                                       primary_url="https://example.test/", acquisition_method="file_xlsx",
                                       data_format="xlsx", frequency="monthly")
        user = get_user_model().objects.create_user(username="fixture-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        before = DataUpdateLog.objects.count()
        response = client.patch("/api/admin/sources/MIXED/update/", '{"status":"inactive","sourceName":"Changed","expectedRevision":0}',
                                content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        self.assertEqual(source.status, "inactive")
        self.assertEqual(DataUpdateLog.objects.count(), before)

    def test_dry_run_does_not_create_missing_source(self):
        with patch("indicators.kemenkeu_discovery.discover_via_anggaran_search", return_value=[]), \
             patch("indicators.management.commands.fetch_kemenkeu.discover_kita_urls", return_value=[]):
            with self.assertRaises(SystemExit):
                call_command("fetch_kemenkeu", discover=True, dry_run=True)
        self.assertFalse(Source.objects.filter(source_id="KEMENKEU").exists())

    def test_status_edit_does_not_probe_admin_supplied_url(self):
        Source.objects.create(source_id="URL", source_name="Fixture", institution="Fixture",
                              primary_url="https://example.test/", acquisition_method="file_xlsx",
                              data_format="xlsx", frequency="monthly")
        user = get_user_model().objects.create_user(username="fixture-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        with patch("indicators.source_admin_views._probe_endpoint_reachable",
                   side_effect=AssertionError("untrusted endpoint probed")):
            response = client.patch(
                "/api/admin/sources/URL/update/",
                '{"status":"inactive","endpointUrl":"https://example.test/path","expectedRevision":0}',
                content_type="application/json", HTTP_X_CSRFTOKEN=token,
            )
        self.assertEqual(response.status_code, 200)

    def test_admin_login_update_and_logout_use_real_session_and_csrf(self):
        Source.objects.create(source_id="FLOW", source_name="Fixture", institution="Fixture",
                              primary_url="https://example.test/", acquisition_method="file_xlsx",
                              data_format="xlsx", frequency="monthly")
        user = get_user_model().objects.create_user(username="flow-admin", is_staff=True)
        user.set_password("synthetic-password-for-tests")
        user.save()
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.post(
            "/api/admin/login/", '{"username":"flow-admin","password":"synthetic-password-for-tests"}',
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.patch("/api/admin/sources/FLOW/update/", '{"status":"inactive","expectedRevision":0}',
                                content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Source.objects.get(source_id="FLOW").status, "inactive")
        response = client.post("/api/admin/logout/", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(client.get("/api/admin/session/").json()["authenticated"])

    def test_status_only_update_works_for_legacy_incomplete_source(self):
        source = Source.objects.create(source_id="LEGACY", source_name="Legacy", institution="Fixture",
                                       primary_url="https://example.test/")
        user = get_user_model().objects.create_user(username="fixture-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.patch("/api/admin/sources/LEGACY/update/", '{"status":"inactive","expectedRevision":0}',
                                content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        self.assertEqual(source.status, "inactive")
        self.assertEqual(source.acquisition_method, "")
