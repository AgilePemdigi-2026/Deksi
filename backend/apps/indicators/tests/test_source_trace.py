from django.apps import apps
from django.test import SimpleTestCase
from django.test import TestCase
from django.core.exceptions import ValidationError

from .support import reviewer, revision_candidate, stored_revision, working_trace


class RevisionModelContractTests(SimpleTestCase):
    def test_revision_is_distinct_from_the_mutable_working_trace(self):
        models = {model.__name__: model for model in apps.get_app_config('indicators').get_models()}
        self.assertIn('SourceTraceRevision', models, 'A version label must not stand in for a stored revision.')
        revision = models['SourceTraceRevision']
        self.assertEqual(revision._meta.get_field('source_trace').many_to_one, True)
        self.assertTrue(revision._meta.get_field('snapshot').get_internal_type() == 'JSONField')


class RevisionStorageTests(TestCase):
    def test_review_publishes_only_the_selected_revision_and_only_once(self):
        from apps.indicators import source_trace

        review = source_trace.review_revision
        trace = working_trace()
        a = source_trace.capture_revision(trace.id, data_origin='demo')
        result = review(a.id, reviewer(), 'published', expected_digest=a.content_sha256)
        self.assertEqual(result.publication_status, 'published')
        self.assertIsNotNone(result.reviewed_at)
        b = source_trace.capture_revision(trace.id, data_origin='demo')
        self.assertEqual(b.publication_status, 'draft')
        self.assertEqual(b.previous_revision_id, a.id)
        with self.assertRaises(ValidationError):
            review(a.id, result.reviewed_by, 'rejected', expected_digest=a.content_sha256)

    def test_capture_reads_the_working_value_but_never_inherits_its_publication(self):
        from apps.indicators import source_trace

        capture = source_trace.capture_revision
        trace = working_trace()
        revision = capture(trace.id, data_origin='demo')
        self.assertEqual(revision.snapshot['observation']['value'], '5.0500')
        self.assertEqual(revision.publication_status, 'draft')
        self.assertIsNone(revision.reviewed_by_id)
        trace.data_point.value = '6.0000'
        trace.data_point.save()
        revision.refresh_from_db()
        self.assertEqual(revision.snapshot['observation']['value'], '5.0500')

    def test_snapshot_cannot_be_overwritten(self):
        revision = stored_revision(working_trace())
        revision.snapshot['observation']['value'] = '99.0000'
        with self.assertRaises(ValidationError):
            revision.save()
        revision.refresh_from_db()
        self.assertEqual(revision.snapshot['observation']['value'], '5.0500')

    def test_new_revision_cannot_inherit_publication(self):
        revision = revision_candidate(working_trace())
        revision.publication_status = 'published'
        with self.assertRaises(ValidationError):
            revision.save()

    def test_snapshot_identity_cannot_point_to_another_data_point(self):
        revision = revision_candidate(working_trace())
        revision.snapshot['identity']['data_point_id'] = '00000000-0000-4000-8000-000000000001'
        with self.assertRaises(ValidationError):
            revision.save()
