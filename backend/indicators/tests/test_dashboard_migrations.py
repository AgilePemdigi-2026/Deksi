from datetime import date
from decimal import Decimal

from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone

# Nilai aman untuk kolom Source yang ditambahkan Fitur 10. Dipakai hanya bila
# status migrasi yang diuji tidak mengenal kolom tersebut sementara tabel
# database sudah memilikinya (cabang migrasi paralel tetap teraplikasi).
_SOURCE_BACKFILL = {
    "acquisition_method": "",
    "data_format": "",
    "endpoint_url": "",
    "frequency": "",
    "update_schedule": "",
    "status": "active",
}


def _create_source_compat(hist_source_model, **kwargs):
    """Buat baris Source pada status migrasi lama yang toleran skema baru."""
    model_fields = {f.name for f in hist_source_model._meta.fields}
    create_kwargs = dict(kwargs)
    create_kwargs.update({k: v for k, v in _SOURCE_BACKFILL.items() if k in model_fields})
    try:
        return hist_source_model.objects.create(**create_kwargs)
    except IntegrityError:
        pass
    table = hist_source_model._meta.db_table
    field_by_column = {f.column: f for f in hist_source_model._meta.fields}
    auto_column = hist_source_model._meta.auto_field.column if hist_source_model._meta.auto_field else None
    with connection.cursor() as cur:
        db_columns = [c.name for c in connection.introspection.get_table_description(cur, table)]
    insert_columns, params = [], []
    for column in db_columns:
        if column == auto_column:
            continue
        field = field_by_column.get(column)
        if field is not None and field.name in create_kwargs:
            params.append(create_kwargs[field.name])
        elif column in _SOURCE_BACKFILL:
            params.append(_SOURCE_BACKFILL[column])
        elif field is not None and (getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False)):
            params.append(timezone.now())
        elif field is not None:
            params.append(field.get_default())
        else:
            params.append(None)
        insert_columns.append(f'"{column}"')
    placeholders = ", ".join(["%s"] * len(insert_columns))
    with connection.cursor() as cur:
        cur.execute(
            f'INSERT INTO "{table}" ({", ".join(insert_columns)}) VALUES ({placeholders}) RETURNING "id"',
            params,
        )
        source_pk = cur.fetchone()[0]
    return hist_source_model.objects.get(pk=source_pk)


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
            source = _create_source_compat(
                apps.get_model("indicators", "Source"),
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
