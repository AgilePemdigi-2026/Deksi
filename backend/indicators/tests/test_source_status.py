import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase

from indicators import bps, fiscal, ingest
from indicators.models import DataUpdateLog, Source, SourceRevision


class SourceStatusTests(TestCase):
    def test_inactive_bps_stops_before_fetch(self):
        source = bps._get_or_create_source()
        source.status = "inactive"
        source.save(update_fields=["status"])
        with patch("indicators.bps.fetch_series", side_effect=AssertionError("inactive source fetched")) as fetch:
            with self.assertRaises(ValidationError):
                bps.sync_bps_indicators()
        fetch.assert_not_called()

    def test_inactive_kemenkeu_stops_before_fetch(self):
        source = fiscal.get_kemenkeu_source()
        source.status = "inactive"
        source.save(update_fields=["status"])
        with patch("indicators.fiscal.kemenkeu.fetch_and_parse", side_effect=AssertionError("inactive source fetched")):
            with self.assertRaises(ValidationError):
                fiscal.ingest_kita_pdf_url("https://example.test/report.pdf")

    def test_inactive_kemenkeu_command_stops_before_discovery(self):
        source = fiscal.get_kemenkeu_source()
        source.status = "inactive"
        source.save(update_fields=["status"])
        before = DataUpdateLog.objects.count()
        output = StringIO()
        with patch("indicators.kemenkeu_discovery.discover_via_anggaran_search",
                   side_effect=AssertionError("discovery called")) as discover:
            call_command("fetch_kemenkeu", discover=True, stdout=output)
        discover.assert_not_called()
        self.assertIn("tidak aktif", output.getvalue().lower())
        self.assertEqual(DataUpdateLog.objects.count(), before)

    def test_inactive_local_sources_do_not_import_files(self):
        with tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            ingest.ingest_local_datasets(Path(directory))
            Source.objects.filter(source_id__in=["BI", "BKPM"]).update(status="inactive")
            (Path(directory) / "bi-7day-rr.xlsx").touch()
            (Path(directory) / "triwulan-i-tahun-2024.zip").touch()
            with patch("indicators.ingest.save_raw_from_path", side_effect=AssertionError("inactive source imported")):
                result = ingest.ingest_local_datasets(Path(directory))
            self.assertEqual(result["bi_rows"], 0)
            self.assertEqual(result["bkpm_quarters"], 0)

    def test_admin_status_change_requires_csrf(self):
        source = Source.objects.create(
            source_id="FIXTURE", source_name="Fixture", institution="Fixture",
            primary_url="https://example.test/", acquisition_method="file_xlsx",
            data_format="xlsx", frequency="monthly",
        )
        user = get_user_model().objects.create_user(username="fixture-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        response = client.patch(
            "/api/admin/sources/FIXTURE/update/", '{"status":"inactive"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        source.refresh_from_db()
        self.assertEqual(source.status, "active")

    def test_admin_can_toggle_with_csrf_and_preserve_separate_audit(self):
        source = Source.objects.create(
            source_id="FIXTURE", source_name="Fixture", institution="Fixture",
            primary_url="https://example.test/", acquisition_method="file_xlsx",
            data_format="xlsx", frequency="monthly",
        )
        user = get_user_model().objects.create_user(username="fixture-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        log_count = DataUpdateLog.objects.count()
        for version, status in enumerate(("inactive", "active")):
            response = client.patch(
                "/api/admin/sources/FIXTURE/update/", '{"status":"' + status + '","expectedRevision":' + str(version) + '}',
                content_type="application/json", HTTP_X_CSRFTOKEN=token,
            )
            self.assertEqual(response.status_code, 200)
            source.refresh_from_db()
            self.assertEqual(source.status, status)
        self.assertEqual(SourceRevision.objects.filter(source=source).count(), 2)
        self.assertEqual(DataUpdateLog.objects.count(), log_count)
