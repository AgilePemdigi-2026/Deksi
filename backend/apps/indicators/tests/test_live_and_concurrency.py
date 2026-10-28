import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.db import close_old_connections, connection
from django.test import LiveServerTestCase, skipUnlessDBFeature

from apps.indicators.models import SourceTraceRevision
from apps.indicators.revisions import capture_revision
from .helpers import RevisionTestCase


class LiveHTTPTests(RevisionTestCase, LiveServerTestCase):
    def test_real_http_detail_history_pinned_and_private_accounts(self):
        revision = self.make_revision(value='0')
        path = '/api/v1/indicators/test_metric/detail/'
        with urlopen(Request(self.live_server_url+path, headers={'Authorization': 'Token malformed'}), timeout=10) as response:
            self.assertEqual(response.status, 200)
            data = json.load(response)['data']
        self.assertEqual(data['snapshot']['observation']['value'], '0.0000')
        self.assertEqual(data['snapshot']['identity']['revision_id'], str(revision.pk))
        with urlopen(self.live_server_url+data['links']['revision'], timeout=10) as response:
            pinned = json.load(response)['data']
        self.assertEqual(data['snapshot'], pinned['snapshot'])
        with urlopen(self.live_server_url+data['links']['history'], timeout=10) as response:
            self.assertEqual(json.load(response)['data']['count'], 1)
        with self.assertRaises(HTTPError) as error:
            urlopen(self.live_server_url+'/api/v1/auth/me/', timeout=10)
        self.assertIn(error.exception.code, [401, 403])


class PostgreSQLCaptureTests(RevisionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_capture_allocates_distinct_point_sequences(self):
        initial = self.make_revision(published=False)
        barrier = Barrier(2)

        def capture():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return capture_revision(initial.data_point_id).sequence
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: capture(), range(2)))
        self.assertEqual(sorted(results), [2, 3])
        self.assertEqual(list(SourceTraceRevision.objects.filter(data_point_id=initial.data_point_id).order_by('sequence').values_list('sequence', flat=True)), [1, 2, 3])
