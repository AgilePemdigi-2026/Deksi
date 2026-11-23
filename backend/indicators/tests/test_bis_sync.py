"""BIS on-demand integration; synthetic inputs and disposable database only."""
import json
import os
import uuid
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from indicators.models import Observation, ObservationCandidate, RawFile

ENDPOINT = 'https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.ID'
XML = b'''<?xml version="1.0"?><StructureSpecificData><DataSet>
<Series FREQ="D" REF_AREA="ID" SOURCE_REF="Bank Indonesia">
<Obs TIME_PERIOD="2026-11-13" OBS_VALUE="5.75" OBS_STATUS="A"/>
<Obs TIME_PERIOD="2026-11-14" OBS_VALUE="NaN" OBS_STATUS="M"/>
<Obs TIME_PERIOD="2026-11-16" OBS_VALUE="5.75" OBS_STATUS="A"/>
</Series></DataSet></StructureSpecificData>'''


class BISIntegrationTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(DEKSI_RAW_DIR=Path(directory)))
        self.client = Client(enforce_csrf_checks=True)
        user = get_user_model().objects.create_user(username='bis-synthetic', is_staff=True, is_superuser=True)
        self.client.force_login(user)
        self.token = self.client.get('/api/auth/csrf/').json()['csrfToken']

    def test_source_create_request_worker_and_pending_preserve_provenance(self):
        from indicators.resync_worker import process_one

        payload = {'sourceId': 'BIS', 'sourceName': 'BIS - Suku bunga Indonesia',
            'institution': 'Bank for International Settlements', 'primaryUrl': 'https://data.bis.org/',
            'description': 'Bank Indonesia melalui BIS; data dapat terlambat.', 'acquisitionMethod': 'api_bis',
            'endpointUrl': ENDPOINT, 'dataFormat': 'xml', 'frequency': 'daily', 'status': 'active'}
        created = self.client.post('/api/admin/sources/create/', json.dumps(payload),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(created.status_code, 201, created.content)
        self.assertTrue(created.json()['source']['resyncAvailable'])
        response = self.client.post('/api/admin/sources/BIS/resync/', json.dumps({'requestId': str(uuid.uuid4())}),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 202, response.content)
        with patch('indicators.online_http.OfficialHTTP.get_bytes', return_value=XML):
            job = process_one()
        self.assertEqual(job.status, 'success')
        candidate = ObservationCandidate.objects.get(source__source_id='BIS', status='pending')
        self.assertEqual(candidate.indicator.code, 'birate')
        self.assertEqual(candidate.payload['observation_date'], '2026-11-16')
        self.assertEqual(Decimal(candidate.payload['value']), Decimal('5.75'))
        self.assertEqual(RawFile.objects.get(source__source_id='BIS').source_url, ENDPOINT)
        self.assertFalse(Observation.objects.exists())
        reviewed = self.client.post(f'/api/admin/sources/BIS/candidates/{candidate.pk}/review/',
            json.dumps({'decision': 'publish', 'fingerprint': candidate.fingerprint, 'notes': 'Review sintetis'}),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(reviewed.status_code, 200, reviewed.content)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'published')
        self.assertTrue(Observation.objects.filter(source__source_id='BIS', indicator__code='birate').exists())
