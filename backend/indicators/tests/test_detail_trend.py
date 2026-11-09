from datetime import date
from decimal import Decimal

from indicators.tests.support import IndicatorCase


class DetailTrendTests(IndicatorCase):
    def trend(self, **query):
        return self.client.get("/api/indicators/inflasi/trend/", query)

    def test_native_history_keeps_each_semantic_and_exact_value(self):
        self.observation(value="5.000001", observation_date=date(1999, 12, 31),
                         frequency="quarterly", data_type="level")
        self.observation(value="5.000002")
        response = self.trend()
        self.assertEqual(response.status_code, 200)
        points = response.json()["points"]
        self.assertEqual([p["exactValue"] for p in points], ["5.000001", "5.000002"])
        self.assertEqual([p["frequency"] for p in points], ["quarterly", "monthly"])
        self.assertEqual([p["dataType"] for p in points], ["level", "yoy"])
        self.assertIsNone(response.json()["historicalAverage"])
        self.assertIsNone(response.json()["historicalAverageExact"])

    def test_mixed_semantics_refuse_annual_aggregation(self):
        self.observation(value="2", observation_date=date(2000, 1, 1), data_type="level")
        self.observation(value="3")
        self.assertEqual(self.trend(granularity="Tahunan").status_code, 400)

    def test_cumulative_ytd_cannot_be_summed_across_periods(self):
        self.indicator.aggregation_kind = "sum"
        self.indicator.save()
        self.observation(value="2", observation_date=date(2000, 1, 1), data_type="cumulative_ytd")
        self.observation(value="3", data_type="cumulative_ytd")
        self.assertEqual(self.trend(granularity="Tahunan").status_code, 400)

    def test_annual_decimal_average_is_not_binary_float_arithmetic(self):
        self.observation(value="0.1", observation_date=date(2000, 1, 1), data_type="level")
        self.observation(value="0.2", data_type="level")
        point = self.trend(granularity="Tahunan").json()["points"][0]
        self.assertEqual(point["exactValue"], "0.15")
        self.assertEqual(point["value"], 0.15)

    def test_unsupported_frequency_aggregation_returns_400(self):
        self.observation()
        self.assertEqual(self.trend(granularity="Harian").status_code, 400)

    def test_extreme_comparison_values_do_not_raise_decimal_exception(self):
        self.observation(value=Decimal("0.000001"), unit="Rp", observation_date=date(1999, 12, 31))
        self.observation(value=Decimal("999999999999999999.999999"), unit="Rp")
        self.assertEqual(self.client.get("/api/indicators/?code=inflasi").status_code, 200)

    def test_no_store_and_no_private_fields(self):
        self.observation(validation_notes="PRIVATE-REVIEW-NOTE")
        paths = ["/api/indicators/?code=inflasi", "/api/indicators/inflasi/trend/",
                 "/api/indicators/inflasi/source-trace/"]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertIn("no-store", response.headers.get("Cache-Control", ""))
                self.assertNotIn("PRIVATE-REVIEW-NOTE", response.content.decode())
                self.assertNotIn("reviewer-test", response.content.decode())

    def test_same_date_rows_remain_deterministic(self):
        self.observation(data_type="level", value="2")
        self.observation(data_type="yoy", value="0")
        summary = self.client.get("/api/indicators/?code=inflasi").json()["indicators"][0]
        trace = self.client.get("/api/indicators/inflasi/source-trace/").json()
        self.assertEqual((summary["dataType"], summary["value"]), (trace["dataType"], trace["value"]))
