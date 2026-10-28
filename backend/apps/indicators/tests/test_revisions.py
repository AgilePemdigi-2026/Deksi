from django.apps import apps
from django.test import TestCase
from importlib import util, import_module
from decimal import Decimal
from apps.indicators.models import EconomicIndicator, IndicatorDataPoint


class RevisionRegistrationTests(TestCase):
    def test_shared_observation_revision_is_registered(self):
        names = {model.__name__ for model in apps.get_app_config('indicators').get_models()}
        self.assertIn('SourceTraceRevision', names, 'Detail needs a shared revision, not mutable point IDs.')

    def test_capture_creates_a_draft_without_fabricating_a_trace(self):
        self.assertIsNotNone(util.find_spec('apps.indicators.revisions'), 'Revision capture service is not implemented.')
        indicator = EconomicIndicator.objects.create(code='test_metric', name='Synthetic metric', short_name='Test', category='pdb', unit='test units')
        point = IndicatorDataPoint.objects.create(indicator=indicator, value=Decimal('0'), period_type='quarterly', period_year=2024, period_quarter=2, period_label='Q2 2024')
        revision = import_module('apps.indicators.revisions').capture_revision(point.pk)
        self.assertEqual(revision.publication_status, 'draft')
        self.assertIsNone(revision.source_trace_id)
        self.assertEqual(revision.snapshot['observation']['value'], '0.0000')
        self.assertEqual(revision.snapshot['data_origin'], 'unknown')
