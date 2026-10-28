from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from django.db import DatabaseError, models

from apps.indicators.models import IndicatorDataPoint, SourceTrace, SourceTraceRevision

from apps.indicators.source_trace import capture_revision, review_revision
from .support import reviewer, working_trace


class SourceTraceAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.trace = working_trace()
        self.actor = reviewer()
        self.revision = capture_revision(self.trace.id, data_origin='demo')
        review_revision(self.revision.id, self.actor, 'published', expected_digest=self.revision.content_sha256)
        self.url = f'/api/v1/indicators/synthetic_pdb/data-points/{self.trace.data_point_id}/source-trace/'

    def test_anonymous_current_returns_the_exact_published_snapshot(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['snapshot']['identity']['revision_id'], str(self.revision.id))
        self.assertEqual(data['snapshot']['observation']['value'], '5.0500')
        self.assertEqual(data['snapshot']['data_origin'], 'demo')
        self.assertEqual(data['publication']['status'], 'published')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_pinned_revision_does_not_follow_a_later_publication(self):
        b = capture_revision(self.trace.id, data_origin='demo')
        review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        pinned = self.client.get(f'{self.url}revisions/{self.revision.id}/')
        self.assertEqual(pinned.status_code, 200)
        self.assertEqual(pinned.json()['data']['snapshot']['identity']['revision_id'], str(self.revision.id))
        self.assertEqual(self.client.get(self.url).json()['data']['snapshot']['identity']['revision_id'], str(b.id))

    def test_history_contains_only_public_revisions_of_this_observation(self):
        capture_revision(self.trace.id, data_origin='demo')
        response = self.client.get(f'{self.url}revisions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)
        self.assertEqual(response.json()['data']['results'][0]['revision_id'], str(self.revision.id))

    def test_new_draft_and_edits_to_working_rows_keep_the_last_publication_available(self):
        self.trace.institution_name = 'Unreviewed new institution'
        self.trace.save()
        point = self.trace.data_point
        point.value = '8.0000'
        point.publication_status = 'draft'
        point.save()
        capture_revision(self.trace.id)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['snapshot']['observation']['value'], '5.0500')
        self.assertNotIn('Unreviewed new institution', response.content.decode())

    def test_draft_cross_parent_and_invalid_identity_share_the_same_generic_404(self):
        draft = capture_revision(self.trace.id)
        paths = [f'{self.url}revisions/{draft.id}/', f'{self.url}revisions/{uuid4()}/',
                 self.url.replace('synthetic_pdb', 'another_code'),
                 self.url.replace(str(self.trace.data_point_id), 'invalid-uuid')]
        bodies = []
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                bodies.append(response.json())
        self.assertTrue(all(body == bodies[0] for body in bodies))

    def test_malformed_token_does_not_block_public_reads_or_open_accounts(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token not-a-valid-admin-token')
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertIn(self.client.post('/api/v1/auth/logout/').status_code, (401, 403))

    def test_partial_metadata_is_not_official_verification(self):
        data = self.client.get(self.url).json()['data']
        self.assertEqual(data['metadata']['status'], 'partial')
        self.assertEqual(data['metadata']['verification_status'], 'unassessed')
        self.assertIsNone(data['snapshot']['source']['release_date'])
        self.assertIn('snapshot.source.release_date', data['metadata']['missing_fields'])

    def test_null_and_zero_are_distinct_and_date_precision_is_preserved(self):
        point = self.trace.data_point
        point.value = None
        point.save()
        self.trace.release_date = date(2026, 1, 1)
        self.trace.fetched_at = datetime(2026, 1, 2, 3, tzinfo=timezone.utc)
        self.trace.save()
        b = capture_revision(self.trace.id)
        review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        data = self.client.get(self.url).json()['data']
        self.assertIsNone(data['snapshot']['observation']['value'])
        self.assertEqual(data['snapshot']['source']['release_date'], '2026-01-01')
        self.assertEqual(data['snapshot']['source']['fetched_at'], '2026-01-02T03:00:00+00:00')
        point.value = '0.0000'
        point.save()
        c = capture_revision(self.trace.id)
        review_revision(c.id, self.actor, 'published', expected_digest=c.content_sha256)
        self.assertEqual(self.client.get(self.url).json()['data']['snapshot']['observation']['value'], '0.0000')

    def test_private_input_references_and_values_are_not_exposed(self):
        private = capture_revision(self.trace.id)
        point = self.trace.data_point
        indicator = point.indicator
        indicator.data_type = 'derived'
        indicator.save()
        point.data_layer = 'derived'
        point.save()
        self.trace.formula_used = 'x'
        self.trace.formula_inputs_detail = {'schema_version': 1, 'inputs': [{
            'key': 'x', 'label': 'Synthetic input', 'value': '7.0000', 'unit': 'percent', 'period': None,
            'source_data_point_id': str(point.id), 'source_revision_id': str(private.id),
            'price_concept': None, 'base_year': None,
        }]}
        self.trace.save()
        b = capture_revision(self.trace.id)
        review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        data = self.client.get(self.url).json()['data']
        item = data['snapshot']['calculation']['inputs'][0]
        self.assertIsNone(item['source_revision_id'])
        self.assertIsNone(item['source_data_point_id'])
        self.assertIsNone(item['value'])
        self.assertNotIn(str(private.id), str(data))

    def test_source_text_is_json_data_and_no_network_or_internal_notes_are_used(self):
        self.trace.institution_name = '<script>not executable</script>'
        self.trace.publication_url = 'https://example.invalid/synthetic'
        self.trace.data_point.notes = 'INTERNAL-NOTES-MUST-NOT-LEAK'
        self.trace.data_point.save()
        self.trace.save()
        b = capture_revision(self.trace.id)
        review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        with patch('socket.socket.connect', side_effect=AssertionError('No source HTTP calls')):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('INTERNAL-NOTES-MUST-NOT-LEAK', response.content.decode())
        self.assertNotIn(self.actor.email, response.content.decode())

    def test_storage_failure_is_sanitized_503_without_demo_fallback(self):
        with patch('apps.indicators.views.public_revisions', side_effect=DatabaseError('INTERNAL-DB-DETAIL')):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'source_trace_unavailable')
        self.assertIsNone(response.json()['data'])
        self.assertNotIn('INTERNAL-DB-DETAIL', response.content.decode())

    def test_tampered_snapshot_is_rejected_instead_of_rendered(self):
        snapshot = self.revision.snapshot
        snapshot['observation']['value'] = '99.0000'
        # Deliberate privileged-ORM corruption, outside the protected default manager.
        models.QuerySet(model=SourceTraceRevision).filter(pk=self.revision.id).update(snapshot=snapshot)
        self.assertEqual(self.client.get(self.url).status_code, 503)

    def test_fake_published_row_without_review_binding_remains_private(self):
        models.QuerySet(model=SourceTraceRevision).filter(pk=self.revision.id).update(reviewed_by=None)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_read_methods_and_rejected_mutations_never_change_database_rows(self):
        before = list(SourceTraceRevision.objects.values())
        self.assertEqual(self.client.head(self.url).content, b'')
        self.assertEqual(self.client.options(self.url).status_code, 200)
        for method in ('post', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json()['error']['code'], 'method_not_allowed')
        self.assertEqual(list(SourceTraceRevision.objects.values()), before)

    def test_unknown_duplicate_and_invalid_page_queries_are_rejected(self):
        for path in (self.url + '?page=1', self.url + 'revisions/?page=0',
                     self.url + 'revisions/?page=1&page=2', self.url + 'revisions/?unknown=1'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 400)

    def test_history_pagination_is_bounded_and_uses_relative_links(self):
        for _ in range(20):
            b = capture_revision(self.trace.id)
            review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        response = self.client.get(self.url + 'revisions/')
        data = response.json()['data']
        self.assertEqual(data['count'], 21)
        self.assertEqual(len(data['results']), 20)
        self.assertEqual(data['next'], self.url + 'revisions/?page=2')
        second = self.client.get(data['next']).json()['data']
        self.assertEqual(len(second['results']), 1)
        self.assertIsNone(second['next'])
        self.assertEqual(self.client.get(self.url + 'revisions/?page=3').status_code, 404)

    def test_anonymous_throttle_remains_enabled(self):
        statuses = [self.client.get(self.url).status_code for _ in range(21)]
        self.assertEqual(statuses[:20], [200] * 20)
        self.assertEqual(statuses[-1], 429)
        response = self.client.get(self.url)
        self.assertIn('Retry-After', response)

    def test_previous_revision_link_skips_unpublished_parent(self):
        capture_revision(self.trace.id)
        c = capture_revision(self.trace.id)
        review_revision(c.id, self.actor, 'published', expected_digest=c.content_sha256)
        data = self.client.get(self.url).json()['data']
        self.assertEqual(data['links']['previous_revision'], f'{self.url}revisions/{self.revision.id}/')

    def test_ambiguous_legacy_trace_lineages_are_not_resolved_by_first_row(self):
        original_point = self.trace.data_point
        other = IndicatorDataPoint.objects.create(
            indicator=original_point.indicator, period_type='quarterly', period_year=2027,
            period_quarter=1, period_label='Test Q1', value='1.0000', data_layer='clean',
        )
        self.trace.data_point = other
        self.trace.save()
        trace_b = SourceTrace.objects.create(data_point=original_point, institution_name='Synthetic second lineage')
        b = capture_revision(trace_b.id)
        review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        self.assertEqual(self.client.get(self.url).status_code, 503)
        self.assertEqual(self.client.get(self.url + 'revisions/').status_code, 503)
        self.assertEqual(self.client.get(f'{self.url}revisions/{self.revision.id}/').status_code, 200)

    def test_invalid_suffix_still_has_a_scoped_json_not_found_response(self):
        response = self.client.get(self.url + 'not-an-endpoint/extra/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.json()['error']['code'], 'not_found')

    def test_valid_public_formula_input_keeps_its_exact_frozen_source_reference(self):
        point = self.trace.data_point
        indicator = point.indicator
        indicator.data_type = 'derived'
        indicator.save()
        point.data_layer = 'derived'
        point.save()
        self.trace.formula_used = 'x'
        self.trace.formula_inputs_detail = {'schema_version': 1, 'inputs': [{
            'key': 'x', 'label': 'Synthetic input', 'value': '5.0500', 'unit': 'percent',
            'period': self.revision.snapshot['observation']['period'],
            'source_data_point_id': str(point.id), 'source_revision_id': str(self.revision.id),
            'price_concept': None, 'base_year': None,
        }]}
        self.trace.save()
        b = capture_revision(self.trace.id)
        review_revision(b.id, self.actor, 'published', expected_digest=b.content_sha256)
        item = self.client.get(self.url).json()['data']['snapshot']['calculation']['inputs'][0]
        self.assertEqual(item['source_revision_id'], str(self.revision.id))
        self.assertEqual(item['value'], '5.0500')
