from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TransactionTestCase


class DashboardMigrationGraphTests(SimpleTestCase):
    def test_feedback_and_provenance_have_one_migration_leaf(self):
        loader = MigrationLoader(None)
        self.assertEqual(loader.detect_conflicts(), {})
        self.assertEqual(len(loader.graph.leaf_nodes("indicators")), 1)


class DashboardMigrationUpgradeTests(TransactionTestCase):
    def upgrade_from(self, migration_name, value, *, feedback_exists):
        executor = MigrationExecutor(connection)
        final_targets = executor.loader.graph.leaf_nodes()
        old_targets = [("indicators", migration_name)]
        try:
            executor.migrate(old_targets)
            apps = executor.loader.project_state(old_targets).apps
            indicator = apps.get_model("indicators", "Indicator").objects.create(
                code="synthetic-migration",
                name="SYNTHETIC migration",
                category="Test",
                unit="Rp",
            )
            source = apps.get_model("indicators", "Source").objects.create(
                source_id="TEST_MIGRATION",
                source_name="SYNTHETIC",
                institution="SYNTHETIC",
                primary_url="https://example.test/migration",
            )
            observation = apps.get_model("indicators", "Observation").objects.create(
                indicator=indicator,
                source=source,
                observation_date=date(2000, 1, 1),
                period_label="2000",
                frequency="annual",
                data_type="level",
                value=Decimal(value),
                unit="Rp",
            )
            if feedback_exists:
                feedback = apps.get_model("indicators", "Feedback").objects.create(
                    category="other",
                    description="SYNTHETIC feedback before merge",
                )
            executor = MigrationExecutor(connection)
            executor.migrate(final_targets)
            final_apps = executor.loader.project_state(final_targets).apps
            restored = final_apps.get_model("indicators", "Observation").objects.get(pk=observation.pk)
            self.assertEqual(restored.value, Decimal(value))
            self.assertEqual(restored.period_label, "2000")
            self.assertEqual(restored.validation_status, "pending")
            self.assertIsNone(restored.reviewed_by_id)
            self.assertEqual(restored.source_id, source.pk)
            feedback_model = final_apps.get_model("indicators", "Feedback")
            if feedback_exists:
                self.assertEqual(feedback_model.objects.get(pk=feedback.pk).description, feedback.description)
            else:
                self.assertEqual(feedback_model.objects.count(), 0)
            tables = connection.introspection.table_names()
            self.assertIn("indicators_observationcandidate", tables)
            self.assertIn("feedback", tables)
        finally:
            MigrationExecutor(connection).migrate(final_targets)

    def test_upgrade_from_feedback_branch_preserves_synthetic_rows(self):
        self.upgrade_from("0004_feedback_model", "1.234567", feedback_exists=True)

    def test_upgrade_from_provenance_branch_preserves_exact_decimal(self):
        self.upgrade_from("0005_observation_candidate", "123456789012345678.123456", feedback_exists=False)
