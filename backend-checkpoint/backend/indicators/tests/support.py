from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from indicators.models import Indicator, Observation, Source


class IndicatorCase(TestCase):
    def setUp(self):
        self.reviewer = get_user_model().objects.create_user(username="reviewer-test", is_staff=True)
        self.indicator = Indicator.objects.create(code="inflasi", name="Inflasi UJI SINTETIS", category="Uji", unit="%")
        self.source = Source.objects.create(source_id="TEST_ONLY", source_name="Dataset UJI SINTETIS",
                                            institution="INSTANSI UJI SINTETIS", primary_url="https://example.test/source")

    def observation(self, **changes):
        fields = {"indicator": self.indicator, "source": self.source, "observation_date": date(2000, 1, 31),
                  "period_label": "Januari 2000", "frequency": "monthly", "data_type": "yoy",
                  "value": Decimal("0"), "unit": "%", "validation_status": Observation.Status.PUBLISHED,
                  "reviewed_by": self.reviewer, "reviewed_at": timezone.now()}
        fields.update(changes)
        return Observation.objects.create(**fields)
