"""Cross-feature checks on disposable storage, never production configuration."""
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase


class EngineAIIntegrationTests(TestCase):
    def test_main_and_ai_schema_have_one_shared_leaf(self):
        loader = MigrationLoader(None)
        self.assertEqual(loader.detect_conflicts(), {})
        self.assertEqual(loader.graph.leaf_nodes('indicators'),
                         [('indicators', '0026_merge_ai_narrative_main')])
        migration = loader.disk_migrations[('indicators', '0026_merge_ai_narrative_main')]
        self.assertEqual(migration.operations, [])
        self.assertEqual(set(migration.dependencies), {
            ('indicators', '0025_ai_narrative_drafts'),
            ('indicators', '0025_merge_20261124_2326'),
        })

    def test_public_calculations_do_not_enable_admin_generation_or_draft_preview(self):
        public = self.client.get('/api/economic-engine/gdp/')
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json()['methodVersion'], 'bps-gdp-shares.v3')
        self.assertIn(self.client.get('/api/admin/ai-narratives/capabilities/').status_code, (401, 403))
        self.assertEqual(self.client.get('/api/preview-engine-narrative/').status_code, 404)
