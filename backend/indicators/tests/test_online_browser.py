"""Real browser/HTTP/job integration with disposable PostgreSQL and offline source fixtures."""
import json
import os
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import connection
from django.test import LiveServerTestCase, override_settings

from indicators.models import Observation, ObservationCandidate, Source
from indicators.resync_model import ResyncJob
from indicators.resync_worker import process_one
from indicators.tests.test_bis_sync import XML
from indicators.tests.test_bkpm_online import successful_transport
from indicators.tests.test_online_sync import bi_response
from indicators.tests.test_kemenkeu_online import ARCHIVE, MEDIA, archive_body
from indicators.kemenkeu import KitaMetric, KitaResult


@skipUnless(os.environ.get('DEKSI_BROWSER_INTEGRATION') == '1', 'Requires the explicit disposable browser runner')
class OnlineBrowserIntegrationTests(LiveServerTestCase):
    host = '0.0.0.0'  # Container-only; runner publishes this port on host loopback only.
    port = 8080

    def test_browser_syncs_both_sources_and_logs_out(self):
        self.assertEqual(connection.vendor, 'postgresql', 'Use the dedicated disposable PostgreSQL runner')
        directory = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(DEKSI_RAW_DIR=Path(directory),
            ALLOWED_HOSTS=['localhost', '127.0.0.1', '0.0.0.0']))
        user = get_user_model().objects.create_user(username='online-browser-synthetic', is_staff=True,
            is_superuser=True)
        user.set_password(os.environ['DEKSI_SYNTHETIC_PASSWORD'])
        user.save()
        for source_id, method, endpoint, fmt in [
            ('BI', 'web_bi', 'https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx', 'html'),
            ('BKPM', 'web_bkpm', 'https://data.bkpm.go.id/dataset', 'json'),
            ('KEMENKEU', 'web_kemenkeu', ARCHIVE, 'pdf'),
        ]:
            Source.objects.filter(source_id=source_id).update(acquisition_method=method,
                endpoint_url=endpoint, data_format=fmt)
        Source.objects.create(source_id='BIS', source_name='BIS - Suku bunga Indonesia',
            institution='Bank for International Settlements', primary_url='https://data.bis.org/',
            acquisition_method='api_bis', endpoint_url='https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.ID',
            data_format='xml', frequency='daily', status='active')
        ready = Path('/evidence/online-browser-ready.json')
        ready.write_text(json.dumps({'ready': True, 'mode': 'synthetic-provider-disposable-postgres'}))
        for source_id in ('KEMENKEU', 'BI', 'BKPM', 'BIS'):
            deadline = time.monotonic() + 90
            while not ResyncJob.objects.filter(source__source_id=source_id, status='queued').exists():
                if time.monotonic() > deadline:
                    self.fail('Browser did not queue ' + source_id)
                time.sleep(.1)
            if source_id == 'BI':
                reader = bi_response
            elif source_id == 'BKPM':
                reader = successful_transport()
            elif source_id == 'KEMENKEU':
                def reader(url, params=None):
                    if url == ARCHIVE:
                        return archive_body()
                    if url == MEDIA:
                        return b'%PDF-' + b'x' * 1200
                    raise AssertionError('unexpected Kemenkeu URL')
            else:
                def reader(*args, **kwargs):
                    return XML
            with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=reader):
                with patch('httpx.Client.send', side_effect=AssertionError('External transport forbidden in test')):
                    if source_id == 'KEMENKEU':
                        metrics = {key: KitaMetric(key, Decimal(value), 'Rp Triliun', 'synthetic') for key, value in [
                            ('pendapatan_negara', '100'), ('belanja_negara', '120'), ('defisit_apbn', '20')]}
                        metrics['defisit_pdb'] = KitaMetric('defisit_pdb', Decimal('1.24'), '% PDB', 'synthetic')
                        parsed = KitaResult(MEDIA, date(2026, 9, 30), 'Kumulatif s.d. 30 September 2026', None, metrics)
                        with patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
                             patch('indicators.kemenkeu.parse_kita_text', return_value=parsed):
                            self.assertEqual(process_one().status, 'success')
                    else:
                        self.assertEqual(process_one().status, 'success')
        deadline = time.monotonic() + 45
        while Session.objects.exists():
            if time.monotonic() > deadline:
                self.fail('Browser did not complete logout')
            time.sleep(.1)
        self.assertEqual(ObservationCandidate.objects.filter(source__source_id='BI', status='pending').count(), 3)
        self.assertEqual(ObservationCandidate.objects.filter(source__source_id='BKPM', status='pending').count(), 1)
        self.assertEqual(ObservationCandidate.objects.filter(source__source_id='BIS', status='pending').count(), 1)
        self.assertEqual(ObservationCandidate.objects.filter(source__source_id='KEMENKEU', status='pending').count(), 4)
        self.assertFalse(Observation.objects.exists())
