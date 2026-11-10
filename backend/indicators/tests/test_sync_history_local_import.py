import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import TestCase

from indicators.ingest import ingest_local_datasets
from indicators.models import Source
from indicators.sync_history_model import SyncRun


class LocalImportSyncHistoryTests(TestCase):
    def test_inactive_sources_create_no_runs(self):
        with TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            ingest_local_datasets(Path(directory))
            Source.objects.filter(source_id__in=["BI", "BKPM"]).update(status="inactive")
            result = ingest_local_datasets(Path(directory))
        self.assertEqual(result["skipped_inactive"], ["BI", "BKPM"])
        self.assertFalse(SyncRun.objects.filter(source_id_snapshot__in=["BI", "BKPM"]).exists())

    def test_empty_active_import_does_not_invent_runs(self):
        with TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            ingest_local_datasets(Path(directory))
        self.assertFalse(SyncRun.objects.exists())

    def test_partial_failure_records_failed_without_exception_text(self):
        with TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            Path(directory, "bi-7day-rr.xlsx").touch()
            with patch("indicators.ingest.save_raw_from_path", side_effect=RuntimeError("secret detail")):
                result = ingest_local_datasets(Path(directory))
        failed = SyncRun.objects.get(source_id_snapshot="BI")
        self.assertEqual(failed.status, SyncRun.Status.FAILED)
        self.assertNotIn("secret detail", failed.safe_message or "")
        self.assertFalse(SyncRun.objects.filter(source_id_snapshot="BKPM").exists())
        self.assertTrue(result["errors"])

    def test_successful_bi_file_records_one_successful_run(self):
        with TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            Path(directory, "bi-7day-rr.xlsx").touch()
            with patch("indicators.ingest.save_raw_from_path", return_value=(Mock(), False)), \
                 patch("indicators.ingest.parse_bi_rr_xlsx", return_value=[]):
                result = ingest_local_datasets(Path(directory))
        self.assertEqual(result["errors"], [])
        run = SyncRun.objects.get(source_id_snapshot="BI")
        self.assertEqual(run.status, SyncRun.Status.SUCCESS)
        self.assertIsNone(run.item_count)
        self.assertFalse(SyncRun.objects.filter(source_id_snapshot="BKPM").exists())
