"""Kemenkeu queue, fencing and staging on disposable synthetic data."""
import json
import os
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from indicators.kemenkeu import KitaMetric, KitaResult
from indicators.models import Observation, ObservationCandidate, RawFile, Source
from indicators.resync_worker import process_one
from indicators.tests.test_kemenkeu_online import ARCHIVE, MEDIA, archive_body


class KemenkeuQueueTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(DEKSI_RAW_DIR=Path(directory)))
        self.client = Client(enforce_csrf_checks=True)
        user = get_user_model().objects.create_user(username='kita-queue', is_staff=True)
        self.client.force_login(user)
        self.csrf = self.client.get('/api/auth/csrf/').json()['csrfToken']
        self.pdf = b'%PDF-' + b'x' * 1200
        self.parsed = KitaResult(MEDIA, date(2026, 9, 30), 'Kumulatif s.d. 30 September 2026', None,
            {key: KitaMetric(key, Decimal(value), 'Rp Triliun', 'synthetic') for key, value in [
                ('pendapatan_negara', '100'), ('belanja_negara', '120'), ('defisit_apbn', '20')]})
        self.parsed.metrics['defisit_pdb'] = KitaMetric('defisit_pdb', Decimal('1.24'), '% PDB', 'synthetic')

    def configure(self):
        response = self.client.put('/api/admin/sources/KEMENKEU/update/', json.dumps({
            'expectedRevision': 0, 'acquisitionMethod': 'web_kemenkeu', 'dataFormat': 'pdf',
            'endpointUrl': ARCHIVE}), content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200, response.content)

    def queue(self):
        response = self.client.post('/api/admin/sources/KEMENKEU/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202, response.content)

    def transport(self, url, params=None):
        if url == ARCHIVE:
            return archive_body()
        if url == MEDIA:
            return self.pdf
        raise AssertionError(url)

    def test_admin_can_queue_worker_stages_raw_and_candidates_not_public(self):
        self.configure()
        source = next(x for x in self.client.get('/api/admin/sources/').json()['sources']
                      if x['sourceId'] == 'KEMENKEU')
        self.assertTrue(source['resyncAvailable'])
        self.queue()
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=self.transport), \
             patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=self.parsed):
            job = process_one()
        self.assertEqual(job.status, 'success')
        self.assertEqual(ObservationCandidate.objects.filter(source__source_id='KEMENKEU', status='pending').count(), 4)
        self.assertEqual(RawFile.objects.get(source__source_id='KEMENKEU').source_url, MEDIA)
        self.assertFalse(Observation.objects.exists())

    def test_source_deactivated_during_fetch_writes_nothing(self):
        self.configure()
        self.queue()
        def deactivate(url, params=None):
            Source.objects.filter(source_id='KEMENKEU').update(status='inactive')
            return self.transport(url, params)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=deactivate), \
             patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=self.parsed):
            job = process_one()
        self.assertEqual(job.status, 'cancelled')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())

    def test_incomplete_pdf_reports_failure_without_staging(self):
        self.configure()
        self.queue()
        self.parsed.metrics.pop('defisit_apbn')
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=self.transport), \
             patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=self.parsed):
            job = process_one()
        self.assertEqual(job.status, 'failed')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())

    def test_missing_deficit_ratio_is_failure_not_success(self):
        self.configure()
        self.queue()
        self.parsed.metrics.pop('defisit_pdb', None)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=self.transport), \
             patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=self.parsed):
            job = process_one()
        self.assertEqual(job.status, 'failed')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())

    def test_reconciled_worker_cannot_write(self):
        from indicators.resync_model import ResyncJob
        from indicators.sync_history_model import SyncRun
        self.configure()
        self.queue()
        def reconcile(url, params=None):
            job = ResyncJob.objects.get(status='running')
            ResyncJob.objects.filter(pk=job.pk).update(status='unknown')
            SyncRun.objects.filter(pk=job.run_id).update(status='unknown')
            return self.transport(url, params)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=reconcile), \
             patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=self.parsed):
            job = process_one()
        self.assertEqual(job.status, 'unknown')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())
