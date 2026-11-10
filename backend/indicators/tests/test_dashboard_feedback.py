import json

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase

from indicators.feedback_model import Feedback


class DashboardFeedbackTests(TestCase):
    def payload(self, **changes):
        return {"category": "other", "description": "SYNTHETIC feedback for isolated tests", **changes}

    def post(self, data=None, **headers):
        return self.client.post(
            "/api/feedback/",
            self.payload() if data is None else data,
            content_type="application/json",
            **headers,
        )

    def test_anonymous_feedback_is_pending_and_response_is_minimal(self):
        response = self.post(self.payload(status="resolved", admin_notes="FORGED", sender_email="sender@example.test"))
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(set(payload), {"id", "status", "message"})
        self.assertEqual(payload["status"], "pending")
        stored = Feedback.objects.get(pk=payload["id"])
        self.assertEqual(stored.description, self.payload()["description"])
        self.assertEqual(stored.sender_email, "sender@example.test")
        self.assertEqual(stored.admin_notes, "")
        self.assertEqual(stored.status, Feedback.Status.PENDING)
        self.assertEqual(self.client.get("/api/feedback/").status_code, 405)

    def test_non_string_fields_return_400_not_server_error(self):
        self.client.raise_request_exception = False
        for key in (
            "category",
            "description",
            "sender_name",
            "sender_email",
            "related_indicator_code",
            "related_period",
        ):
            with self.subTest(field=key):
                self.assertEqual(self.post(self.payload(**{key: {"unexpected": "object"}})).status_code, 400)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_feedback_post_requires_csrf_even_for_anonymous_visitors(self):
        response = Client(enforce_csrf_checks=True).post(
            "/api/feedback/",
            self.payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_categories_bootstrap_allows_valid_csrf_without_login(self):
        client = Client(enforce_csrf_checks=True)
        bootstrap = client.get("/api/feedback/categories/")
        self.assertEqual(bootstrap.status_code, 200)
        self.assertIn("csrfToken", bootstrap.json())
        self.assertIn("csrftoken", client.cookies)
        response = client.post(
            "/api/feedback/",
            self.payload(),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=bootstrap.json()["csrfToken"],
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(bootstrap["Cache-Control"], "no-store")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_invalid_types_encoding_and_duplicate_keys_are_rejected(self):
        for body in (
            b"\xff",
            b"[]",
            b"null",
            b"{",
            b'{"category":"other","extra":NaN}',
            b'{"category":"other","category":"source","description":"SYNTHETIC feedback"}',
        ):
            with self.subTest(body=body[:45]):
                self.assertEqual(self.post(body).status_code, 400)
        self.assertEqual(self.client.post("/api/feedback/", "{}", content_type="application/jsonx").status_code, 400)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_oversize_json_is_rejected_before_persistence(self):
        body = json.dumps(self.payload(extra="X" * 32769))
        self.assertEqual(self.post(body).status_code, 413)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_optional_field_lengths_are_not_silently_truncated(self):
        for key, length in (
            ("sender_name", 151),
            ("sender_email", 255),
            ("related_indicator_code", 33),
            ("related_period", 51),
        ):
            with self.subTest(field=key):
                self.assertEqual(self.post(self.payload(**{key: "X" * length})).status_code, 400)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_invalid_category_description_and_email(self):
        for changes in (
            {"category": "invalid"},
            {"description": "short"},
            {"description": "X" * 2001},
            {"sender_email": "a@.invalid"},
        ):
            with self.subTest(fields=list(changes)):
                self.assertEqual(self.post(self.payload(**changes)).status_code, 400)

    def test_forwarded_header_cannot_forge_the_recorded_peer(self):
        response = self.post(HTTP_X_FORWARDED_FOR="203.0.113.77", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Feedback.objects.get(pk=response.json()["id"]).ip_address, "127.0.0.1")

    def test_untrusted_feedback_context_is_not_written_to_logs(self):
        code = "pdb\nFORGED-LOG"
        with self.assertLogs("indicators.feedback_views", level="INFO") as captured:
            response = self.post(self.payload(related_indicator_code=code))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Feedback.objects.get(pk=response.json()["id"]).related_indicator_code, code)
        self.assertNotIn("FORGED-LOG", "\n".join(captured.output))

    def test_unpaired_surrogate_is_rejected_without_database_error(self):
        self.client.raise_request_exception = False
        response = self.post(self.payload(description="SYNTHETIC invalid surrogate \ud800"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_valid_unicode_description_at_character_limit_is_accepted(self):
        response = self.post(self.payload(description="\U0001f642" * 2000))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(Feedback.objects.get(pk=response.json()["id"]).description), 2000)

    def test_view_only_admin_cannot_use_mutating_feedback_actions(self):
        user = get_user_model().objects.create_user(username="synthetic-view-only", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_feedback"))
        request = RequestFactory().get("/admin/indicators/feedback/")
        request.user = user
        actions = admin.site._registry[Feedback].get_actions(request)
        self.assertNotIn("action_mark_resolved", actions)
        self.assertNotIn("action_mark_in_review", actions)
