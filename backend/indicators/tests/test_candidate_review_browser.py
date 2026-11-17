"""Real browser -> Vite -> Django -> disposable SQLite review integration."""
import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.utils import timezone

from indicators.lifecycle import stage_observation
from indicators.models import DataUpdateLog, Indicator, Observation, ObservationCandidate, Source


class CandidateReviewBrowserTests(LiveServerTestCase):
    def test_real_browser_review_publication_and_rejection(self):
        frontend = os.environ.get('DEKSI_FRONTEND_TEST_ROOT')
        if not frontend:
            self.skipTest('DEKSI_FRONTEND_TEST_ROOT must identify the test frontend')
        user = get_user_model().objects.create_superuser(
            username='synthetic-browser-reviewer', password='synthetic-browser-review-password')
        indicator = Indicator.objects.create(code='inflasi', name='Inflasi Synthetic Review', category='Uji', unit='%')
        source = Source.objects.create(source_id='BROWSER_TEST', source_name='Synthetic Review Source',
            institution='Synthetic Institution', primary_url='https://example.test/')
        old = Observation.objects.create(indicator=indicator, source=source,
            observation_date=date(2023, 1, 31), period_label='OLD SYNTHETIC', frequency='monthly',
            data_type='yoy', value=Decimal('1.000000'), unit='%', validation_status='published',
            reviewed_by=user, reviewed_at=timezone.now())
        for number, observed, value in ((1, date(2024, 1, 1), '3.250000'),
                                        (2, date(2023, 1, 31), '7.500000'),
                                        (3, date(2025, 1, 1), '4.000000')):
            candidate = stage_observation(indicator_id=indicator.pk, source_id=source.pk,
                observation_date=observed, period_label=f'SYNTHETIC {number}', frequency='monthly',
                data_type='yoy', value=Decimal(value), unit='%')
            self.assertIsNotNone(candidate)
        env = os.environ.copy()
        env.update(DEKSI_TEST_BACKEND=self.live_server_url, DEKSI_TEST_USER='synthetic-browser-reviewer',
            DEKSI_TEST_PASS='synthetic-browser-review-password')
        result = subprocess.run(['node', str(Path(frontend) / 'tests/candidate-review-e2e.browser.mjs')],
            cwd=frontend, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS: real browser candidate review', result.stdout)
        print(result.stdout.strip())
        old.refresh_from_db()
        self.assertEqual(old.value, Decimal('1.000000'))
        rows = list(Observation.objects.filter(indicator=indicator).order_by('observation_date'))
        self.assertEqual([row.value for row in rows],
                         [Decimal('1.000000'), Decimal('3.250000'), Decimal('4.000000')])
        self.assertEqual(rows[1].reviewed_by_id, user.pk)
        self.assertIsNotNone(rows[1].reviewed_at)
        self.assertEqual(set(ObservationCandidate.objects.filter(source=source).values_list('status', flat=True)),
                         {'published', 'rejected'})
        self.assertEqual(DataUpdateLog.objects.filter(event_kind='publication', updated_by=user).count(), 2)
