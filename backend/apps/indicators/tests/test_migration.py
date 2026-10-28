from django.core.management import call_command
from django.db import connection

from apps.indicators.models import IndicatorDataPoint, SourceTraceRevision
from .helpers import RevisionTestCase


class RevisionMigrationTests(RevisionTestCase):
    def test_additive_migration_roundtrip_preserves_working_observations(self):
        revision = self.make_revision(published=False)
        point_id = revision.data_point_id
        before = IndicatorDataPoint.objects.get(pk=point_id).value
        try:
            call_command('migrate', 'indicators', '0001', verbosity=0, interactive=False)
            self.assertNotIn('source_trace_revisions', connection.introspection.table_names())
            self.assertEqual(IndicatorDataPoint.objects.get(pk=point_id).value, before)
        finally:
            call_command('migrate', 'indicators', '0002', verbosity=0, interactive=False)
        self.assertIn('source_trace_revisions', connection.introspection.table_names())
        self.assertEqual(IndicatorDataPoint.objects.get(pk=point_id).value, before)
        self.assertEqual(SourceTraceRevision.objects.count(), 0)
