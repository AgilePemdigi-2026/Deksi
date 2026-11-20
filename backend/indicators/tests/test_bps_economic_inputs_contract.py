"""Offline contract checks; synthetic IDs do not identify BPS datasets."""
import json
import os
import tempfile
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from indicators import bps
from indicators.models import Indicator, Observation, ObservationCandidate, RawFile
from indicators.storage import verified_raw_bytes
from indicators.views import aggregate_trend


class BpsEconomicInputsContractTests(TestCase):
    def setUp(self):
        super().setUp()
        self.raw_dir = tempfile.TemporaryDirectory(dir=os.environ.get("HERMES_TEST_SCRATCH"))
        self.addCleanup(self.raw_dir.cleanup)
        settings_override = override_settings(DEKSI_RAW_DIR=self.raw_dir.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_metadata_unit_validation_rejects_changed_missing_or_ambiguous(self):
        series = next(s for s in bps.BPS_SERIES if s["code"] == "pdb_nominal")
        good = {"var_id": 1955, "unit": "Milyar Rupiah"}
        for rows in ([], [{"var_id": 1955, "unit": "Rupiah"}], [good, good]):
            with self.subTest(rows=rows), patch.object(bps, "_paged_rows", return_value=rows):
                with self.assertRaises(bps.BpsError):
                    bps._validate_variable_unit(series)
        with patch.object(bps, "_paged_rows", return_value=[good]):
            bps._validate_variable_unit(series)

    def test_empty_or_malformed_response_is_reported_not_success(self):
        series = {"var_id": 9999, "frequency": "monthly", "data_type": "level", "unit": "%",
                  "subperiods": {1: 1}, "national_label": "SYNTHETIC", "turvar_keyword": None}
        for body in ({}, {"datacontent": []}, {"datacontent": {}}, {"datacontent": {"irrelevant": "1"}}):
            with self.subTest(body=body), patch.object(bps, "_year_period_ids", return_value={2020: 120}), \
                    patch.object(bps, "_resolve_national_vervar", return_value=7), \
                    patch.object(bps, "_request", return_value=body), patch.object(bps.time, "sleep"):
                with self.assertRaises(bps.BpsError):
                    bps.fetch_series(series, start_year=2020, end_year=2020)

    def test_no_year_metadata_is_reported_as_unavailable(self):
        series = {"var_id": 9999}
        with patch.object(bps, "_year_period_ids", return_value={}):
            with self.assertRaises(bps.BpsError):
                bps.fetch_series(series, start_year=2020, end_year=2020)

    def test_legacy_bps_sync_stores_sanitized_raw_excerpt_for_candidate(self):
        series_list = [{**series, "subperiods": {next(iter(series["subperiods"])):
                       next(iter(series["subperiods"].values()))}} for series in bps.BPS_SERIES[:3]]
        def response(path, params):
            var_id = path.split("/var/")[1].split("/")[0]
            key = f"7{var_id}0120{params['turth']}"
            return {"datacontent": {key: "12.5"}, "untrusted_secret": "DO_NOT_STORE"}

        with tempfile.TemporaryDirectory(dir=os.environ.get("HERMES_TEST_SCRATCH")) as tmp, \
                override_settings(DEKSI_RAW_DIR=tmp), patch.object(bps, "BPS_SERIES", series_list), \
                patch.object(bps, "_year_period_ids", return_value={2020: 120}), \
                patch.object(bps, "_resolve_national_vervar", return_value=7), \
                patch.object(bps, "_resolve_turvar", return_value=0), \
                patch.object(bps, "_request", side_effect=response), patch.object(bps.time, "sleep"):
            result = bps.sync_bps_indicators(start_year=2020, end_year=2020)
            self.assertEqual(result["errors"], [])
            self.assertEqual(ObservationCandidate.objects.count(), 3)
            for candidate in ObservationCandidate.objects.all():
                raw = RawFile.objects.get(pk=candidate.payload["raw_file_id"])
                content = verified_raw_bytes(raw)
                self.assertNotIn(b"DO_NOT_STORE", content)
                self.assertEqual(list(json.loads(content)["datacontent"].values()), ["12.5"])
                self.assertIsNone(candidate.payload["publication_date"])
                self.assertEqual(candidate.status, "pending")
            self.assertEqual(Observation.objects.count(), 0)

    def test_annual_sum_excludes_incomplete_years_for_new_series(self):
        from types import SimpleNamespace

        indicator = Indicator(code="pdb_nominal", aggregation_kind="sum")
        source = SimpleNamespace(source_id="BPS")
        def row(year, month, value):
            return SimpleNamespace(observation_date=date(year, month, 1), value=Decimal(value),
                                   source=source, source_id=1, unit="Rp miliar",
                                   frequency="quarterly", data_type="level")
        observations = [row(2020, m, "1") for m in (3, 6, 9, 12)] + [row(2021, 3, "8")]
        result = aggregate_trend(observations, "Tahunan", indicator)
        self.assertEqual([(p["year"], p["exactValue"]) for p in result], [(2020, "4")])

    def test_annual_monthly_sum_requires_all_distinct_months(self):
        from types import SimpleNamespace

        indicator = Indicator(code="ekspor_barang", aggregation_kind="sum")
        source = SimpleNamespace(source_id="BPS")
        def row(year, month):
            return SimpleNamespace(observation_date=date(year, month, 1), value=Decimal("1"),
                                   source=source, source_id=1, unit="US$ juta",
                                   frequency="monthly", data_type="level")
        observations = ([row(2020, m) for m in range(1, 13)]
                        + [row(2021, m) for m in range(1, 12)]
                        + [row(2022, 1) for _ in range(12)])
        result = aggregate_trend(observations, "Tahunan", indicator)
        self.assertEqual([(p["year"], p["exactValue"]) for p in result], [(2020, "12")])

    def test_annual_sum_rejects_incompatible_source_frequency_unit_and_type(self):
        from types import SimpleNamespace

        indicator = Indicator(code="pdb_nominal", aggregation_kind="sum")
        base = {"observation_date": date(2020, 3, 31), "value": Decimal("1"),
                "source": SimpleNamespace(source_id="BPS"), "source_id": 1, "unit": "Rp miliar",
                "frequency": "quarterly", "data_type": "level"}
        changes = ({"unit": "US$ juta"}, {"frequency": "monthly"},
                   {"source": SimpleNamespace(source_id="OTHER")}, {"data_type": "yoy"})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                aggregate_trend([SimpleNamespace(**(base | change))], "Tahunan", indicator)

    def test_registered_economic_series_use_verified_component_and_stage_pending(self):
        selected = [series for series in bps.BPS_SERIES if "component_id" in series]
        def metadata(path, params):
            if "/model/var/" in path:
                return [{"var_id": var_id, "unit": unit} for var_id, (_, unit) in bps.BPS_VARIABLE_METADATA.items()]
            return [{"kode_ver_id": s["component_id"], "vervar": s["component_label"], "var_id": s["var_id"]}
                    for s in selected if s["var_id"] == params["var"]]

        def data(path, params):
            var_id = int(path.split("/var/")[1].split("/")[0])
            component_id = params["vervar"]
            period = params["turth"].split(";")[0]
            return {"datacontent": {f"{component_id}{var_id}0120{period}": "42.5"}}

        with patch.object(bps, "BPS_SERIES", selected), \
                patch.object(bps, "_paged_rows", side_effect=metadata), \
                patch.object(bps, "_year_period_ids", return_value={2020: 120}), \
                patch.object(bps, "_request", side_effect=data), \
                patch.object(bps.time, "sleep"):
            result = bps.sync_bps_indicators(start_year=2020, end_year=2020)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["observations"], 5)
        self.assertEqual(Observation.objects.count(), 0)
        self.assertEqual(ObservationCandidate.objects.filter(status="pending").count(), 5)
        self.assertEqual(RawFile.objects.count(), 5)
        self.assertTrue(all(candidate.payload["raw_file_id"] for candidate in ObservationCandidate.objects.all()))

    def test_verified_economic_series_are_registered_with_distinct_components(self):
        expected = {
            "pdb_nominal": (1955, 800, "quarterly", "Rp miliar"),
            "pmtb_nominal": (1955, 400, "quarterly", "Rp miliar"),
            "konsumsi_rumah_tangga": (1955, 100, "quarterly", "Rp miliar"),
            "ekspor_barang": (1753, 3, "monthly", "US$ juta"),
            "impor_barang": (1754, 3, "monthly", "US$ juta"),
        }
        configured = {series["code"]: series for series in bps.BPS_SERIES}
        for code, (var_id, component_id, frequency, unit) in expected.items():
            with self.subTest(code=code):
                series = configured[code]
                self.assertEqual((series["var_id"], series["component_id"],
                                  series["frequency"], series["unit"]),
                                 (var_id, component_id, frequency, unit))
                self.assertEqual(series["aggregation_kind"], "sum")

    def test_component_selection_rejects_missing_wrong_or_duplicate_metadata(self):
        series = {"var_id": 1955, "component_id": 800,
                  "component_label": "8. PRODUK DOMESTIK BRUTO"}
        correct = {"kode_ver_id": 800, "vervar": "8. PRODUK DOMESTIK BRUTO", "var_id": 1955}
        for rows in ([], [{"kode_ver_id": 800, "vervar": "wrong", "var_id": 1955}],
                     [correct, correct], [{"kode_ver_id": 1, "vervar": "INDONESIA", "var_id": 1955}]):
            with self.subTest(rows=rows), patch.object(bps, "_paged_rows", return_value=rows):
                with self.assertRaises(bps.BpsError):
                    bps._resolve_national_vervar(series)
        with patch.object(bps, "_paged_rows", return_value=[correct]):
            self.assertEqual(bps._resolve_national_vervar(series), 800)

    def test_synthetic_economic_series_stage_candidates_without_publication(self):
        # These labels and IDs exercise the common importer, not real BPS mappings.
        profiles = (
            ("test_nominal_gdp", "quarterly", "Rp miliar", {31: 1}),
            ("test_pmtb", "quarterly", "Rp miliar", {31: 1}),
            ("test_household", "quarterly", "Rp miliar", {31: 1}),
            ("test_exports", "monthly", "US$ juta", {1: 1}),
            ("test_imports", "monthly", "US$ juta", {1: 1}),
        )
        series_list = [
            {"code": code, "var_id": 9000 + index, "name": code, "category": "Synthetic",
             "unit": unit, "aggregation_kind": "sum", "sort_order": index,
             "frequency": frequency, "data_type": "level", "national_label": "SYNTHETIC",
             "turvar_keyword": None, "subperiods": subperiods}
            for index, (code, frequency, unit, subperiods) in enumerate(profiles, 1)
        ]

        def metadata(path, params=None):
            if "/model/th/" in path:
                return [{"th": "2020", "th_id": "120"}]
            if "/model/vervar/" in path:
                return [{"vervar": "SYNTHETIC", "kode_ver_id": "7"}]
            raise AssertionError("unexpected metadata request")

        def data(path, params):
            var_id = path.split("/var/")[1].split("/")[0]
            period = str(params["turth"])
            return {"datacontent": {f"7{var_id}0120{period}": "42.5"}}

        with patch.object(bps, "BPS_SERIES", series_list), \
                patch.object(bps, "_paged_rows", side_effect=metadata), \
                patch.object(bps, "_request", side_effect=data), \
                patch.object(bps.time, "sleep"):
            result = bps.sync_bps_indicators(start_year=2020, end_year=2020)

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["observations"], 5)
        self.assertEqual(Observation.objects.count(), 0)
        self.assertEqual(ObservationCandidate.objects.count(), 5)
        for code, frequency, unit, _ in profiles:
            with self.subTest(code=code):
                candidate = ObservationCandidate.objects.get(indicator__code=code)
                self.assertEqual(candidate.status, ObservationCandidate.Status.PENDING)
                self.assertEqual(Decimal(candidate.payload["value"]), Decimal("42.5"))
                self.assertEqual(candidate.payload["unit"], unit)
                self.assertEqual(candidate.payload["frequency"], frequency)
                expected = date(2020, 3, 31) if frequency == "quarterly" else date(2020, 1, 31)
                self.assertEqual(candidate.payload["observation_date"], expected.isoformat())

    def test_missing_value_is_not_zero_and_zero_is_retained(self):
        series = {"var_id": 9999, "frequency": "monthly", "data_type": "level", "unit": "synthetic",
                  "subperiods": {1: 1, 2: 2}, "national_label": "SYNTHETIC", "turvar_keyword": None}
        with patch.object(bps, "_year_period_ids", return_value={2020: 120}), \
                patch.object(bps, "_resolve_national_vervar", return_value=7), \
                patch.object(bps, "_request", return_value={"datacontent": {"7999901201": 0}}), \
                patch.object(bps.time, "sleep"):
            points = bps.fetch_series(series, start_year=2020, end_year=2020)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["value"], Decimal(0))
        self.assertEqual(points[0]["observation_date"], date(2020, 1, 31))
