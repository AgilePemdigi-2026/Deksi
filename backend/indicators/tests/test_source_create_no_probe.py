import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from indicators.models import Source, SourceRevision


class SourceCreateNoProbeTests(TestCase):
    def test_create_saves_metadata_without_contacting_endpoint(self):
        user = get_user_model().objects.create_user(username="create-admin", is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        csrf = client.get('/api/auth/csrf/').json()['csrfToken']
        payload = {
            'sourceId': 'NOPROBE', 'sourceName': 'Synthetic source', 'institution': 'Synthetic',
            'primaryUrl': 'https://example.test/', 'acquisitionMethod': 'api_bps',
            'endpointUrl': 'http://127.0.0.1:34567/private', 'dataFormat': 'json',
            'frequency': 'monthly', 'status': 'active',
        }
        with patch('indicators.source_admin_views._probe_endpoint_reachable', side_effect=AssertionError('unexpected request')):
            response = client.post('/api/admin/sources/create/', json.dumps(payload),
                                   content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 201)
        source = Source.objects.get(source_id='NOPROBE')
        self.assertEqual(source.endpoint_url, payload['endpointUrl'])
        self.assertEqual(SourceRevision.objects.get(source=source).version, 1)
