from .helpers import RevisionTestCase


class DetailAPITests(RevisionTestCase):
    def test_public_detail_preserves_zero_decimal_and_pinned_identity(self):
        revision = self.make_revision(value='0')
        self.client.credentials(HTTP_AUTHORIZATION='Token malformed-public-token')
        response = self.client.get('/api/v1/indicators/test_metric/detail/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['data']['snapshot']['observation']['value'], '0.0000')
        self.assertEqual(body['data']['snapshot']['identity']['revision_id'], str(revision.pk))
        self.assertIsNone(body['data']['links']['source_trace'])
        self.assertEqual(body['data']['metadata']['verification_status'], 'unassessed')
        self.assertEqual(response['Cache-Control'], 'no-store')
