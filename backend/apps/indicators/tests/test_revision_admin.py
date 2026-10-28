from unittest.mock import patch

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.indicators.models import SourceTrace, SourceTraceRevision
from apps.indicators.source_trace import capture_revision
from .support import reviewer, working_trace


class RevisionAdminTests(TestCase):
    def setUp(self):
        self.actor = reviewer()
        self.request = RequestFactory().post('/admin/')
        self.request.user = self.actor
        self.trace = working_trace()

    def test_working_trace_admin_can_create_a_draft_without_publication(self):
        model_admin = admin.site._registry[SourceTrace]
        actions = model_admin.get_actions(self.request)
        self.assertIn('capture_draft', actions)
        with patch.object(model_admin, 'message_user'):
            model_admin.capture_draft(self.request, SourceTrace.objects.filter(pk=self.trace.id))
        self.assertEqual(SourceTraceRevision.objects.get().publication_status, 'draft')

    def test_revision_admin_is_read_only_with_explicit_permission_checked_review_actions(self):
        model_admin = admin.site._registry.get(SourceTraceRevision)
        self.assertIsNotNone(model_admin, 'A human reviewer needs a read-only revision screen.')
        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_change_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))
        actions = model_admin.get_actions(self.request)
        self.assertIn('publish_selected', actions)
        revision = capture_revision(self.trace.id)
        with patch.object(model_admin, 'message_user'):
            model_admin.publish_selected(self.request, SourceTraceRevision.objects.filter(pk=revision.id))
        revision.refresh_from_db()
        self.assertEqual(revision.publication_status, 'published')
        self.assertEqual(revision.reviewed_by_id, self.actor.id)

    def test_review_action_is_not_available_to_a_staff_user_without_publish_permission(self):
        model_admin = admin.site._registry.get(SourceTraceRevision)
        self.assertIsNotNone(model_admin)
        self.actor.is_superuser = False
        self.actor.save()
        actions = model_admin.get_actions(self.request)
        self.assertNotIn('publish_selected', actions)
        self.assertNotIn('reject_selected', actions)
