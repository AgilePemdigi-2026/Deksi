"""Actual PostgreSQL race coverage for the new online staging path, offline transport."""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from indicators.models import ObservationCandidate, RawFile, Source
from indicators.resync_model import ResyncJob
from indicators.resync_worker import process_one
from indicators.sync_history_model import SyncRun
from indicators.tests.test_online_sync import bi_response


@skipUnlessDBFeature('has_select_for_update')
class OnlinePostgresTests(TransactionTestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(DEKSI_RAW_DIR=Path(directory)))
        self.user = get_user_model().objects.create_user(username='online-race', is_staff=True)
        self.source, _ = Source.objects.get_or_create(source_id='BI', defaults={
            'source_name': 'BI UJI SINTETIS', 'institution': 'INSTANSI UJI',
            'primary_url': 'https://www.bi.go.id/',
        })
        self.source.acquisition_method = 'web_bi'
        self.source.endpoint_url = 'https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx'
        self.source.data_format = 'html'
        self.source.save()
        self.job = ResyncJob.objects.create(source=self.source, requested_by=self.user, request_key=uuid.uuid4())

    def race_after_fetch(self, update):
        fetching, resume = threading.Event(), threading.Event()
        def fetch(url, params=None):
            fetching.set()
            if not resume.wait(15):
                raise TimeoutError('Synthetic race barrier expired')
            return bi_response(url)
        def work():
            close_old_connections()
            try:
                return process_one().status
            finally:
                close_old_connections()
        with patch('indicators.online_http.OfficialHTTP.get_bytes', side_effect=fetch):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(work)
                try:
                    self.assertTrue(fetching.wait(15))
                    update()
                finally:
                    resume.set()
                status = future.result(timeout=20)
        self.assertFalse(ObservationCandidate.objects.exists())
        self.assertFalse(RawFile.objects.exists())
        return status

    def test_deactivation_on_independent_connection_blocks_staging(self):
        def deactivate():
            Source.objects.filter(pk=self.source.pk).update(status='inactive')
        self.assertEqual(self.race_after_fetch(deactivate), 'cancelled')

    def test_reconciled_job_cannot_stage_after_network_returns(self):
        def reconcile():
            job = ResyncJob.objects.get(pk=self.job.pk)
            ResyncJob.objects.filter(pk=job.pk).update(status='unknown')
            SyncRun.objects.filter(pk=job.run_id).update(status='unknown')
        self.assertEqual(self.race_after_fetch(reconcile), 'unknown')
