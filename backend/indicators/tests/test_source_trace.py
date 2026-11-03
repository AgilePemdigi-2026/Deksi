import hashlib
from datetime import date

from indicators.models import RawFile, Source
from indicators.tests.support import IndicatorCase


class SourceTraceTests(IndicatorCase):
    def trace(self, **query):
        return self.client.get("/api/indicators/inflasi/source-trace/", query)

    def raw(self, source=None):
        return RawFile.objects.create(source=source or self.source, document_name="UJI SINTETIS.txt",
                                      source_url="https://example.test/document",
                                      checksum_sha256=hashlib.sha256(b"uji").hexdigest(),
                                      file_size_bytes=3)

    def test_shared_raw_metadata_remains_bound_to_every_observation(self):
        raw = self.raw()
        self.observation(raw_file=raw)
        self.observation(raw_file=raw, value="2", observation_date=date(1999, 12, 31))
        rows = self.trace().json()["history"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["rawFile"] and r["rawFile"]["checksumSha256"] == raw.checksum_sha256 for r in rows))

    def test_wrong_source_raw_is_not_projected_or_downloadable(self):
        source = Source.objects.create(source_id="OTHER", source_name="Other", institution="Other",
                                       primary_url="https://example.test")
        raw = self.raw(source)
        self.observation(raw_file=raw)
        self.assertIsNone(self.trace().json()["rawFile"])
        self.assertEqual(self.client.get(f"/api/indicators/inflasi/raw-file/{raw.pk}/").status_code, 404)

    def test_unsafe_urls_are_null_without_fetching_source(self):
        self.source.primary_url = "https://user:password@example.test/private"
        self.source.save()
        raw = self.raw()
        raw.source_url = "file:///private/internal/path"
        raw.save()
        self.observation(raw_file=raw)
        result = self.trace().json()
        self.assertIsNone(result["source"]["primaryUrl"])
        self.assertIsNone(result["rawFile"]["sourceUrl"])
        self.assertNotIn("password", str(result))

    def test_exact_selection_does_not_fall_back_to_latest(self):
        old = self.observation(value="2", observation_date=date(1999, 12, 31), period_label="Desember 1999")
        self.observation()
        query = {"observationDate": "1999-12-31", "frequency": "monthly", "dataType": "yoy", "sourceId": "TEST_ONLY"}
        response = self.trace(**query)
        self.assertEqual(response.json()["value"], "2")
        self.assertEqual(response.json()["observationId"], old.pk)
        query["observationDate"] = "1998-12-31"
        self.assertEqual(self.trace(**query).status_code, 404)

    def test_incomplete_malformed_or_unknown_selectors_are_rejected(self):
        self.observation()
        for query in [{"observationDate": "2000-01-31"}, {"revision": "fake"}, {"limit": "-1"},
                      {"limit": "101"}, {"offset": "bad"}]:
            with self.subTest(query=query):
                self.assertEqual(self.trace(**query).status_code, 400)

    def test_bounded_history_pagination_has_truthful_totals(self):
        for year in range(1990, 2000):
            self.observation(observation_date=date(year, 1, 1))
        result = self.trace(limit="3", offset="3").json()
        self.assertEqual(len(result["history"]), 3)
        self.assertEqual(result["pagination"], {"offset": 3, "limit": 3, "total": 10, "hasMore": True})
        self.assertEqual(len(self.trace(limit="3", offset="9").json()["history"]), 1)

    def test_no_fabricated_formula_revision_or_official_verification(self):
        self.observation(data_type="derived_sum")
        result = self.trace().json()
        self.assertEqual(result["valueKind"], "derived")
        self.assertFalse(result["calculation"]["available"])
        self.assertIsNone(result["calculation"]["formula"])
        self.assertIsNone(result["revisionId"])
        self.assertFalse(result["immutableSnapshot"])
        self.assertEqual(result["officialVerification"], "unassessed")
        self.assertNotIn("Nilai berasal dari dokumen resmi", result["note"])

    def test_empty_missing_and_get_only(self):
        self.assertFalse(self.trace().json()["available"])
        self.assertEqual(self.client.get("/api/indicators/unknown/source-trace/").status_code, 404)
        self.assertEqual(self.client.post("/api/indicators/inflasi/source-trace/").status_code, 405)
