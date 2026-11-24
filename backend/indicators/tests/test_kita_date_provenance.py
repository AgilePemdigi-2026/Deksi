from datetime import date
from unittest import TestCase

from indicators.kemenkeu import find_period_info


class KitaDateProvenanceTests(TestCase):
    def test_observation_date_alone_is_not_publication_date(self):
        self.assertEqual(find_period_info('Realisasi APBN s.d. 30 September 2026'),
                         (date(2026, 9, 30), None))

    def test_unlabeled_date_is_not_assumed_publication_date(self):
        text = '9 Oktober 2026. Realisasi APBN s.d. 30 September 2026.'
        self.assertEqual(find_period_info(text), (date(2026, 9, 30), None))
