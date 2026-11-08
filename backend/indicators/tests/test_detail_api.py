import hashlib
import os
import tempfile
from datetime import date
from pathlib import Path

from indicators.models import Observation, RawFile, Source
from indicators.tests.support import IndicatorCase


class DetailPublicationTests(IndicatorCase):
    def test_raw_download_also_requires_recorded_review(self):
        with tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"], prefix="deksi-f6-raw-") as directory:
            content = b"SYNTHETIC RAW NOT PUBLIC"
            path = Path(directory) / "test.txt"
            path.write_bytes(content)
            raw = RawFile.objects.create(source=self.source, document_name="test.txt", stored_path=str(path),
                                         checksum_sha256=hashlib.sha256(content).hexdigest(),
                                         file_size_bytes=len(content))
            self.observation(raw_file=raw, reviewed_by=None, reviewed_at=None)
            response = self.client.get(f"/api/indicators/inflasi/raw-file/{raw.pk}/")
            response.close()
            self.assertEqual(response.status_code, 404)

    def test_only_reviewed_published_values_are_public(self):
        self.observation()
        statuses = [Observation.Status.PENDING, Observation.Status.VALIDATED, Observation.Status.REJECTED]
        for index, status in enumerate(statuses):
            self.observation(observation_date=date(2001 + index, 1, 1), validation_status=status, value="99")
        self.observation(observation_date=date(2005, 1, 1), reviewed_by=None, reviewed_at=None, value="888")
        response = self.client.get("/api/indicators/?code=inflasi")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["indicators"][0]["value"], "0")
        self.assertEqual(len(self.client.get("/api/indicators/inflasi/trend/").json()["points"]), 1)
        self.assertEqual(self.client.get("/api/indicators/inflasi/source-trace/").json()["value"], "0")

    def test_empty_unknown_methods_and_no_authentication(self):
        self.assertFalse(self.client.get("/api/indicators/?code=inflasi").json()["indicators"][0]["available"])
        self.assertEqual(self.client.get("/api/indicators/unknown/trend/").status_code, 404)
        self.assertEqual(self.client.post("/api/indicators/").status_code, 405)
        self.observation()
        response = self.client.get("/api/indicators/inflasi/trend/", HTTP_AUTHORIZATION="invalid")
        self.assertEqual(response.status_code, 200)

    def test_trace_query_count_does_not_grow_per_history_row(self):
        for year in range(1990, 1994):
            self.observation(observation_date=date(year, 1, 1))
        with self.assertNumQueries(4):
            response = self.client.get("/api/indicators/inflasi/source-trace/")
        self.assertEqual(response.status_code, 200)


class DetailComparisonTests(IndicatorCase):
    def summary(self):
        return self.client.get("/api/indicators/?code=inflasi").json()["indicators"][0]

    def test_comparison_and_sparkline_use_only_same_series(self):
        self.observation(value="2", observation_date=date(1999, 12, 31), period_label="Desember 1999")
        other = Source.objects.create(source_id="OTHER", source_name="Other", institution="Other", primary_url="https://example.test")
        self.observation(value="200", source=other, observation_date=date(2000, 1, 1))
        self.observation(value="100", frequency="quarterly", observation_date=date(2000, 1, 2))
        self.observation(value="300", data_type="level", observation_date=date(2000, 1, 3))
        self.observation(value="400", unit="Rp", observation_date=date(2000, 1, 4))
        self.observation(value="900", observation_date=date(2000, 1, 5), reviewed_at=None)
        self.observation(value="3")
        row = self.summary()
        self.assertEqual(row["sparkline"], [2, 3])
        self.assertEqual(row["previousPeriod"], "Desember 1999")
        self.assertEqual(row["changeValue"], "1")
        self.assertEqual(row["changeUnit"], "percentage_point")
        self.assertIn("poin persentase", row["delta"])
        self.assertIsNone(row["changePercentage"])

    def test_zero_denominator_is_unavailable_not_flat_or_zero_change(self):
        self.observation(value="0", unit="Rp", observation_date=date(1999, 12, 31))
        self.observation(value="5", unit="Rp")
        row = self.summary()
        self.assertIsNone(row["changePercentage"])
        self.assertIsNone(row["deltaDirection"])
        self.assertIsNone(row["changeValue"])

    def test_decimal_relative_change_and_negative_values(self):
        self.observation(value="-2", unit="Rp", observation_date=date(1999, 12, 31), period_label="Lalu")
        self.observation(value="-1", unit="Rp")
        row = self.summary()
        self.assertEqual(row["changeValue"], "50")
        self.assertEqual(row["changeUnit"], "percent")
        self.assertEqual(row["changePercentage"], 50)
        self.assertEqual(row["deltaDirection"], "up")
