from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from apps.indicators.admin import SourceTraceRevisionAdmin
from apps.indicators.models import SourceTraceRevision
from apps.indicators.revisions import submit_revision
from .helpers import RevisionTestCase


class RevisionAdminTests(RevisionTestCase):
    def test_mixed_invalid_bulk_publication_is_atomic_and_reports_error(self):
        first = self.make_revision(published=False)
        second = self.make_revision(year=2023, published=False)
        submit_revision(first.pk, self.reviewer)
        request = RequestFactory().post('/admin/indicators/sourcetracerevision/')
        request.user = self.reviewer
        request.session = {}
        request._messages = FallbackStorage(request)
        model_admin = SourceTraceRevisionAdmin(SourceTraceRevision, admin.site)
        model_admin.publish_selected(request, SourceTraceRevision.objects.filter(pk__in=[first.pk, second.pk]).order_by('-data_point__period_year'))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.publication_status, 'pending_review')
        self.assertEqual(second.publication_status, 'draft')
        self.assertTrue(list(request._messages))

    def test_revision_admin_cannot_add_edit_content_or_delete(self):
        request = RequestFactory().get('/admin/')
        request.user = self.reviewer
        model_admin = SourceTraceRevisionAdmin(SourceTraceRevision, admin.site)
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertIn('snapshot', model_admin.readonly_fields)
        self.assertIn('publication_status', model_admin.readonly_fields)
