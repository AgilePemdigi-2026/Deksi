"""Offline contract checks; synthetic IDs do not identify BPS datasets."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from indicators import bps
from indicators.models import Observation, ObservationCandidate


class BpsEconomicInputsContractTests(TestCase):
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
