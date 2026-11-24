from django.test import TestCase

from indicators.models import Source
from indicators.source_status import InactiveSourceError
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import begin_sync_run, finalize_sync_run


class SyncProcessSafetyTests(TestCase):
    def setUp(self):
        self.source = Source.objects.create(
            source_id="SAFETY_TEST", source_name="Safety source", institution="Test",
            primary_url="https://example.test/",
        )

    def test_inactive_source_cannot_start_or_record_run(self):
        self.source.status = Source.SourceStatus.INACTIVE
        self.source.save(update_fields=["status"])
        with self.assertRaises(InactiveSourceError):
            begin_sync_run(source=self.source)
        self.assertFalse(SyncRun.objects.exists())

    def test_start_records_running_and_finalization_keeps_unknown_count_null(self):
        run = begin_sync_run(source=self.source)
        self.assertEqual(run.status, SyncRun.Status.RUNNING)
        finalize_sync_run(run, success=True)
        run.refresh_from_db()
        self.assertEqual(run.status, SyncRun.Status.SUCCESS)
        self.assertIsNone(run.item_count)
        self.assertIsNone(run.actor_id)

    def test_local_bi_and_bkpm_runs_are_separate_and_empty_input_is_not_a_run(self):
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock, patch

        from indicators.ingest import ingest_local_datasets

        with TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            root = Path(directory)
            (root / "bi-7day-rr.xlsx").touch()
            (root / "Realisasi-triwulan-i-tahun-2025.zip").touch()
            with patch("indicators.ingest.save_raw_from_path", return_value=(Mock(), False)), \
                 patch("indicators.ingest.parse_bi_rr_xlsx", side_effect=ValueError("offline parse failure")), \
                 patch("indicators.ingest.sum_bkpm_zip_csv", side_effect=ValueError("offline csv failure")):
                ingest_local_datasets(root)
        runs = list(SyncRun.objects.order_by("source_id_snapshot"))
        self.assertEqual([run.source_id_snapshot for run in runs], ["BI", "BKPM"])
        self.assertEqual(runs[0].status, SyncRun.Status.FAILED)
        self.assertEqual(runs[1].status, SyncRun.Status.FAILED)

    def test_deactivation_race_for_bi_does_not_prevent_bkpm_start(self):
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from indicators.ingest import ingest_local_datasets
        from indicators.sync_history_service import begin_sync_run as real_begin

        def deactivate_bi(*, source):
            if source.source_id == "BI":
                Source.objects.filter(pk=source.pk).update(status=Source.SourceStatus.INACTIVE)
            return real_begin(source=source)

        with TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"]) as directory:
            root = Path(directory)
            (root / "bi-7day-rr.xlsx").touch()
            (root / "bad.zip").touch()
            with patch("indicators.sync_history_service.begin_sync_run", side_effect=deactivate_bi):
                result = ingest_local_datasets(root)
        self.assertFalse(SyncRun.objects.filter(source_id_snapshot="BI").exists())
        self.assertEqual(SyncRun.objects.get(source_id_snapshot="BKPM").status, SyncRun.Status.FAILED)
        self.assertIn("BI", result["skipped_inactive"])
