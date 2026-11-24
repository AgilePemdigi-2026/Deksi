from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from indicators.models import DataUpdateLog
from indicators.updates import latest_successful_update, record_update_success


class UpdateLogProvenanceTests(TestCase):
    def test_ambiguous_historical_success_is_not_a_data_update(self):
        DataUpdateLog.objects.create(source="ambiguous", status=DataUpdateLog.Status.SUCCESS)
        self.assertIsNone(latest_successful_update())

    def test_only_explicit_publication_counts_as_latest_update(self):
        published = record_update_success("published", observation_count=1, event_kind="publication")
        ambiguous = DataUpdateLog.objects.create(source="config edit", status=DataUpdateLog.Status.SUCCESS)
        DataUpdateLog.objects.filter(pk=ambiguous.pk).update(updated_at=timezone.now() + timedelta(seconds=1))
        self.assertEqual(latest_successful_update().pk, published.pk)
        self.assertEqual(DataUpdateLog.objects.filter(pk=ambiguous.pk).count(), 1)
