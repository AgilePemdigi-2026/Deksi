import json

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase

from indicators.models import Source, SourceRevision


class SourceRevisionSafetyTests(TestCase):
    def setUp(self):
        self.source = Source.objects.create(
            source_id="SAFE", source_name="Original", institution="Fixture",
            primary_url="https://example.test/", acquisition_method="file_xlsx",
            data_format="xlsx", frequency="monthly",
        )
        self.user = get_user_model().objects.create_user(username="safety-admin", is_staff=True)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.csrf = self.client.get("/api/auth/csrf/").json()["csrfToken"]

    def patch(self, payload):
        return self.client.patch(
            "/api/admin/sources/SAFE/update/", json.dumps(payload),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf,
        )

    def test_null_revision_is_rejected(self):
        response = self.patch({"expectedRevision": None, "sourceName": "Stale"})
        self.assertEqual(response.status_code, 400)

    def test_missing_revision_cannot_overwrite_changes(self):
        response = self.patch({"sourceName": "Stale"})
        self.assertEqual(response.status_code, 400)
        self.source.refresh_from_db()
        self.assertEqual(self.source.source_name, "Original")

    def test_bool_revision_is_rejected(self):
        response = self.patch({"expectedRevision": True, "sourceName": "Stale"})
        self.assertEqual(response.status_code, 400)

    def test_matching_revision_version_can_update_and_read_exposes_version(self):
        response = self.patch({"expectedRevision": 0, "sourceName": "Changed"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revision"]["version"], 1)
        detail = self.client.get("/api/admin/sources/SAFE/")
        self.assertEqual(detail.json()["revisionVersion"], 1)

    def test_source_admin_is_read_only_to_preserve_revision_history(self):
        model_admin = admin.site._registry[Source]
        request = RequestFactory().get("/admin/indicators/source/")
        request.user = self.user
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

    def test_revision_history_cannot_be_deleted_from_admin(self):
        request = RequestFactory().get("/admin/indicators/sourcerevision/")
        request.user = get_user_model().objects.create_superuser(username="revision-superuser", password=None)
        self.assertFalse(admin.site._registry[SourceRevision].has_delete_permission(request))
