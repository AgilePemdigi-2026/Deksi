from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class ResetRequestTests(TestCase):
    def test_request_acknowledges_generically_and_delivers_only_in_memory(self):
        get_user_model().objects.create_user(
            username="reset-admin",
            email="admin@example.test",
            password="SYNTHETIC-old-account-password-731!",
            is_staff=True,
        )
        client = Client(enforce_csrf_checks=True)
        csrf = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.post(
            "/api/auth/password-reset/request/",
            {"email": "admin@example.test"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"code": "reset_request_accepted", "accepted": True})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.test"])
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        parsed = urlsplit(link)
        self.assertEqual(parsed.netloc, "127.0.0.1:62944")
        self.assertEqual(parsed.path, "/admin/reset-password")
        self.assertFalse(parsed.query)
        self.assertEqual(set(parse_qs(parsed.fragment)), {"uid", "token"})


class ResetLimiterTests(TestCase):
    def post_request(self, client, email, csrf):
        return client.post(
            "/api/auth/password-reset/request/",
            {"email": email},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )

    def test_case_aliases_share_identity_limit_without_changing_generic_response(self):
        get_user_model().objects.create_user(
            username="limited",
            email="admin@example.test",
            password="SYNTHETIC-identity-only-password-826!",
            is_staff=True,
        )
        client = Client(enforce_csrf_checks=True)
        csrf = client.get("/api/auth/csrf/").json()["csrfToken"]
        for email in ["admin@example.test", "ADMIN@example.test", " admin@example.test ", "Admin@Example.Test"]:
            response = self.post_request(client, email, csrf)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json(), {"code": "reset_request_accepted", "accepted": True})
        self.assertEqual(len(mail.outbox), 3)

    def test_ip_limit_applies_to_unknown_email_and_ignores_forwarded_header(self):
        client = Client(enforce_csrf_checks=True)
        csrf = client.get("/api/auth/csrf/").json()["csrfToken"]
        for index in range(20):
            self.assertEqual(self.post_request(client, f"unknown-{index}@example.test", csrf).status_code, 202)
        response = client.post(
            "/api/auth/password-reset/request/",
            {"email": "other@example.test"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_X_FORWARDED_FOR="198.51.100.200",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"code": "rate_limited"})


class ResetTestCase(TestCase):
    old_password = "SYNTHETIC-original-Admin-password-572!"
    new_password = "SYNTHETIC-replacement-Account-password-916!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="flow-admin", email="flow@example.test", password=cls.old_password, is_staff=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/auth/csrf/").json()["csrfToken"]

    def credentials(self):
        return {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": default_token_generator.make_token(self.user),
        }

    def post(self, action, data):
        return self.client.post(
            f"/api/auth/password-reset/{action}/", data, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf
        )


class ResetFlowTests(ResetTestCase):
    def test_native_capability_check_is_read_only_and_does_not_expose_account(self):
        capability = self.credentials()
        original = self.user.password
        for _ in range(2):
            response = self.post("check", capability)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"valid": True})
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertEqual(self.client.get("/api/auth/password-reset/check/").status_code, 405)
        self.user.refresh_from_db()
        self.assertTrue(self.user.password == original)
        self.assertTrue(default_token_generator.check_token(self.user, capability["token"]))

    def test_native_capability_expires_after_thirty_minutes(self):
        start = datetime(2026, 1, 1)
        with patch.object(default_token_generator, "_now", return_value=start):
            capability = self.credentials()
        with patch.object(default_token_generator, "_now", return_value=start + timedelta(seconds=1801)):
            response = self.post("check", capability)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"code": "invalid_reset_link"})

    def test_confirm_changes_password_once_revokes_old_api_and_admin_sessions_without_auto_login(self):
        old_session = Client()
        old_session.force_login(self.user, backend="admin_auth.backends.AdminBackend")
        self.assertTrue(old_session.get("/api/auth/session/").json()["authenticated"])
        native_session = Client()
        native_session.force_login(self.user, backend="admin_auth.backends.AdminBackend")
        self.assertEqual(native_session.get("/admin/").status_code, 200)
        self.user.refresh_from_db()
        capability = self.credentials()
        data = {**capability, "newPassword": self.new_password, "confirmPassword": self.new_password}
        response = self.post("confirm", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"code": "reset_complete", "authenticated": False})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertFalse(self.user.check_password(self.old_password))
        self.assertEqual(native_session.get("/admin/").status_code, 302)
        self.assertFalse(old_session.get("/api/auth/session/").json()["authenticated"])
        self.assertFalse(self.client.get("/api/auth/session/").json()["authenticated"])
        self.assertEqual(self.post("confirm", data).status_code, 400)
        self.assertEqual(self.post("check", capability).json(), {"code": "invalid_reset_link"})
        login = self.client.post(
            "/api/auth/login/",
            {"identifier": self.user.username, "password": self.new_password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(login.status_code, 200)
