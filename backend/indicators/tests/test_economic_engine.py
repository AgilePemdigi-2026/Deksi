import json
import os
import tempfile
from datetime import date
from decimal import Decimal, ROUND_UP, localcontext
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from indicators.models import Indicator, Observation, RawFile, Source
from indicators.storage import save_raw


class EconomicEngineTests(TestCase):
    def setUp(self):
        self.raw_directory = tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"])
        self.addCleanup(self.raw_directory.cleanup)
        self.enterContext(override_settings(DEKSI_RAW_DIR=self.raw_directory.name))
        self.source, _ = Source.objects.get_or_create(
            source_id="BPS", defaults={"source_name": "BPS sintetis", "institution": "BPS",
                                       "primary_url": "https://example.test"})
        self.reviewer = get_user_model().objects.create_user(username="reviewer-sintetis")
        self.indicators = {}
        for code in ("pdb_nominal", "pmtb_nominal", "konsumsi_rumah_tangga", "ekspor_barang", "impor_barang"):
            self.indicators[code], _ = Indicator.objects.get_or_create(
                code=code, defaults={"name": code, "category": "test", "unit": "Rp miliar"})

    def row(self, code, value, **kwargs):
        values = {"indicator": self.indicators[code], "source": self.source, "observation_date": date(2025, 3, 31),
                  "period_label": "Q1 2025", "frequency": "quarterly", "data_type": "level", "value": Decimal(value),
                  "unit": "Rp miliar", "validation_status": "published", "reviewed_by": self.reviewer,
                  "reviewed_at": timezone.now()}
        values.update(kwargs)
        row = Observation.objects.create(**values)
        if "raw_file" not in kwargs and code in {"pdb_nominal", "pmtb_nominal", "konsumsi_rumah_tangga"}:
            self.bind_raw(row)
        return row

    def bind_raw(self, row):
        component = {"pdb_nominal": 800, "pmtb_nominal": 400, "konsumsi_rumah_tangga": 100}[row.indicator.code]
        subperiod = {3: 31, 6: 32, 9: 33, 12: 34}.get(row.observation_date.month, 31)
        key = f"{component}195507{subperiod}"
        excerpt = {"kind": "bps_selected_datacontent_excerpt", "var_id": 1955,
            "vervar": component, "turvar": 0, "th_id": 7, "year": row.observation_date.year,
            "turth_id": subperiod, "datacontent": {key: str(row.value)}}
        row.raw_file, _ = save_raw(row.source, json.dumps(excerpt).encode(), "synthetic-bps.json")
        row.save(update_fields=["raw_file"])
        return excerpt

    def engine(self):
        self.assertIsNotNone(find_spec("indicators.economic_engine"), "Economic Engine belum diimplementasikan")
        return import_module("indicators.economic_engine")

    def test_both_shares_use_reviewed_quarterly_bps_inputs(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300")
        self.row("konsumsi_rumah_tangga", "550")
        result = self.engine().calculate_gdp_shares(date(2025, 3, 31))
        self.assertEqual(result["pmtb_share"]["value"], "30.00")
        self.assertEqual(result["household_consumption_share"]["value"], "55.00")
        self.assertEqual(result["pmtb_share"]["period"], "Q1 2025")
        self.assertEqual(result["pmtb_share"]["inputs"]["pdb_nominal"]["value"], "1000.000000")

    def test_actual_importer_excerpt_is_accepted_without_reconstructing_raw(self):
        from indicators import bps

        for code, value in (("pdb_nominal", "1000"), ("pmtb_nominal", "300")):
            series = next(series for series in bps.BPS_SERIES if series["code"] == code)
            component = series["component_id"]
            key = f"{component}1955012531"
            with patch.object(bps, "_validate_variable_unit"), \
                    patch.object(bps, "_year_period_ids", return_value={2025: 125}), \
                    patch.object(bps, "_resolve_national_vervar", return_value=component), \
                    patch.object(bps, "_resolve_turvar", return_value=0), \
                    patch.object(bps, "_request", return_value={"datacontent": {key: value}}), \
                    patch.object(bps.time, "sleep"):
                point, = bps.fetch_series(series, start_year=2025, end_year=2025)
            raw, _ = save_raw(self.source, point.pop("raw_excerpt"), "actual-importer-synthetic.json")
            self.row(code, str(point.pop("value")), raw_file=raw, **point)
        metric = self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]
        self.assertTrue(metric["available"])
        self.assertEqual(metric["value"], "30.00")
        self.assertTrue(all(row["bindingStatus"] == "matched" for row in metric["inputs"].values()))

    def test_missing_raw_never_produces_a_ready_derived_value(self):
        self.row("pdb_nominal", "1000", raw_file=None)
        self.row("pmtb_nominal", "300", raw_file=None)
        metric = self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]
        self.assertFalse(metric["available"])
        self.assertIsNone(metric["value"])
        self.assertEqual(metric["reasonCode"], "input_evidence_unqualified")
        self.assertEqual(Observation.objects.count(), 2)

    def test_intact_raw_must_match_the_selected_observation_value(self):
        self.row("pdb_nominal", "1000")
        component = self.row("pmtb_nominal", "300")
        component.value = Decimal("301")
        component.save(update_fields=["value"])
        metric = self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]
        self.assertFalse(metric["available"])
        self.assertIsNone(metric["value"])
        self.assertEqual(metric["inputs"]["pmtb_nominal"]["evidenceStatus"], "integrity_ok")
        self.assertEqual(metric["inputs"]["pmtb_nominal"]["bindingStatus"], "mismatch")

    def test_qualified_result_has_a_stable_method_bound_identity(self):
        self.row("pdb_nominal", "1000")
        component = self.row("pmtb_nominal", "300")
        calculate = self.engine().calculate_gdp_shares
        first = calculate(date(2025, 3, 31))["pmtb_share"]
        self.assertEqual(first.get("methodVersion"), "bps-gdp-shares.v3")
        self.assertEqual(first["priceBasis"], "current_prices")
        self.assertEqual(first["officialVerification"], "unassessed")
        self.assertRegex(first["inputDigest"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["resultDigest"], calculate(date(2025, 3, 31))["pmtb_share"]["resultDigest"])
        component.value = Decimal("310")
        component.save(update_fields=["value"])
        self.bind_raw(component)
        changed = calculate(date(2025, 3, 31))["pmtb_share"]
        self.assertEqual(changed["value"], "31.00")
        self.assertNotEqual(first["inputDigest"], changed["inputDigest"])
        self.assertNotEqual(first["resultDigest"], changed["resultDigest"])

    def test_rounding_does_not_inherit_process_decimal_context(self):
        self.row("pdb_nominal", "100")
        self.row("pmtb_nominal", "1.005")
        with localcontext() as context:
            context.rounding = ROUND_UP
            metric = self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]
        self.assertEqual(metric["value"], "1.00")

    def test_api_keeps_unsaved_revision_status_unknown(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300")
        response = self.client.get("/api/economic-engine/gdp/?quarter=2025-03-31")
        self.assertEqual(response.status_code, 200)
        for metric in response.json()["metrics"].values():
            self.assertEqual(metric.get("revisionStatus"), "unknown")
            self.assertEqual(metric["revisionNote"], "Status revisi belum diketahui; angka dapat direvisi.")
        self.assertEqual(response.json()["metrics"]["pmtb_share"]["value"], "30.00")

    def test_excerpt_identity_types_and_shape_must_match_the_importer_contract(self):
        self.row("pdb_nominal", "1000")
        component = self.row("pmtb_nominal", "300")
        mutations = ({"var_id": 1956}, {"vervar": 800}, {"turvar": True}, {"turvar": 1},
            {"year": 2024}, {"turth_id": 32}, {"th_id": -1}, {"kind": "unrelated"},
            {"datacontent": {"unrelated": "300"}}, {"datacontent": {"40019550731": "NaN"}},
            {"datacontent": {"40019550731": 300}}, {"extra": "untrusted"})
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                excerpt = self.bind_raw(component)
                excerpt.update(mutation)
                component.raw_file, _ = save_raw(self.source, json.dumps(excerpt).encode(), "mismatch.json")
                component.save(update_fields=["raw_file"])
                metric = self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]
                self.assertFalse(metric["available"])
                self.assertIsNone(metric["value"])
                self.assertEqual(metric["inputs"]["pmtb_nominal"]["bindingStatus"], "mismatch")

    def test_invalid_json_and_duplicate_json_keys_do_not_qualify(self):
        self.row("pdb_nominal", "1000")
        component = self.row("pmtb_nominal", "300")
        good = json.dumps(self.bind_raw(component))
        for payload in (b"not json", b"\xff", b"[]", good.replace('{', '{"var_id": 1955,', 1).encode()):
            with self.subTest(payload=payload[:30]):
                component.raw_file, _ = save_raw(self.source, payload, "invalid.json")
                component.save(update_fields=["raw_file"])
                self.assertFalse(self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]["available"])

    def test_calculation_is_read_only_and_keeps_missing_release_unknown(self):
        self.row("pdb_nominal", "3")
        self.row("pmtb_nominal", "1")
        observations, raw_files = list(Observation.objects.values()), list(RawFile.objects.values())
        metric = self.engine().calculate_gdp_shares(date(2025, 3, 31))["pmtb_share"]
        self.assertEqual(metric["value"], "33.33")
        self.assertIsNone(metric["inputs"]["pmtb_nominal"]["publicationDate"])
        self.assertEqual(list(Observation.objects.values()), observations)
        self.assertEqual(list(RawFile.objects.values()), raw_files)

    def test_missing_pending_and_different_period_are_not_used(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300", validation_status="pending")
        self.row("konsumsi_rumah_tangga", "550", observation_date=date(2025, 6, 30), period_label="Q2 2025")
        result = self.engine().calculate_gdp_shares(date(2025, 3, 31))
        for metric in result.values():
            self.assertFalse(metric["available"])
            self.assertIsNone(metric["value"])
            self.assertTrue(metric["reason"])

    def test_invalid_metadata_and_missing_reviewer_are_rejected(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300", unit="US$ juta")
        self.row("konsumsi_rumah_tangga", "550", reviewed_at=None)
        result = self.engine().calculate_gdp_shares(date(2025, 3, 31))
        self.assertFalse(result["pmtb_share"]["available"])
        self.assertFalse(result["household_consumption_share"]["available"])

    def test_zero_denominator_and_zero_numerator(self):
        gdp = self.row("pdb_nominal", "0")
        self.row("pmtb_nominal", "0")
        calculate = self.engine().calculate_gdp_shares
        self.assertFalse(calculate(date(2025, 3, 31))["pmtb_share"]["available"])
        gdp.value = Decimal("100")
        gdp.save(update_fields=["value"])
        self.bind_raw(gdp)
        self.assertEqual(calculate(date(2025, 3, 31))["pmtb_share"]["value"], "0.00")

    def test_ambiguous_same_indicator_is_not_silently_selected(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "999", data_type="yoy")
        self.row("pmtb_nominal", "300")
        result = self.engine().calculate_gdp_shares(date(2025, 3, 31))
        self.assertFalse(result["pmtb_share"]["available"])

    def test_only_quarter_end_is_allowed(self):
        calculate = self.engine().calculate_gdp_shares
        for invalid in (date(2025, 3, 30), date(2025, 4, 30)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                calculate(invalid)

    def test_negative_component_and_unreviewed_publication_are_rejected(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "-1")
        self.row("konsumsi_rumah_tangga", "550", reviewed_by=None)
        result = self.engine().calculate_gdp_shares(date(2025, 3, 31))
        self.assertFalse(result["pmtb_share"]["available"])
        self.assertFalse(result["household_consumption_share"]["available"])

    def test_other_source_is_not_used(self):
        other = Source.objects.create(source_id="TEST_OTHER", source_name="sintetis", institution="Uji", primary_url="https://example.test")
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300", source=other)
        result = self.engine().calculate_gdp_shares(date(2025, 3, 31))
        self.assertFalse(result["pmtb_share"]["available"])

    def trade_row(self, code, value, **changes):
        fields = {"observation_date": date(2025, 1, 31), "period_label": "Januari 2025",
                  "frequency": "monthly", "data_type": "level", "unit": "US$ juta"}
        fields.update(changes)
        return self.row(code, value, **fields)

    def test_trade_balance_and_ratio_from_matching_month(self):
        self.trade_row("ekspor_barang", "120")
        self.trade_row("impor_barang", "100")
        result = self.engine().calculate_goods_trade(date(2025, 1, 31))
        self.assertEqual(result["goods_trade_balance"]["value"], "20.00")
        self.assertEqual(result["goods_export_import_ratio"]["value"], "120.00")
        self.assertEqual(result["goods_trade_balance"]["unit"], "US$ juta")
        self.assertEqual(result["goods_trade_balance"]["inputs"]["ekspor_barang"]["period"], "Januari 2025")

    def test_trade_missing_invalid_and_zero_denominator(self):
        self.trade_row("ekspor_barang", "120")
        imported = self.trade_row("impor_barang", "0")
        calculate = self.engine().calculate_goods_trade
        result = calculate(date(2025, 1, 31))
        self.assertEqual(result["goods_trade_balance"]["value"], "120.00")
        self.assertFalse(result["goods_export_import_ratio"]["available"])
        imported.unit = "Rp miliar"
        imported.save(update_fields=["unit"])
        self.assertFalse(calculate(date(2025, 1, 31))["goods_trade_balance"]["available"])
        imported.validation_status = "pending"
        imported.save(update_fields=["validation_status"])
        self.assertFalse(calculate(date(2025, 1, 31))["goods_trade_balance"]["available"])

    def test_trade_rejects_ambiguous_and_mismatched_months(self):
        self.trade_row("ekspor_barang", "120")
        self.trade_row("impor_barang", "100", observation_date=date(2025, 2, 28), period_label="Februari 2025")
        calculate = self.engine().calculate_goods_trade
        self.assertFalse(calculate(date(2025, 1, 31))["goods_trade_balance"]["available"])
        self.trade_row("impor_barang", "50", data_type="yoy")
        self.trade_row("impor_barang", "100")
        self.assertFalse(calculate(date(2025, 1, 31))["goods_trade_balance"]["available"])
        with self.assertRaises(ValueError):
            calculate(date(2025, 1, 30))

    def test_public_gdp_endpoint_is_independent_and_excludes_pending_data(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300")
        self.row("konsumsi_rumah_tangga", "550", validation_status="pending")
        url = "/api/economic-engine/gdp/"
        response = self.client.get(url, {"quarter": "2025-03-31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["metrics"]["pmtb_share"]["value"], "30.00")
        self.assertIsNone(response.json()["metrics"]["household_consumption_share"]["value"])
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.client.get(url, {"quarter": "bad"}).status_code, 400)

    def test_public_gdp_rejects_ambiguous_or_noncanonical_query_parameters(self):
        for suffix in ("?quarter=20250331", "?quarter=2025-03-31&quarter=2025-06-30", "?unknown=1"):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.client.get("/api/economic-engine/gdp/" + suffix).status_code, 400)

    def test_trade_is_not_public_until_methodology_is_verified(self):
        self.trade_row("ekspor_barang", "120")
        self.trade_row("impor_barang", "100")
        response = self.client.get("/api/economic-engine/trade/", {"month": "2025-01-31"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])
        self.assertNotIn("metrics", response.json())

    def test_public_gdp_defaults_to_latest_reviewed_gdp_quarter(self):
        self.row("pdb_nominal", "1000")
        self.row("pmtb_nominal", "300")
        self.row("pdb_nominal", "2000", observation_date=date(2025, 6, 30), period_label="Q2 2025",
                 validation_status="pending")
        response = self.client.get("/api/economic-engine/gdp/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["metrics"]["pmtb_share"]["period"], "Q1 2025")

    def test_public_input_exposes_context_and_missing_evidence_without_claiming_verification(self):
        self.row("pdb_nominal", "1000", raw_file=None)
        self.row("pmtb_nominal", "300", raw_file=None)
        response = self.client.get("/api/economic-engine/gdp/", {"quarter": "2025-03-31"})
        row = response.json()["metrics"]["pmtb_share"]["inputs"]["pdb_nominal"]
        self.assertEqual(row["frequency"], "quarterly")
        self.assertEqual(row["dataType"], "level")
        self.assertEqual(row["observationDate"], "2025-03-31")
        self.assertEqual(row["evidenceStatus"], "missing")
        self.assertIsNone(row["publicationDate"])
        self.assertEqual(row["trace"]["indicatorCode"], "pdb_nominal")
        self.assertEqual(row["trace"]["value"], "1000")
        self.assertIsNone(row["trace"]["rawFile"])

    def test_evidence_integrity_is_checked_without_changing_observations(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("HERMES_TEST_SCRATCH")) as rawdir:
            with override_settings(DEKSI_RAW_DIR=rawdir):
                raw, _ = save_raw(self.source, b"synthetic bps excerpt", "synthetic.json")
                self.row("pdb_nominal", "1000", raw_file=raw)
                self.row("pmtb_nominal", "300")
                url = "/api/economic-engine/gdp/?quarter=2025-03-31"
                before = self.client.get(url).json()["metrics"]["pmtb_share"]["inputs"]["pdb_nominal"]
                self.assertEqual(before["evidenceStatus"], "integrity_ok")
                Path(raw.stored_path).write_bytes(b"corrupt")
                after = self.client.get(url).json()["metrics"]["pmtb_share"]["inputs"]["pdb_nominal"]
                self.assertEqual(after["evidenceStatus"], "unavailable_or_invalid")
                self.assertEqual(after["value"], before["value"])
