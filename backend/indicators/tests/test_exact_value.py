from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from indicators.models import Observation
from indicators.tests.support import IndicatorCase


class ExactValueTests(IndicatorCase):
    def test_all_24_digits_survive_database_roundtrip_and_api(self):
        value = Decimal("999999999999999999.999999")
        row = self.observation(value=value)
        row.refresh_from_db()
        self.assertEqual(row.value, value)
        self.assertEqual(Observation.objects.get(value=value).pk, row.pk)
        response = self.client.get("/api/indicators/?code=inflasi")
        self.assertEqual(response.json()["indicators"][0]["value"], str(value))
        trace = self.client.get("/api/indicators/inflasi/source-trace/").json()
        self.assertEqual(trace["value"], str(value))

    def test_invalid_nonfinite_and_overprecision_values_rejected(self):
        for value in ["NaN", "Infinity", "0.1234567", "1000000000000000000"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.observation(value=value)


class ExactValueMigrationTests(TransactionTestCase):
    def test_forward_migration_preserves_existing_representable_value(self):
        old = [("indicators", "0003_seed_initial_update_log")]
        new = [("indicators", "0004_exact_observation_decimal")]
        final_targets = MigrationExecutor(connection).loader.graph.leaf_nodes()
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        try:
            state = executor.loader.project_state(old).apps
            indicator = state.get_model("indicators", "Indicator").objects.create(
                code="migration-test", name="Migration UJI", category="Uji", unit="%")
            source = state.get_model("indicators", "Source").objects.create(
                source_id="MIGRATION_TEST", source_name="Uji", institution="Uji", primary_url="https://example.test")
            row = state.get_model("indicators", "Observation").objects.create(
                indicator_id=indicator.pk, source_id=source.pk, observation_date="2000-01-01", period_label="Uji",
                frequency="monthly", data_type="level", value=Decimal("123.123456"), unit="%")
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            self.assertEqual(Observation.objects.get(pk=row.pk).value, Decimal("123.123456"))
        finally:
            MigrationExecutor(connection).migrate(final_targets)
