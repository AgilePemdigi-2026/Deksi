from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import OperationalError, connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from indicators import lifecycle
from indicators.models import Indicator, Observation, ObservationCandidate, Source


class LifecycleTransactionTests(TransactionTestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(
            username="review-transaction", is_staff=True, is_superuser=True)
        self.indicator = Indicator.objects.create(code="inflasi", name="UJI", category="UJI", unit="%")
        self.source = Source.objects.create(source_id="UJI_TX", source_name="UJI", institution="UJI",
                                            primary_url="https://example.test/")
        self.row = Observation.objects.create(indicator=self.indicator, source=self.source,
            observation_date=date(2020, 1, 31), period_label="Januari UJI", frequency="monthly", data_type="yoy",
            value=Decimal("5"), unit="%", validation_status="published", reviewed_by=self.actor,
            reviewed_at="2020-02-01T00:00:00Z")

    def stage(self, value):
        candidate = lifecycle.stage_observation(indicator_id=self.indicator.pk, source_id=self.source.pk,
            observation_date=self.row.observation_date, period_label=self.row.period_label,
            frequency="monthly", data_type="yoy", value=Decimal(value), unit="%")
        assert candidate is not None
        return candidate

    def test_simultaneous_reviews_never_publish_two_candidates_from_same_basis(self):
        first, second = self.stage("6"), self.stage("7")
        barrier = Barrier(2)
        actual_state = lifecycle._state

        def synchronized(payload):
            state = actual_state(payload)
            barrier.wait(timeout=5)
            return state

        def review(pk):
            try:
                lifecycle.review_candidate(pk, self.actor)
                return "published"
            except (OperationalError, ValidationError) as exc:
                return type(exc).__name__
            finally:
                connections.close_all()

        with patch("indicators.lifecycle._state", side_effect=synchronized):
            with ThreadPoolExecutor(max_workers=2) as workers:
                outcomes = list(workers.map(review, [first.pk, second.pk]))
        winners = ObservationCandidate.objects.filter(status="published").count()
        self.assertLessEqual(winners, 1, outcomes)
        self.row.refresh_from_db()
        if winners:
            self.assertIn(self.row.value, [Decimal("6"), Decimal("7")])
            self.assertEqual(outcomes.count("published"), 1)
        else:
            # SQLite may explicitly refuse both concurrent writers; never retry/claim guaranteed progress.
            self.assertEqual(self.row.value, Decimal("5"))
        self.assertEqual(self.row.validation_status, "published")
        self.assertEqual(ObservationCandidate.objects.filter(status="pending").count(), 2 - winners)

    def test_candidate_migration_preserves_active_observation_and_adds_empty_staging(self):
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("indicators", "0004_exact_observation_decimal")])
            self.assertEqual(Observation.objects.get(pk=self.row.pk).value, Decimal("5"))
            MigrationExecutor(connection).migrate([("indicators", "0005_observation_candidate")])
            self.assertEqual(Observation.objects.get(pk=self.row.pk).validation_status, "published")
            self.assertFalse(ObservationCandidate.objects.exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
