from datetime import date
from decimal import Decimal

from django.apps import apps
from django.core.exceptions import ValidationError

from indicators.ingest import get_or_create_indicator, get_or_create_source, upsert_bi_observations
from indicators.models import Observation
from indicators.tests.support import IndicatorCase


class ImportLifecycleTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.row = self.observation(observation_date=date(2020, 1, 31), value=Decimal("5"))

    def incoming(self, **changes):
        result = {"indicator_id": self.indicator.pk, "source_id": self.source.pk,
                  "observation_date": self.row.observation_date, "period_label": self.row.period_label,
                  "frequency": self.row.frequency, "data_type": self.row.data_type,
                  "value": Decimal("6"), "unit": "%"}
        result.update(changes)
        return result

    def test_bi_reimport_stages_change_without_replacing_reviewed_public_value(self):
        before = self.client.get("/api/indicators/?code=inflasi").json()
        old_review = (self.row.reviewed_by_id, self.row.reviewed_at)
        upsert_bi_observations([self.incoming()])
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))
        self.assertEqual(self.row.validation_status, Observation.Status.PUBLISHED)
        self.assertEqual((self.row.reviewed_by_id, self.row.reviewed_at), old_review)
        self.assertEqual(self.client.get("/api/indicators/?code=inflasi").json(), before)
        candidate = apps.get_model("indicators", "ObservationCandidate").objects.get()
        self.assertEqual(candidate.payload["value"], "6.000000")
        self.assertEqual(candidate.status, "pending")
        self.assertIsNone(candidate.reviewed_by_id)

    def test_identical_reimport_is_noop_and_does_not_reset_existing_review(self):
        upsert_bi_observations([self.incoming(value=self.row.value)])
        self.assertFalse(apps.get_model("indicators", "ObservationCandidate").objects.exists())
        self.row.refresh_from_db()
        self.assertEqual(self.row.validation_status, "published")

    def test_duplicate_new_facts_reuse_candidate_without_inheriting_review(self):
        for _ in range(2):
            upsert_bi_observations([self.incoming(value=Decimal("999999999999999999.999999"))])
        candidate = apps.get_model("indicators", "ObservationCandidate").objects.get()
        self.assertEqual(candidate.payload["value"], "999999999999999999.999999")
        self.assertIsNone(candidate.reviewed_at)

    def test_importer_cannot_silently_rewrite_existing_source_metadata(self):
        with self.assertRaises(ValidationError):
            get_or_create_source(self.source.source_id, self.source.source_name, "UJI BERUBAH", self.source.primary_url)
        self.source.refresh_from_db()
        self.assertEqual(self.source.institution, "INSTANSI UJI SINTETIS")

    def test_importer_cannot_silently_rewrite_existing_indicator_metadata(self):
        with self.assertRaises(ValidationError):
            get_or_create_indicator(self.indicator.code, "UJI BERUBAH", self.indicator.category, "%", "avg", 0)
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.name, "Inflasi UJI SINTETIS")
