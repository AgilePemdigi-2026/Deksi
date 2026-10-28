import json
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from django.core.cache import cache
from django.test import LiveServerTestCase

from apps.indicators.source_trace import capture_revision, review_revision
from .support import reviewer, working_trace


class SourceTraceLiveHTTPTests(LiveServerTestCase):
    host = '127.0.0.1'

    def test_real_anonymous_http_current_pinned_history_and_private_rejection(self):
        opener = build_opener(ProxyHandler({}))
        cache.clear()
        trace = working_trace()
        actor = reviewer()
        revision = capture_revision(trace.id, data_origin='demo')
        review_revision(revision.id, actor, 'published', expected_digest=revision.content_sha256)
        root = f'/api/v1/indicators/synthetic_pdb/data-points/{trace.data_point_id}/source-trace/'
        draft = capture_revision(trace.id)
        for path in (root, f'{root}revisions/{revision.id}/', f'{root}revisions/'):
            with self.subTest(path=path), opener.open(self.live_server_url + path, timeout=10) as response:
                body = json.load(response)
                self.assertEqual(response.status, 200)
                self.assertTrue(body['success'])
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                if path.endswith('revisions/'):
                    self.assertEqual(body['data']['count'], 1)
                else:
                    self.assertEqual(body['data']['snapshot']['identity']['revision_id'], str(revision.id))
        with self.assertRaises(HTTPError) as private_error:
            opener.open(self.live_server_url + f'{root}revisions/{draft.id}/', timeout=10)
        self.assertEqual(private_error.exception.code, 404)
        with self.assertRaises(HTTPError) as mutation_error:
            opener.open(Request(self.live_server_url + root, method='POST', data=b'{}'), timeout=10)
        self.assertEqual(mutation_error.exception.code, 405)
        draft.refresh_from_db()
        self.assertEqual(draft.publication_status, 'draft')
