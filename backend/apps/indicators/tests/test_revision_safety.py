import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, IntegrityError, models, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase

from apps.indicators.models import EconomicIndicator, SourceTraceRevision
from apps.indicators.source_trace import capture_revision, decimal_string, digest, review_revision, safe_url
from .support import reviewer, revision_candidate, working_trace


class RevisionSafetyTests(TestCase):
    def setUp(self):
        self.trace = working_trace()
        self.actor = reviewer()

    def test_default_queryset_mutations_and_parent_deletion_are_blocked(self):
        rev = capture_revision(self.trace.id)
        operations = [
            lambda: SourceTraceRevision.objects.filter(pk=rev.id).update(sequence=99),
            lambda: SourceTraceRevision.objects.filter(pk=rev.id).delete(),
            lambda: SourceTraceRevision.objects.bulk_update([rev], ['snapshot']),
            lambda: SourceTraceRevision.objects.bulk_create([rev]),
            lambda: rev.delete(),
        ]
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(ValidationError):
                operation()
        for parent in (self.trace, self.trace.data_point, self.trace.data_point.indicator):
            with self.subTest(parent=type(parent).__name__), self.assertRaises(ProtectedError):
                parent.delete()

    def test_new_instance_with_existing_id_cannot_overwrite_content(self):
        rev = capture_revision(self.trace.id)
        clone = revision_candidate(self.trace)
        clone.pk = rev.pk
        clone.snapshot['identity']['revision_id'] = str(rev.pk)
        with self.assertRaises(ValidationError):
            clone.save(force_update=True)

    def test_invalid_public_snapshot_fields_fail_before_storage(self):
        mutations = [
            lambda s: s['source'].update(publication_url=17),
            lambda s: s['identity'].update(schema_version=True),
            lambda s: s['identity'].update(revision_sequence=True),
            lambda s: s['observation'].update(value=0.5),
            lambda s: s['observation'].update(value='NaN'),
            lambda s: s['observation'].update(data_layer='raw'),
            lambda s: s['observation']['period'].update(quarter=5),
            lambda s: s['observation']['period'].update(month=1),
            lambda s: s['source'].update(fetched_at='2026-01-01T12:00:00'),
            lambda s: s.update(internal_notes='must never be copied'),
        ]
        for mutate in mutations:
            rev = revision_candidate(self.trace)
            mutate(rev.snapshot)
            with self.subTest(mutation=mutate), self.assertRaises(ValidationError):
                rev.save()
        self.assertEqual(SourceTraceRevision.objects.count(), 0)

    def test_unauthorized_or_stale_digest_review_does_not_publish(self):
        rev = capture_revision(self.trace.id)
        self.actor.is_staff = False
        self.actor.save()
        with self.assertRaises(PermissionDenied):
            review_revision(rev.id, self.actor, 'published', expected_digest=rev.content_sha256)
        self.actor.is_staff = True
        self.actor.save()
        with self.assertRaises(ValidationError):
            review_revision(rev.id, self.actor, 'published', expected_digest='0' * 64)
        rev.refresh_from_db()
        self.assertEqual(rev.publication_status, 'draft')
        self.assertIsNone(rev.reviewed_at)

    def test_rejected_content_cannot_later_be_published_or_edited(self):
        rev = capture_revision(self.trace.id)
        original = copy.deepcopy(rev.snapshot)
        review_revision(rev.id, self.actor, 'rejected', expected_digest=rev.content_sha256)
        with self.assertRaises(ValidationError):
            review_revision(rev.id, self.actor, 'published', expected_digest=rev.content_sha256)
        rev.refresh_from_db()
        self.assertEqual(rev.snapshot, original)
        self.assertEqual(digest(rev.snapshot), rev.content_sha256)
        self.assertIsNone(rev.published_at)

    def test_capture_uses_trace_evidence_not_master_formula_and_does_no_network_io(self):
        point = self.trace.data_point
        indicator = point.indicator
        indicator.data_type = 'derived'
        indicator.formula = 'MASTER MUST NOT BE USED'
        indicator.save()
        point.data_layer = 'derived'
        point.value = None
        point.save()
        self.trace.formula_used = 'synthetic_formula(x)'
        self.trace.formula_inputs_detail = {'unsupported_legacy_key': 'private'}
        self.trace.publication_url = 'javascript:alert(1)'
        self.trace.save()
        with patch('socket.socket.connect', side_effect=AssertionError('Unexpected network access')):
            # Local DB connection is already established by setup; capture may use it, not source URLs.
            rev = capture_revision(self.trace.id)
        self.assertIsNone(rev.snapshot['observation']['value'])
        self.assertEqual(rev.snapshot['calculation']['expression'], 'synthetic_formula(x)')
        self.assertEqual(rev.snapshot['calculation']['inputs'], [])
        self.assertIsNone(rev.snapshot['source']['publication_url'])
        self.assertEqual(rev.snapshot['data_origin'], 'unknown')

    def test_decimal_zero_and_boundaries_are_exact(self):
        for value, expected in [(0, '0.0000'), ('-1.125', '-1.1250'), ('9999999999999999.9999', '9999999999999999.9999')]:
            with self.subTest(value=value):
                self.assertEqual(decimal_string(value), expected)
        for value in (True, 1.5, '0.00001', 'Infinity', '10000000000000000'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                decimal_string(value)

    def test_url_validation_is_metadata_only(self):
        for value in ('javascript:x', 'data:text/plain,x', 'https://user:password@example.invalid/', 'https://example.invalid/\n', 'https://example.invalid\\evil', 'https://example.invalid:999999/'):
            with self.subTest(value=value):
                self.assertIsNone(safe_url(value))
        self.assertEqual(safe_url('https://example.invalid/release'), 'https://example.invalid/release')


class RevisionPostgreSQLTests(TransactionTestCase):
    def test_concurrent_review_commits_only_one_terminal_decision(self):
        trace = working_trace()
        actor = reviewer()
        rev = capture_revision(trace.id)
        gate = Barrier(2)

        def review(decision):
            close_old_connections()
            try:
                gate.wait(timeout=10)
                try:
                    review_revision(rev.id, actor, decision, expected_digest=rev.content_sha256)
                    return 'committed'
                except ValidationError:
                    return 'conflict'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(review, decision) for decision in ('published', 'rejected')]
            self.assertEqual(sorted(f.result(timeout=20) for f in futures), ['committed', 'conflict'])
        rev.refresh_from_db()
        self.assertIn(rev.publication_status, ('published', 'rejected'))
        self.assertEqual(digest(rev.snapshot), rev.content_sha256)

    def test_database_itself_rejects_duplicate_or_nonpositive_sequences(self):
        from uuid import uuid4

        trace = working_trace()
        rev = capture_revision(trace.id)
        for sequence in (1, 0):
            duplicate = SourceTraceRevision(
                id=uuid4(), source_trace=trace, data_point=trace.data_point,
                indicator=trace.data_point.indicator, sequence=sequence,
                snapshot=rev.snapshot, content_sha256=rev.content_sha256,
            )
            with self.subTest(sequence=sequence), self.assertRaises(IntegrityError), transaction.atomic():
                models.QuerySet(model=SourceTraceRevision).bulk_create([duplicate])

    def test_concurrent_capture_allocates_distinct_ordered_sequences(self):
        self.assertEqual(connection.vendor, 'postgresql')
        trace = working_trace()
        gate = Barrier(2)

        def capture():
            close_old_connections()
            try:
                gate.wait(timeout=10)
                rev = capture_revision(trace.id)
                return rev.sequence
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(capture) for _ in range(2)]
            self.assertEqual(sorted(f.result(timeout=20) for f in futures), [1, 2])
        ordered = list(SourceTraceRevision.objects.order_by('sequence'))
        self.assertEqual(ordered[1].previous_revision_id, ordered[0].id)

    def test_additive_migration_can_reverse_and_reapply_without_changing_working_data(self):
        trace = working_trace()
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([('indicators', '0001_initial')])
            self.assertNotIn('source_trace_revisions', connection.introspection.table_names())
            self.assertTrue(EconomicIndicator.objects.filter(pk=trace.data_point.indicator_id).exists())
        finally:
            MigrationExecutor(connection).migrate([('indicators', '0002_source_trace_revision')])
        self.assertIn('source_trace_revisions', connection.introspection.table_names())
