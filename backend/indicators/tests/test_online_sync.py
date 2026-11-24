"""Offline online-source request/worker acceptance; never use a user database."""
import json
import os
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from indicators.models import Source
from indicators.resync_model import ResyncJob

RATE_HTML = (b'<table><tr><th>No</th><th>Tanggal</th><th>BI-Rate</th></tr>'
    b'<tr><td>1</td><td>21 Oktober 2026</td><td>5,75 %</td></tr></table>')
JISDOR_HTML = (b'<table><tr><th>Tanggal</th><th>Kurs</th></tr>'
    b'<tr><td>21 Oktober 2026</td><td>Rp 15.000,00</td></tr></table>')
RESERVE_HTML = (b'<table><tr><th>No</th><th>Items</th><th>30 Sep 2026</th></tr>'
    b'<tr><td>4</td><td>Cadangan Devisa (konsep IRFCL) dalam juta USD</td><td>150.000</td></tr></table>')


def bi_response(url, params=None):
    if 'BI-Rate.aspx' in url:
        return RATE_HTML
    if 'jisdor/Default.aspx' in url:
        return JISDOR_HTML
    if 'indikator-moneter.aspx' in url:
        return RESERVE_HTML
    raise AssertionError('Unexpected synthetic URL')


class OnlineRequestTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(DEKSI_RAW_DIR=Path(directory)))
        self.client = Client(enforce_csrf_checks=True)
        user = get_user_model().objects.create_user(username='online-test', is_staff=True)
        self.client.force_login(user)
        self.csrf = self.client.get('/api/auth/csrf/').json()['csrfToken']

    def test_online_bi_and_bkpm_can_queue_without_fetching(self):
        for source_id, method, endpoint, data_format in [
            ('BI', 'web_bi', 'https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx', 'html'),
            ('BKPM', 'web_bkpm', 'https://data.bkpm.go.id/dataset', 'json'),
        ]:
            Source.objects.filter(source_id=source_id).update(acquisition_method=method, endpoint_url=endpoint,
                                                            data_format=data_format)
            response = self.client.post(f'/api/admin/sources/{source_id}/resync/',
                json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
                HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(response.status_code, 202, (source_id, response.content))
            self.assertEqual(response.json()['status'], 'queued')
        self.assertEqual(ResyncJob.objects.count(), 2)

    def test_old_file_modes_remain_unsupported_for_online_jobs(self):
        for source_id in ('BI', 'BKPM'):
            response = self.client.post(f'/api/admin/sources/{source_id}/resync/',
                json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
                HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(response.status_code, 400)
        self.assertFalse(ResyncJob.objects.exists())

    def test_real_request_worker_and_parsers_stage_bi_without_publication(self):
        from indicators.models import Observation, ObservationCandidate, RawFile
        from indicators.resync_worker import process_one

        Source.objects.filter(source_id='BI').update(acquisition_method='web_bi', data_format='html',
            endpoint_url='https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx')
        response = self.client.post('/api/admin/sources/BI/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=bi_response):
            job = process_one()
        self.assertEqual(job.status, 'success')
        self.assertEqual(ObservationCandidate.objects.filter(source__source_id='BI', status='pending').count(), 3)
        self.assertEqual(RawFile.objects.filter(source__source_id='BI').count(), 3)
        self.assertFalse(Observation.objects.exists())
        self.assertIsNone(ObservationCandidate.objects.first().reviewed_by_id)

    def test_server_advertises_capability_for_exact_source_configuration_only(self):
        Source.objects.filter(source_id='BI').update(acquisition_method='web_bi', data_format='html',
            endpoint_url='https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx')
        entries = {row['sourceId']: row for row in self.client.get('/api/admin/sources/').json()['sources']}
        self.assertIs(entries['BI'].get('resyncAvailable'), True)
        self.assertIs(entries['BKPM'].get('resyncAvailable'), False)
        self.assertIs(entries['BPS'].get('resyncAvailable'), True)
        methods = self.client.get('/api/admin/sources/acquisition-methods/').json()['methods']
        self.assertTrue({'web_bi', 'web_bkpm'} <= {method['value'] for method in methods})

    def enable_bi(self):
        Source.objects.filter(source_id='BI').update(acquisition_method='web_bi', data_format='html',
            endpoint_url='https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx')

    def queue_bi(self):
        response = self.client.post('/api/admin/sources/BI/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202)
        return response.json()['id']

    def test_repeated_sync_reuses_raw_and_pending_candidates(self):
        from indicators.models import ObservationCandidate, RawFile
        from indicators.resync_worker import process_one

        self.enable_bi()
        for _ in range(2):
            self.queue_bi()
            with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=bi_response):
                self.assertEqual(process_one().status, 'success')
        self.assertEqual(RawFile.objects.count(), 3)
        self.assertEqual(ObservationCandidate.objects.count(), 3)

    def test_deactivation_during_fetch_prevents_every_staging_write(self):
        from indicators.models import Indicator, ObservationCandidate, RawFile
        from indicators.resync_worker import process_one

        self.enable_bi()
        self.queue_bi()
        def deactivate(url, params=None):
            Source.objects.filter(source_id='BI').update(status='inactive')
            return bi_response(url)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=deactivate):
            self.assertEqual(process_one().status, 'cancelled')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())
        self.assertFalse(Indicator.objects.filter(code='birate').exists())

    def test_manual_reconciliation_fences_a_returning_worker(self):
        from indicators.models import ObservationCandidate, RawFile
        from indicators.resync_worker import process_one
        from indicators.sync_history_model import SyncRun

        self.enable_bi()
        self.queue_bi()
        def reconcile(url, params=None):
            job = ResyncJob.objects.get(status='running')
            ResyncJob.objects.filter(pk=job.pk).update(status='unknown')
            SyncRun.objects.filter(pk=job.run_id).update(status='unknown')
            return bi_response(url)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=reconcile):
            self.assertEqual(process_one().status, 'unknown')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())

    def test_partial_source_failure_is_failed_not_false_success(self):
        from indicators.models import ObservationCandidate
        from indicators.online_http import AcquisitionError
        from indicators.resync_worker import process_one

        self.enable_bi()
        self.queue_bi()
        def partial(url, params=None):
            if 'jisdor/Default.aspx' in url:
                raise AcquisitionError('private source detail must not be persisted')
            return bi_response(url)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=partial):
            job = process_one()
        self.assertEqual(job.status, 'failed')
        job.run.refresh_from_db()
        self.assertEqual(job.run.item_count, 2)
        self.assertEqual(ObservationCandidate.objects.count(), 2)
        self.assertNotIn('private', job.safe_message)

    def test_wrong_source_method_or_endpoint_never_queues(self):
        self.enable_bi()
        for changes in [
            {'acquisition_method': 'web_bkpm'},
            {'acquisition_method': 'web_bi', 'endpoint_url': 'https://example.test/'},
        ]:
            Source.objects.filter(source_id='BI').update(**changes)
            response = self.client.post('/api/admin/sources/BI/resync/',
                json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
                HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(response.status_code, 400)
        self.assertFalse(ResyncJob.objects.exists())

    def test_admin_must_explicitly_select_online_mode_with_revision(self):
        payload = {'expectedRevision': 0, 'acquisitionMethod': 'web_bi', 'dataFormat': 'html',
            'endpointUrl': 'https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx'}
        response = self.client.put('/api/admin/sources/BI/update/', json.dumps(payload),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200, response.content)
        source = Source.objects.get(source_id='BI')
        self.assertEqual(source.acquisition_method, 'web_bi')
        self.assertEqual(source.revisions.count(), 1)

    def test_bi_sync_does_not_touch_bps_or_its_published_value(self):
        from datetime import date
        from decimal import Decimal

        from django.utils import timezone

        from indicators.models import Indicator, Observation
        from indicators.resync_worker import process_one

        indicator = Indicator.objects.create(code='bps_synthetic_sentinel', name='UJI SINTETIS', unit='%')
        row = Observation.objects.create(indicator=indicator, source=Source.objects.get(source_id='BPS'),
            observation_date=date(2000, 1, 31), value=Decimal('5'), unit='%', validation_status='published',
            reviewed_by=get_user_model().objects.get(username='online-test'), reviewed_at=timezone.now())
        before = Observation.objects.filter(pk=row.pk).values().get()
        self.enable_bi()
        self.queue_bi()
        with patch('indicators.bps.fetch_series', side_effect=AssertionError('BPS must not be fetched')):
            with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=bi_response):
                self.assertEqual(process_one().status, 'success')
        self.assertEqual(Observation.objects.filter(pk=row.pk).values().get(), before)

    def test_bkpm_request_runs_concrete_adapter_and_stages_one_quarter(self):
        from indicators.models import Observation, ObservationCandidate, RawFile
        from indicators.resync_worker import process_one
        from indicators.tests.test_bkpm_online import successful_transport

        Source.objects.filter(source_id='BKPM').update(acquisition_method='web_bkpm', data_format='json',
            endpoint_url='https://data.bkpm.go.id/dataset')
        response = self.client.post('/api/admin/sources/BKPM/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202)
        transport = successful_transport()
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=transport):
            job = process_one()
        self.assertEqual(job.status, 'success')
        candidate = ObservationCandidate.objects.get()
        self.assertEqual(candidate.source.source_id, 'BKPM')
        self.assertEqual(candidate.payload['period_label'], 'Triwulan III 2026')
        self.assertEqual(candidate.status, 'pending')
        self.assertIsNone(candidate.reviewed_at)
        raw = RawFile.objects.get()
        self.assertEqual(raw.parse_status, 'parsed')
        self.assertIn('-preview.json', raw.document_name)
        self.assertFalse(Observation.objects.exists())

    def test_bkpm_worker_accepts_preview_larger_than_two_mib(self):
        import httpx
        from indicators.online_http import OfficialHTTP
        from indicators.resync_worker import process_one
        from indicators.tests.test_bkpm_online import BASE, successful_transport

        Source.objects.filter(source_id='BKPM').update(acquisition_method='web_bkpm', data_format='json',
            endpoint_url='https://data.bkpm.go.id/dataset')
        response = self.client.post('/api/admin/sources/BKPM/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202)
        fixture = successful_transport()
        key = f'{BASE}/data'
        fixture.responses[key] += b' ' * (8 * 1024 * 1024 - len(fixture.responses[key]))
        def respond(request):
            return httpx.Response(200, content=fixture(str(request.url.copy_with(query=None))))
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            def factory(**kwargs):
                return OfficialHTTP(client=client, pause=0, **kwargs)
            with patch('indicators.online_sync.OfficialHTTP', side_effect=factory):
                job = process_one()
        self.assertEqual(job.status, 'success')

    def test_bkpm_worker_rejects_preview_above_eight_mib_without_staging(self):
        import httpx
        from indicators.models import ObservationCandidate, RawFile
        from indicators.online_http import OfficialHTTP
        from indicators.resync_worker import process_one
        from indicators.tests.test_bkpm_online import BASE, successful_transport

        Source.objects.filter(source_id='BKPM').update(acquisition_method='web_bkpm', data_format='json',
            endpoint_url='https://data.bkpm.go.id/dataset')
        response = self.client.post('/api/admin/sources/BKPM/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202)
        fixture = successful_transport()
        fixture.responses[f'{BASE}/data'] += b' ' * (8 * 1024 * 1024)
        def respond(request):
            return httpx.Response(200, content=fixture(str(request.url.copy_with(query=None))))
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            with patch('indicators.online_sync.OfficialHTTP', side_effect=lambda **kw: OfficialHTTP(client=client, pause=0, **kw)):
                job = process_one()
        self.assertEqual(job.status, 'failed')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())

    def test_incomplete_bkpm_preview_stores_neither_candidate_nor_raw(self):
        from indicators.models import ObservationCandidate, RawFile
        from indicators.resync_worker import process_one
        from indicators.tests.test_bkpm_online import BASE, api_page, successful_transport

        Source.objects.filter(source_id='BKPM').update(acquisition_method='web_bkpm', data_format='json',
            endpoint_url='https://data.bkpm.go.id/dataset')
        response = self.client.post('/api/admin/sources/BKPM/resync/',
            json.dumps({'requestId': str(uuid.uuid4())}), content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 202)
        transport = successful_transport()
        transport.responses[f'{BASE}/data'] = api_page(total=20)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=transport):
            job = process_one()
        self.assertEqual(job.status, 'failed')
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())
