import os
import tempfile
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.test import override_settings

from indicators import bps, fiscal, ingest
from indicators.models import Observation
from indicators.tests.support import IndicatorCase

Candidate = apps.get_model("indicators", "ObservationCandidate")


class ImportWriterLifecycleTests(IndicatorCase):
    def assert_candidate(self, *, indicator_code, source_id, observation_date):
        candidate = Candidate.objects.get(indicator__code=indicator_code, source__source_id=source_id)
        self.assertEqual(candidate.status, Candidate.Status.PENDING)
        self.assertEqual(candidate.payload["value"], "6.000000")
        self.assertIsNone(candidate.reviewed_by_id)
        self.assertEqual(candidate.payload["observation_date"], observation_date.isoformat())
        return candidate

    def assert_reviewed_row_unchanged(self, row, old_review):
        row.refresh_from_db()
        self.assertEqual(row.value, Decimal("5"))
        self.assertEqual(row.validation_status, Observation.Status.PUBLISHED)
        self.assertEqual((row.reviewed_by_id, row.reviewed_at), old_review)

    def test_bkpm_import_stages_and_preserves_public_observation(self):
        with tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"], prefix="deksi-f6-bkpm-") as tmp:
            root = Path(tmp)
            archive_path = root / "realisasi-triwulan-i-tahun-2020.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("data.csv", "investasi_rp_juta,catatan\n5000000,a\n1000000,b\n")
            indicator = ingest.get_or_create_indicator("investasi", "Realisasi Investasi", "Rencana Modal",
                                                       "Rp Triliun", "sum", 4)
            source = ingest.get_or_create_source("BKPM", "Realisasi Investasi BKPM", "Kementerian Investasi/BKPM",
                "https://realisasiinvestasi.id/", "Dataset realisasi investasi triwulanan PMA/PMDN tingkat nasional.")
            observation_date = date(2020, 3, 31)
            row = self.observation(indicator=indicator, source=source, observation_date=observation_date,
                                   period_label="Triwulan I 2020", frequency="quarterly", data_type="derived_sum",
                                   value=Decimal("5"), unit="Rp Triliun")
            old_review = (row.reviewed_by_id, row.reviewed_at)
            before = self.client.get("/api/indicators/?code=investasi").json()
            raw_root = root / "raw"
            with override_settings(DEKSI_RAW_DIR=raw_root):
                result = ingest.ingest_local_datasets(root)
            self.assertEqual(result["bkpm_quarters"], 1)
            self.assertEqual(result["errors"], [])
            self.assert_reviewed_row_unchanged(row, old_review)
            self.assertEqual(self.client.get("/api/indicators/?code=investasi").json(), before)
            candidate = self.assert_candidate(indicator_code="investasi", source_id="BKPM",
                                              observation_date=observation_date)
            self.assertIsNotNone(candidate.payload["raw_file_id"])

    def test_fiscal_import_stages_and_preserves_public_observation(self):
        from indicators.kemenkeu import KitaMetric, KitaResult

        source = fiscal.get_kemenkeu_source()
        indicator = fiscal.get_fiscal_indicators()["pendapatan_negara"]
        observation_date = date(2020, 3, 31)
        row = self.observation(indicator=indicator, source=source, observation_date=observation_date,
                               period_label="s.d. Maret 2020", frequency="monthly", data_type="cumulative_ytd",
                               value=Decimal("5"), unit="Rp Triliun")
        old_review = (row.reviewed_by_id, row.reviewed_at)
        before = self.client.get(f"/api/indicators/?code={indicator.code}").json()
        parsed = KitaResult(source_url="https://example.test/kita.pdf", cumulative_until=observation_date,
                            period_label="s.d. Maret 2020", publication_date=date(2020, 4, 1),
                            metrics={"pendapatan_negara": KitaMetric("pendapatan_negara", Decimal("6"),
                                                                      "Rp Triliun", "synthetic")})
        with tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"], prefix="deksi-f6-fiscal-") as tmp:
            with override_settings(DEKSI_RAW_DIR=Path(tmp) / "raw"), \
                    patch("indicators.fiscal.kemenkeu.fetch_and_parse", return_value=(b"%PDF synthetic", parsed)), \
                    patch("indicators.fiscal.kemenkeu.suggested_document_name", return_value="synthetic-kita.pdf"):
                result = fiscal.ingest_kita_pdf_url("https://example.test/kita.pdf")
        self.assertEqual(result["metrics"], ["pendapatan_negara=6 Rp Triliun"])
        self.assert_reviewed_row_unchanged(row, old_review)
        self.assertEqual(self.client.get(f"/api/indicators/?code={indicator.code}").json(), before)
        candidate = self.assert_candidate(indicator_code=indicator.code, source_id="KEMENKEU",
                                          observation_date=observation_date)
        self.assertIsNotNone(candidate.payload["raw_file_id"])

    def test_bps_sync_stages_existing_revision_and_new_data_is_not_public(self):
        series = {"code": "bps_lifecycle_test", "var_id": 987654, "name": "BPS synthetic",
                  "category": "Uji", "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
                  "frequency": "annual", "data_type": "level", "subperiods": {1: 1}}
        observation_date = date(2020, 12, 31)
        source = bps._get_or_create_source()
        indicator = bps._get_or_create_indicator(series)
        row = self.observation(indicator=indicator, source=source, observation_date=observation_date,
                               period_label="2020", frequency="annual", data_type="level", value=Decimal("5"))
        old_review = (row.reviewed_by_id, row.reviewed_at)
        before = self.client.get(f"/api/indicators/?code={indicator.code}").json()
        point = {"observation_date": observation_date, "period_label": "2020", "frequency": "annual",
                 "data_type": "level", "value": Decimal("6"), "unit": "%"}
        with patch.object(bps, "BPS_SERIES", [series]), patch.object(bps, "fetch_series", return_value=[point]):
            result = bps.sync_bps_indicators(start_year=2020, end_year=2020)
        self.assertEqual(result["observations"], 1)
        self.assert_reviewed_row_unchanged(row, old_review)
        self.assertEqual(self.client.get(f"/api/indicators/?code={indicator.code}").json(), before)
        self.assert_candidate(indicator_code=indicator.code, source_id="BPS", observation_date=observation_date)

        new_series = {**series, "code": "bps_lifecycle_new"}
        new_indicator = bps._get_or_create_indicator(new_series)
        new_point = {**point, "observation_date": date(2021, 12, 31), "period_label": "2021"}
        with patch.object(bps, "BPS_SERIES", [new_series]), patch.object(bps, "fetch_series", return_value=[new_point]):
            bps.sync_bps_indicators(start_year=2021, end_year=2021)
        self.assertFalse(Observation.objects.filter(indicator=new_indicator).exists())
        self.assertEqual(self.client.get(f"/api/indicators/?code={new_indicator.code}").json()
                         ["indicators"][0]["available"], False)
        self.assert_candidate(indicator_code=new_indicator.code, source_id="BPS",
                              observation_date=date(2021, 12, 31))
