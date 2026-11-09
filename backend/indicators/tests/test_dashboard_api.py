from datetime import date, datetime, timezone
from unittest.mock import patch

from indicators.models import RawFile, Source
from indicators.tests.support import IndicatorCase


class DashboardFilterTests(IndicatorCase):
    def dashboard(self, **params):
        return self.client.get("/api/indicators/dashboard/", {"code": "inflasi", **params})

    @patch("indicators.views.timezone.localdate", return_value=date(2001, 6, 1))
    def test_selected_year_uses_complete_reviewed_context(self, _today):
        self.observation(value="1", observation_date=date(1999, 12, 31), period_label="Desember 1999")
        raw = RawFile.objects.create(
            source=self.source,
            document_name="SYNTHETIC-2000.txt",
            checksum_sha256="a" * 64,
            period_label="Januari 2000",
            retrieved_at=datetime(2000, 2, 4, tzinfo=timezone.utc),
        )
        self.observation(value="0", raw_file=raw, publication_date=date(2000, 2, 3))
        self.observation(value="1000", unit="Rp", observation_date=date(2000, 1, 30))
        self.observation(value="888", observation_date=date(2000, 7, 1), reviewed_at=None)
        other = Source.objects.create(
            source_id="OTHER_TEST",
            source_name="Other synthetic dataset",
            institution="OTHER SYNTHETIC INSTITUTION",
            primary_url="https://example.test/other",
        )
        self.observation(
            value="500",
            source=other,
            unit="Rp",
            frequency="annual",
            data_type="level",
            observation_date=date(2001, 1, 1),
            period_label="2001",
            publication_date=date(2001, 2, 1),
        )
        response = self.dashboard(year=2000)
        self.assertEqual(response.status_code, 200)
        card = response.json()["indicators"][0]
        expected = {
            "available": True,
            "value": "0",
            "unit": "%",
            "period": "Januari 2000",
            "latestPeriod": "Januari 2000",
            "latestYear": 2000,
            "latestObservationDate": "2000-01-31",
            "observationDate": "2000-01-31",
            "source": self.source.institution,
            "sourceId": self.source.source_id,
            "publicationDate": "2000-02-03",
            "retrievedAt": raw.retrieved_at.isoformat(),
            "frequency": "monthly",
            "dataType": "yoy",
            "hasCurrentYearData": False,
            "sparkline": [1, 0],
            "previousPeriod": "Desember 1999",
            "changeValue": "-1",
            "changeUnit": "percentage_point",
            "changePercentage": None,
            "deltaDirection": "down",
            "deltaPositive": False,
        }
        self.assertEqual({key: card.get(key) for key in expected}, expected)
        self.assertIn("Januari 2000", card["dataAvailabilityNote"])
        self.assertEqual(response.json()["activeFilters"], {"year": 2000})

    def test_invalid_years_and_duplicate_filters_are_rejected(self):
        self.client.raise_request_exception = False
        for year in ("0", "10000", "9" * 5000, "²", "٢٠٠٠", "-1", "2000.5", "abc"):
            with self.subTest(year=year[:20]):
                self.assertEqual(self.dashboard(year=year).status_code, 400)
        for query in ("year=2000&year=2001", "category=Inflasi&category=PDB", "unsupported=x"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/indicators/dashboard/?" + query).status_code, 400)

    def test_unfiltered_dashboard_preserves_summary_contract(self):
        self.observation(value="0.123456")
        summary = self.client.get("/api/indicators/?code=inflasi").json()
        dashboard = self.dashboard().json()
        self.assertEqual(dashboard.pop("activeFilters"), {})
        self.assertEqual(dashboard, summary)

    def test_unreviewed_or_unpublished_year_does_not_fall_back(self):
        self.observation(observation_date=date(1999, 1, 1), value="3")
        for index, changes in enumerate(
            (
                {"reviewed_by": None},
                {"reviewed_at": None},
                {"validation_status": "pending"},
                {"validation_status": "validated"},
                {"validation_status": "rejected"},
            )
        ):
            year = 2000 + index
            self.observation(observation_date=date(year, 1, 1), value="999", **changes)
            with self.subTest(changes=changes):
                card = self.dashboard(year=year).json()["indicators"][0]
                self.assertFalse(card["available"])
                self.assertIsNone(card["value"])
                self.assertIsNone(card["latestPeriod"])
                self.assertNotIn("sourceId", card)
                self.assertIn(str(year), card["dataAvailabilityNote"])

    def test_category_filter_and_unknown_or_missing_indicators(self):
        self.observation()
        payload = self.dashboard(category="iNfLaSi", year=2000).json()
        self.assertEqual([row["id"] for row in payload["indicators"]], ["inflasi"])
        self.assertEqual(self.dashboard(category="unknown").status_code, 400)
        self.assertEqual(self.dashboard().json()["indicators"][0]["value"], "0")
        empty = self.dashboard(code="unknown").json()["indicators"][0]
        self.assertFalse(empty["available"])
        self.assertIsNone(empty["value"])
        categories = self.client.get("/api/indicators/categories/").json()["categories"]
        self.assertIn({"category": "Inflasi", "codes": ["inflasi"]}, categories)
        self.assertEqual(self.client.post("/api/indicators/dashboard/").status_code, 405)

    def test_year_range_boundaries_are_valid_and_empty(self):
        for year in (1, 9999):
            with self.subTest(year=year):
                response = self.dashboard(year=year)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()["indicators"][0]["available"])

    def test_historical_sparkline_excludes_later_same_series_values(self):
        self.observation(value="0.123456", observation_date=date(2000, 1, 1))
        self.observation(value="100", observation_date=date(2001, 1, 1))
        card = self.dashboard(year=2000).json()["indicators"][0]
        self.assertEqual(card["value"], "0.123456")
        self.assertEqual(card["sparkline"], [0.123456])
