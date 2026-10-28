from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.indicators.models import EconomicIndicator, IndicatorDataPoint
from apps.indicators.revisions import capture_revision, publish_revision, submit_revision


class RevisionTestCase(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.reviewer = get_user_model().objects.create_user(
            email='reviewer@example.test', full_name='Synthetic reviewer',
            role='reviewer', is_staff=True,
        )

    def make_revision(self, *, value='5.2500', code='test_metric', year=2024,
                      quarter=2, month=None, period_type='quarterly', published=True,
                      data_type='official', origin='unknown'):
        indicator, _ = EconomicIndicator.objects.get_or_create(code=code, defaults={
            'name': 'Synthetic economic metric', 'short_name': 'Test',
            'category': 'pdb', 'unit': 'test units', 'data_type': data_type,
        })
        point = IndicatorDataPoint.objects.create(
            indicator=indicator, value=Decimal(value) if value is not None else None,
            period_type=period_type, period_year=year, period_quarter=quarter,
            period_month=month, period_label=f'{year}:{quarter or month or "annual"}',
            data_layer='derived' if data_type == 'derived' else 'clean',
        )
        revision = capture_revision(point.pk, data_origin=origin)
        if published:
            submit_revision(revision.pk, self.reviewer)
            revision = publish_revision(revision.pk, self.reviewer)
        return revision
