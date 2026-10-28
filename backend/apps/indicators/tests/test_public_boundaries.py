
from copy import deepcopy
from unittest.mock import patch

from django.db import DatabaseError, models

from apps.indicators.models import EconomicIndicator, IndicatorDataPoint, SourceTrace, SourceTraceRevision
from apps.indicators.revisions import capture_revision, publish_revision, submit_revision, withdraw_revision
from .helpers import RevisionTestCase


class PublicBoundaryTests(RevisionTestCase):
    base = '/api/v1/indicators/test_metric/'

    def test_unknown_draft_and_cross_parent_are_generic_not_found(self):
        rev = self.make_revision(published=False)
        other = self.make_revision(code='other', year=2023)
        paths = [self.base+'detail/', '/api/v1/indicators/missing/detail/',
                 self.base+f'data-points/{rev.data_point_id}/revisions/{rev.pk}/',
                 self.base+f'data-points/{other.data_point_id}/revisions/{other.pk}/',
                 self.base+'data-points/not-a-uuid/revisions/not-a-uuid/']
        bodies = []
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            bodies.append(response.json())
        self.assertTrue(all(body == bodies[0] for body in bodies))

    def test_pending_revision_is_hidden_even_to_authenticated_admin(self):
        rev = self.make_revision(published=False)
        submit_revision(rev.pk, self.reviewer)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(self.base+'detail/').status_code, 404)

    def test_null_newest_observation_does_not_fallback_to_old_nonnull(self):
        self.make_revision(quarter=1)
        self.make_revision(quarter=2, value=None)
        self.assertIsNone(self.client.get(self.base+'detail/').json()['data']['snapshot']['observation']['value'])

    def test_latest_is_chronological_not_latest_database_write(self):
        newest = self.make_revision(quarter=3)
        self.make_revision(quarter=1)
        response = self.client.get(self.base+'detail/').json()
        self.assertEqual(response['data']['snapshot']['identity']['revision_id'], str(newest.pk))

    def test_new_draft_and_working_master_edits_preserve_pinned_content(self):
        rev = self.make_revision()
        frozen = deepcopy(rev.snapshot)
        IndicatorDataPoint.objects.filter(pk=rev.data_point_id).update(value='99')
        EconomicIndicator.objects.filter(pk=rev.data_point.indicator_id).update(unit='new unit', name='Changed working name')
        capture_revision(rev.data_point_id)
        current = self.client.get(self.base+'detail/').json()['data']
        pinned = self.client.get(current['links']['revision']).json()['data']
        self.assertEqual(current['snapshot']['observation']['value'], frozen['observation']['value'])
        self.assertEqual(pinned['snapshot']['indicator']['name'], frozen['indicator']['name'])
        self.assertEqual(pinned['snapshot']['indicator']['unit'], frozen['indicator']['unit'])

    def test_history_is_ordered_paged_and_carries_pinned_revisions(self):
        for year in range(2000, 2021):
            self.make_revision(year=year, quarter=1)
        first = self.client.get(self.base+'history/').json()['data']
        self.assertEqual(first['count'], 21)
        self.assertEqual(len(first['results']), 20)
        self.assertEqual([r['period']['year'] for r in first['results']], list(range(2000, 2020)))
        second = self.client.get(first['next']).json()['data']
        self.assertEqual(second['results'][0]['period']['year'], 2020)
        self.assertIsNone(second['next'])
        self.assertEqual(second['previous'], self.base+'history/?period_type=quarterly&page=1')
        self.assertEqual(self.client.get(self.base+'history/?page=3').status_code, 404)
        self.assertEqual(self.client.get(second['results'][0]['links']['revision']).status_code, 200)

    def test_history_retains_supplied_null_and_declares_calendar_gap_policy(self):
        self.make_revision(quarter=1, value='0')
        self.make_revision(quarter=3, value=None)
        data = self.client.get(self.base+'history/').json()['data']
        self.assertEqual([r['period']['quarter'] for r in data['results']], [1, 3])
        self.assertEqual([r['value'] for r in data['results']], ['0.0000', None])
        self.assertEqual(data['gap_policy'], 'break_on_null_or_missing_period')
        self.assertEqual(data['view'], 'current_published_per_observation')

    def test_frequency_selection_is_explicit_and_empty_is_not_failure(self):
        self.make_revision()
        self.make_revision(period_type='annual', quarter=None, year=2023)
        self.assertEqual(self.client.get(self.base+'detail/').json()['error']['code'], 'series_selection_required')
        self.assertEqual(self.client.get(self.base+'detail/?period_type=quarterly').status_code, 200)
        data = self.client.get(self.base+'history/?period_type=monthly').json()['data']
        self.assertEqual(data['results'], [])
        self.assertEqual(data['count'], 0)
        self.assertEqual(self.client.get(self.base+'detail/?period_type=monthly').status_code, 404)

    def test_invalid_unknown_and_duplicate_queries_are_rejected(self):
        self.make_revision()
        for query in ['page=0', 'page=-1', 'page=1.2', 'page='+('9'*50), 'period_type=semester', 'page=1&page=2', 'secret=true', 'period_type=quarterly&period_type=monthly']:
            with self.subTest(query=query):
                response = self.client.get(self.base+'history/?'+query)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()['success'])

    def test_duplicate_period_is_not_arbitrarily_selected(self):
        self.make_revision()
        self.make_revision(value='8')
        response = self.client.get(self.base+'detail/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'ambiguous_series')

    def test_unit_changes_do_not_merge_different_series(self):
        old = self.make_revision(quarter=1)
        EconomicIndicator.objects.filter(pk=old.data_point.indicator_id).update(unit='other units')
        self.make_revision(quarter=2)
        response = self.client.get(self.base+'history/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'inconsistent_series')
        pinned = self.client.get(self.base+f'data-points/{old.data_point_id}/revisions/{old.pk}/').json()['data']
        self.assertIsNone(pinned['links']['history'])
        self.assertIn('history_context_changed', pinned['metadata']['warnings'])

    def test_withdrawal_does_not_redirect_a_pinned_revision(self):
        rev = self.make_revision()
        url = self.client.get(self.base+'detail/').json()['data']['links']['revision']
        withdraw_revision(rev.pk, self.reviewer)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(self.base+'detail/').status_code, 404)

    def test_only_latest_published_revision_of_each_point_is_in_history(self):
        rev = self.make_revision()
        newer = capture_revision(rev.data_point_id)
        submit_revision(newer.pk, self.reviewer)
        publish_revision(newer.pk, self.reviewer)
        rows = self.client.get(self.base+'history/').json()['data']['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['identity']['revision_id'], str(newer.pk))
        old_url = self.base+f'data-points/{rev.data_point_id}/revisions/{rev.pk}/'
        self.assertEqual(self.client.get(old_url).status_code, 200)

    def test_untrusted_text_url_and_internal_fields_are_projected_safely(self):
        rev = self.make_revision(published=False)
        point = rev.data_point
        point.notes = 'PRIVATE-INTERNAL-NOTE'
        point.raw_value = 'PRIVATE-RAW-CONTENT'
        point.save()
        SourceTrace.objects.create(data_point=point, institution_name='<script>synthetic</script>', publication_url='javascript:alert(1)')
        newer = capture_revision(point.pk)
        submit_revision(newer.pk, self.reviewer)
        publish_revision(newer.pk, self.reviewer)
        body = self.client.get(self.base+'detail/').json()
        source = body['data']['snapshot']['source']
        self.assertEqual(source['institution_name'], '<script>synthetic</script>')
        self.assertIsNone(source['publication_url'])
        self.assertIn('source_url_rejected', body['data']['metadata']['warnings'])
        encoded = str(body)
        for private in ['PRIVATE-INTERNAL-NOTE', 'PRIVATE-RAW-CONTENT', 'reviewer@example.test', 'formula_inputs_detail', 'snapshot_hash']:
            self.assertNotIn(private, encoded)

    def test_legacy_trend_does_not_fabricate_change(self):
        rev = self.make_revision(published=False)
        IndicatorDataPoint.objects.filter(pk=rev.data_point_id).update(trend_percent='77', trend_direction='up')
        newer = capture_revision(rev.data_point_id)
        submit_revision(newer.pk, self.reviewer)
        publish_revision(newer.pk, self.reviewer)
        data = self.client.get(self.base+'detail/').json()['data']
        self.assertIsNone(data['snapshot']['change'])
        self.assertIn('change_evidence_unavailable', data['metadata']['warnings'])

    def test_storage_failure_is_sanitized_and_never_empty_or_demo(self):
        self.make_revision()
        with patch('apps.indicators.views.current_detail', side_effect=DatabaseError('PRIVATE-DB-CONNECTION')):
            response = self.client.get(self.base+'detail/')
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(response.json()['data'])
        self.assertNotIn('PRIVATE-DB-CONNECTION', response.content.decode())

    def test_corrupted_frozen_content_is_rejected_not_recomputed(self):
        rev = self.make_revision()
        changed = deepcopy(rev.snapshot)
        changed['observation']['value'] = '99.0000'
        models.QuerySet.update(SourceTraceRevision.objects.filter(pk=rev.pk), snapshot=changed)
        response = self.client.get(self.base+'detail/')
        self.assertEqual(response.status_code, 503)

    def test_read_methods_do_not_write_and_mutations_are_not_allowed(self):
        rev = self.make_revision()
        before = list(SourceTraceRevision.objects.values())
        for method in ['post', 'put', 'patch', 'delete']:
            self.assertEqual(getattr(self.client, method)(self.base+'detail/').status_code, 405)
        self.assertEqual(self.client.head(self.base+'detail/').content, b'')
        options = self.client.options(self.base+'detail/')
        self.assertEqual(options.status_code, 200)
        self.assertNotIn('raw_value', options.content.decode())
        self.assertEqual(before, list(SourceTraceRevision.objects.values()))

    def test_accounts_endpoint_remains_private(self):
        self.assertIn(self.client.get('/api/v1/auth/me/').status_code, [401, 403])

    def test_existing_anonymous_throttle_is_preserved(self):
        self.make_revision()
        for _ in range(20):
            self.assertEqual(self.client.get(self.base+'detail/').status_code, 200)
        response = self.client.get(self.base+'detail/')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()['error']['code'], 'throttled')
        self.assertIn('Retry-After', response)
