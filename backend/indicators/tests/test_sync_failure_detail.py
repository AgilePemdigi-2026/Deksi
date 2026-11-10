import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import TestCase

from indicators import bps, fiscal, ingest
from indicators.models import RawFile
from indicators.sync_history_model import SyncRun


class SyncFailureDetailTests(TestCase):
    def test_bps_fetch_failure_records_safe_stage_without_raw_error(self):
        with patch.object(bps, 'BPS_SERIES', [{'code': 'synthetic'}]), \
             patch.object(bps, '_get_or_create_indicator'), \
             patch.object(bps, 'fetch_series', side_effect=bps.BpsError('sensitive-fixture-url-token')):
            bps.sync_bps_indicators()
        run = SyncRun.objects.get(source_id_snapshot='BPS')
        self.assertEqual(run.status, 'failed')
        self.assertIn('pengambilan data', run.safe_message.lower())
        self.assertNotIn('sensitive-fixture-url-token', run.safe_message)

    def test_kemenkeu_fetch_or_parse_failure_exposes_stage_not_exception(self):
        with patch('indicators.fiscal.kemenkeu.fetch_and_parse', side_effect=RuntimeError('private-fixture-token')):
            with self.assertRaises(RuntimeError):
                fiscal.ingest_kita_pdf_url('https://example.test/synthetic.pdf')
        run = SyncRun.objects.get(source_id_snapshot='KEMENKEU')
        self.assertIn('pengambilan atau pembacaan dokumen', run.safe_message.lower())
        self.assertNotIn('private-fixture-token', run.safe_message)

    def test_kemenkeu_local_pdf_failure_exposes_file_read_stage(self):
        with patch('indicators.fiscal.kemenkeu.pdf_to_text', side_effect=ValueError('private fixture')):
            with self.assertRaises(ValueError):
                fiscal.ingest_kita_pdf_bytes(b'synthetic', 'file://fixture.pdf')
        run = SyncRun.objects.get(source_id_snapshot='KEMENKEU')
        self.assertIn('pembacaan berkas', run.safe_message.lower())
        self.assertNotIn('private fixture', run.safe_message)

    def test_bi_file_parse_failure_records_stage_without_name_or_exception(self):
        with TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']) as folder:
            (Path(folder) / 'bi-7day-rr.xlsx').touch()
            with patch('indicators.ingest.save_raw_from_path', return_value=(Mock(), False)), \
                 patch('indicators.ingest.parse_bi_rr_xlsx', side_effect=ValueError('private fixture')):
                ingest.ingest_local_datasets(Path(folder))
        run = SyncRun.objects.get(source_id_snapshot='BI')
        self.assertEqual(run.status, 'failed')
        self.assertIn('pembacaan berkas', run.safe_message.lower())
        self.assertNotIn('private fixture', run.safe_message)

    def test_bkpm_failed_reprocessing_preserves_existing_raw_status(self):
        source = ingest.get_or_create_source('BKPM', 'Realisasi Investasi BKPM', 'Kementerian Investasi/BKPM',
                                             'https://realisasiinvestasi.id/',
                                             'Dataset realisasi investasi triwulanan PMA/PMDN tingkat nasional.')
        name = 'Realisasi-triwulan-i-tahun-2025.zip'
        raw = RawFile.objects.create(source=source, document_name=name, checksum_sha256='a' * 64,
                                     parse_status=RawFile.ParseStatus.PARSED)
        with TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']) as folder:
            (Path(folder) / name).touch()
            with patch('indicators.ingest.save_raw_from_path', return_value=(raw, False)), \
                 patch('indicators.ingest.sum_bkpm_zip_csv', side_effect=ValueError('private fixture')):
                ingest.ingest_local_datasets(Path(folder))
        raw.refresh_from_db()
        self.assertEqual(raw.parse_status, RawFile.ParseStatus.PARSED)
        run = SyncRun.objects.get(source_id_snapshot='BKPM')
        self.assertIn('pembacaan berkas', run.safe_message.lower())
        self.assertNotIn('private fixture', run.safe_message)
