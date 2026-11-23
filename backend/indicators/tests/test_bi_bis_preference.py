from datetime import date
from decimal import Decimal

from indicators.models import Source
from indicators.tests.support import IndicatorCase
from indicators.views import latest_published


class BIPreferenceTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.indicator.code = 'birate'
        self.indicator.save()
        self.bi = Source.objects.get(source_id='BI')
        self.bis = Source.objects.create(source_id='BIS', source_name='BIS test', institution='BIS', primary_url='https://example.test')

    def test_equal_dates_choose_bi_even_when_bis_inserted_last(self):
        bi = self.observation(source=self.bi, observation_date=date(2025, 1, 1), value=Decimal('5'))
        self.observation(source=self.bis, observation_date=date(2025, 1, 1), value=Decimal('6'))
        self.assertEqual(latest_published(self.indicator).pk, bi.pk)
        self.assertEqual(self.client.get('/api/indicators/?code=birate').json()['indicators'][0]['sourceId'], 'BI')
        trend = self.client.get('/api/indicators/birate/trend/').json()
        self.assertEqual({point['sourceId'] for point in trend['points']}, {'BI'})
        filtered = self.client.get('/api/indicators/dashboard/?code=birate&year=2025').json()
        self.assertEqual(filtered['indicators'][0]['sourceId'], 'BI')
        trace = self.client.get('/api/indicators/birate/source-trace/').json()
        self.assertEqual(trace['source']['sourceId'], 'BI')

    def test_newer_bis_wins_and_pending_does_not_override(self):
        self.observation(source=self.bi, observation_date=date(2025, 1, 1), value=Decimal('5'))
        bis = self.observation(source=self.bis, observation_date=date(2025, 1, 2), value=Decimal('6'))
        self.observation(source=self.bi, observation_date=date(2025, 1, 3), value=Decimal('7'),
                         validation_status='pending', reviewed_by=None, reviewed_at=None)
        self.assertEqual(latest_published(self.indicator).pk, bis.pk)
        trend = self.client.get('/api/indicators/birate/trend/').json()
        self.assertEqual({point['sourceId'] for point in trend['points']}, {'BIS'})

    def test_trend_year_selects_same_source_as_filtered_dashboard(self):
        self.observation(source=self.bi, observation_date=date(2025, 1, 1), value=Decimal('5'))
        self.observation(source=self.bis, observation_date=date(2026, 1, 2), value=Decimal('6'))
        card = self.client.get('/api/indicators/dashboard/?code=birate&year=2025').json()['indicators'][0]
        trend = self.client.get('/api/indicators/birate/trend/?year=2025').json()
        self.assertEqual(card['sourceId'], 'BI')
        self.assertEqual({point['sourceId'] for point in trend['points']}, {'BI'})
        self.assertTrue(all(point['year'] == 2025 for point in trend['points']))

    def test_trend_year_without_data_never_falls_back_to_other_year(self):
        self.observation(source=self.bis, observation_date=date(2026, 1, 2), value=Decimal('6'))
        trend = self.client.get('/api/indicators/birate/trend/?year=2025').json()
        self.assertFalse(trend['available'])
        self.assertEqual(trend['points'], [])
        self.assertEqual(self.client.get('/api/indicators/birate/trend/?year=0000').status_code, 400)

    def test_trend_year_equal_date_tie_selects_bi(self):
        self.observation(source=self.bi, observation_date=date(2025, 1, 2), value=Decimal('5'))
        self.observation(source=self.bis, observation_date=date(2025, 1, 2), value=Decimal('6'))
        trend = self.client.get('/api/indicators/birate/trend/?year=2025').json()
        self.assertEqual({point['sourceId'] for point in trend['points']}, {'BI'})

    def test_newer_bi_wins(self):
        self.observation(source=self.bis, observation_date=date(2025, 1, 1))
        bi = self.observation(source=self.bi, observation_date=date(2025, 1, 2))
        self.assertEqual(latest_published(self.indicator).pk, bi.pk)

    def test_equal_dates_bi_inserted_last_and_single_source(self):
        bis = self.observation(source=self.bis, observation_date=date(2025, 1, 1))
        self.assertEqual(latest_published(self.indicator).pk, bis.pk)
        bi = self.observation(source=self.bi, observation_date=date(2025, 1, 1))
        self.assertEqual(latest_published(self.indicator).pk, bi.pk)
