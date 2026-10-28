from copy import deepcopy
from decimal import Decimal


from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models.deletion import ProtectedError

from apps.indicators.models import IndicatorDataPoint, SourceTrace, SourceTraceRevision
from apps.indicators.revisions import capture_revision, publish_revision, submit_revision
from apps.indicators.snapshots import decimal_string, safe_url
from .helpers import RevisionTestCase


class RevisionStorageTests(RevisionTestCase):
    def test_new_revision_starts_draft_and_needs_explicit_review(self):
        rev = self.make_revision(published=False)
        self.assertIsNone(rev.reviewed_by_id)
        self.assertIsNone(rev.published_at)
        with self.assertRaises(ValidationError):
            publish_revision(rev.pk, self.reviewer)
        submit_revision(rev.pk, self.reviewer)
        result = publish_revision(rev.pk, self.reviewer)
        self.assertEqual(result.reviewed_by_id, self.reviewer.pk)
        self.assertIsNotNone(result.reviewed_at)

    def test_ordinary_or_deactivated_admin_cannot_publish(self):
        rev = self.make_revision(published=False)
        ordinary = get_user_model().objects.create_user(email='admin@example.test', full_name='Test admin', role='admin', is_staff=True)
        with self.assertRaises(PermissionDenied):
            submit_revision(rev.pk, ordinary)
        get_user_model().objects.filter(pk=self.reviewer.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            submit_revision(rev.pk, self.reviewer)
        rev.refresh_from_db()
        self.assertEqual(rev.publication_status, 'draft')

    def test_publication_cannot_inherit_a_working_point_status(self):
        rev = self.make_revision(published=False)
        IndicatorDataPoint.objects.filter(pk=rev.data_point_id).update(publication_status='published')
        rev.refresh_from_db()
        self.assertEqual(rev.publication_status, 'draft')
        self.assertIsNone(rev.reviewed_by_id)

    def test_demo_revision_cannot_be_published_as_production(self):
        rev = self.make_revision(published=False, origin='demo')
        submit_revision(rev.pk, self.reviewer)
        with self.assertRaises(ValidationError):
            publish_revision(rev.pk, self.reviewer)

    def test_snapshot_updates_and_bulk_writes_are_rejected(self):
        rev = self.make_revision()
        rev.snapshot['observation']['value'] = '99.0000'
        for operation in [lambda: rev.save(), lambda: rev.delete(),
                          lambda: SourceTraceRevision.objects.filter(pk=rev.pk).update(snapshot=rev.snapshot),
                          lambda: SourceTraceRevision.objects.filter(pk=rev.pk).delete(),
                          lambda: SourceTraceRevision.objects.bulk_update([rev], ['snapshot']),
                          lambda: SourceTraceRevision.objects.bulk_create([rev])]:
            with self.subTest(operation=operation), self.assertRaises(ValidationError):
                operation()
        rev.refresh_from_db()
        self.assertEqual(rev.snapshot['observation']['value'], '5.2500')

    def test_parent_point_and_indicator_deletion_are_protected(self):
        rev = self.make_revision()
        with self.assertRaises(ProtectedError):
            rev.data_point.delete()
        with self.assertRaises(ProtectedError):
            rev.data_point.indicator.delete()

    def test_capture_sequence_is_point_anchored_when_trace_arrives_later(self):
        first = self.make_revision()
        SourceTrace.objects.create(data_point=first.data_point, institution_name='Synthetic institution')
        second = capture_revision(first.data_point_id)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(second.previous_revision_id, first.pk)
        self.assertIsNotNone(second.source_trace_id)
        first.refresh_from_db()
        self.assertIsNone(first.snapshot['identity']['trace_id'])

    def test_duplicate_revision_sequence_is_a_database_constraint(self):
        rev = self.make_revision()
        second = capture_revision(rev.data_point_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            models.QuerySet.update(SourceTraceRevision.objects.filter(pk=second.pk), sequence=rev.sequence)

    def test_database_prevents_published_without_review(self):
        rev = self.make_revision(published=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            models.QuerySet.update(SourceTraceRevision.objects.filter(pk=rev.pk), publication_status='published')

    def test_raw_and_inconsistent_layer_cannot_be_captured(self):
        rev = self.make_revision(published=False)
        for layer in ['raw', 'derived']:
            IndicatorDataPoint.objects.filter(pk=rev.data_point_id).update(data_layer=layer)
            with self.subTest(layer=layer), self.assertRaises(ValidationError):
                capture_revision(rev.data_point_id)
        self.assertEqual(SourceTraceRevision.objects.count(), 1)

    def test_invalid_period_shape_cannot_be_captured(self):
        rev = self.make_revision(published=False)
        IndicatorDataPoint.objects.filter(pk=rev.data_point_id).update(period_month=3)
        with self.assertRaises(ValidationError):
            capture_revision(rev.data_point_id)

    def test_decimal_contract_does_not_round_or_fill_missing(self):
        self.assertEqual(decimal_string(Decimal('-9999999999999999.9999')), '-9999999999999999.9999')
        self.assertEqual(decimal_string(0), '0.0000')
        self.assertIsNone(decimal_string(None))
        for bad in [True, 1.2, Decimal('1.23456'), Decimal('1e16'), Decimal('NaN'), Decimal('Infinity')]:
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                decimal_string(bad)

    def test_unsafe_urls_are_metadata_not_network_requests(self):
        for url in ['javascript:alert(1)', 'data:text/html,x', '//example.test/path', 'https://u:p@example.test/', 'https://example.test/\\path', 'https://example.test/\npath']:
            self.assertIsNone(safe_url(url))
        self.assertEqual(safe_url('https://example.test/publication'), 'https://example.test/publication')

    def test_derived_formula_is_not_evaluated_or_legacy_inputs_exposed(self):
        rev = self.make_revision(data_type='derived', published=False)
        SourceTrace.objects.create(data_point=rev.data_point, institution_name='Test institution',
                                   formula_used='untrusted expression', formula_inputs_detail={'private': 'do not expose'})
        newer = capture_revision(rev.data_point_id)
        self.assertEqual(newer.snapshot['calculation']['expression'], 'untrusted expression')
        self.assertEqual(newer.snapshot['calculation']['inputs'], [])
        self.assertIsNone(newer.snapshot['change'])
        self.assertNotIn('private', str(newer.snapshot))

    def test_publication_rejects_content_tampered_after_submission(self):
        rev = self.make_revision(published=False)
        submit_revision(rev.pk, self.reviewer)
        changed = deepcopy(rev.snapshot)
        changed['indicator']['unit'] = 'forged units'
        models.QuerySet.update(SourceTraceRevision.objects.filter(pk=rev.pk), snapshot=changed)
        with self.assertRaises(ValidationError):
            publish_revision(rev.pk, self.reviewer)
