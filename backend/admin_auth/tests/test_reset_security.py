from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, override_settings
from django.utils import timezone

from admin_auth.models import ResetRateBucket
from admin_auth.password_reset import frontend_origin

from .test_password_reset import ResetTestCase


class ResetSecurityTests(ResetTestCase):
    def test_csrf_rejection_also_has_reset_privacy_headers(self):
        response = Client(enforce_csrf_checks=True).post(
            "/api/auth/password-reset/request/", {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_role_revocation_between_validation_and_commit_prevents_password_mutation(self):
        from admin_auth import password_reset

        original = password_reset.commit_password

        def revoked(user, form):
            get_user_model().objects.filter(pk=user.pk).update(is_staff=False)
            return original(user, form)

        with patch.object(password_reset, "commit_password", side_effect=revoked):
            result = self.post(
                "confirm",
                {**self.credentials(), "newPassword": self.new_password, "confirmPassword": self.new_password},
            )
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json(), {"code": "invalid_reset_link"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.old_password))

    @override_settings(ALLOWED_HOSTS=["untrusted.example.test", "testserver"])
    def test_request_host_never_controls_email_link_origin(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": self.user.email},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
            HTTP_HOST="untrusted.example.test",
            HTTP_X_FORWARDED_HOST="other.example.test",
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        self.assertTrue(link.startswith("http://127.0.0.1:62944/admin/reset-password#"))

    def test_body_byte_limit_is_distinct_from_field_character_limit(self):
        capability = self.credentials()
        value = "🧪" * 3000
        response = self.post("confirm", {**capability, "newPassword": value, "confirmPassword": value})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json(), {"code": "request_too_large"})
        response = self.post("confirm", {**capability, "newPassword": "x" * 4097, "confirmPassword": "x" * 4097})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"code": "invalid_request"})

    def test_malformed_capability_uses_safe_invalid_link_code(self):
        response = self.post("check", {"uid": "not+canonical", "token": "malformed"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"code": "invalid_reset_link"})

    def test_invalid_email_shapes_and_duplicate_json_fields_are_rejected(self):
        for data in [
            {},
            [],
            {"email": None},
            {"email": 123},
            {"email": ""},
            {"email": "no-email"},
            {"email": "a" * 255},
            {"email": "admin@example.test", "next": "https://evil.invalid"},
        ]:
            response = self.post("request", data)
            self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/auth/password-reset/request/",
            '{"email":"a@example.test","email":"b@example.test"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_utf8_and_nested_json_fail_safely(self):
        for body in [b"\xff", b"{", b"[" * 1100 + b"]" * 1100, b'{"email":"\\ud800@example.test"}']:
            response = self.client.post(
                "/api/auth/password-reset/request/", body, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf
            )
            self.assertEqual(response.status_code, 400)

    def test_csrf_origin_media_method_and_cache_boundaries(self):
        for action in ["request", "check", "confirm"]:
            path = f"/api/auth/password-reset/{action}/"
            self.assertEqual(
                Client(enforce_csrf_checks=True).post(path, {}, content_type="application/json").status_code, 403
            )
            self.assertEqual(
                self.client.post(
                    path,
                    {},
                    content_type="application/json",
                    HTTP_X_CSRFTOKEN=self.csrf,
                    HTTP_ORIGIN="https://evil.invalid",
                ).status_code,
                403,
            )
            response = self.client.get(path)
            self.assertEqual(response.status_code, 405)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["Allow"], "POST")
        response = self.client.post(
            "/api/auth/password-reset/request/",
            "email=admin@example.test",
            content_type="text/plain",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(len(mail.outbox), 0)

    def test_unknown_email_returns_same_acknowledgment_without_mail(self):
        response = self.post("request", {"email": "unknown@example.test"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"code": "reset_request_accepted", "accepted": True})
        self.assertEqual(len(mail.outbox), 0)

    def test_revoked_staff_inactive_and_unusable_accounts_fail_closed(self):
        original = self.user.password
        for values in [{"is_staff": False}, {"is_active": False}, {"password": "!unusable-fixture"}]:
            capability = self.credentials()
            get_user_model().objects.filter(pk=self.user.pk).update(**values)
            self.assertEqual(self.post("request", {"email": self.user.email}).status_code, 202)
            self.assertEqual(self.post("check", capability).json(), {"code": "invalid_reset_link"})
            get_user_model().objects.filter(pk=self.user.pk).update(is_staff=True, is_active=True, password=original)
        self.assertEqual(len(mail.outbox), 0)

    def test_ambiguous_email_including_other_roles_and_unicode_equivalence_never_selects_first(self):
        capability = self.credentials()
        get_user_model().objects.create_user(
            username="ambiguous-public", email="\uff26\uff2c\uff2f\uff37@example.test", password=None, is_staff=False
        )
        response = self.post("request", {"email": "flow@example.test"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.post("check", capability).json(), {"code": "invalid_reset_link"})

    def test_email_or_last_login_changes_invalidate_native_token(self):
        for values in [{"email": "changed@example.test"}, {"last_login": timezone.now()}]:
            self.user.refresh_from_db()
            capability = self.credentials()
            get_user_model().objects.filter(pk=self.user.pk).update(**values)
            self.assertEqual(self.post("check", capability).json(), {"code": "invalid_reset_link"})

    def test_expiry_boundary_is_controlled_without_sleep(self):
        start = datetime(2026, 1, 1)
        with patch.object(default_token_generator, "_now", return_value=start):
            capability = self.credentials()
        with patch.object(default_token_generator, "_now", return_value=start + timedelta(seconds=1800)):
            self.assertEqual(self.post("check", capability).status_code, 200)

    def test_native_password_policy_and_unchanged_password_return_only_allowlisted_codes(self):
        capability = self.credentials()
        for value, expected in [
            (self.old_password, "password_unchanged"),
            ("short", "password_too_short"),
            ("password", "password_too_common"),
            ("flow-admin", "password_too_similar"),
            ("847261590376", "password_entirely_numeric"),
        ]:
            response = self.post("confirm", {**capability, "newPassword": value, "confirmPassword": value})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["code"], "password_validation_failed")
            self.assertIn(expected, response.json()["fields"]["newPassword"])
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password(self.old_password))
        response = self.post(
            "confirm", {**capability, "newPassword": self.new_password, "confirmPassword": "different-synthetic"}
        )
        self.assertIn("password_mismatch", response.json()["fields"]["confirmPassword"])

    def test_unicode_password_whitespace_is_preserved_and_native_change_hook_is_called_once(self):
        value = "  " + self.new_password + " Ж　 "
        with patch.object(password_validation, "password_changed") as changed:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.post("confirm", {**self.credentials(), "newPassword": value, "confirmPassword": value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(changed.call_count, 1)
            self.assertTrue(changed.call_args.args[0] == value)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(value))
        self.assertFalse(self.user.check_password(value.strip()))

    def test_shared_check_confirm_bucket_cannot_be_bypassed_by_route_switching(self):
        capability = {"uid": "MQ", "token": "not-a-valid-token"}
        for index in range(20):
            action = "check" if index % 2 else "confirm"
            data = (
                capability
                if action == "check"
                else {**capability, "newPassword": self.new_password, "confirmPassword": self.new_password}
            )
            self.assertEqual(self.post(action, data).status_code, 400)
        self.assertEqual(self.post("check", capability).status_code, 429)

    def test_limiter_stores_only_hmac_keys_and_cleanup_is_bounded(self):
        self.post("request", {"email": self.user.email})
        rows = list(ResetRateBucket.objects.values())
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(len(row["key"]) == 64 and set(row["key"]) <= set("0123456789abcdef") for row in rows))
        self.assertFalse(self.user.email in repr(rows) or "127.0.0.1" in repr(rows))

    def test_default_disabled_and_console_or_smtp_settings_fail_before_account_lookup(self):
        settings_cases = [
            {"ADMIN_PASSWORD_RESET_ENABLED": False},
            {"MAILERS": {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}},
            {"MAILERS": {"default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"}}},
            {"ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN": "https://evil.invalid/path?next=other"},
        ]
        for values in settings_cases:
            with override_settings(**values), patch("admin_auth.password_reset.recipient") as lookup:
                self.assertEqual(self.post("request", {"email": self.user.email}).status_code, 503)
                lookup.assert_not_called()

    def test_empty_userinfo_and_invalid_ports_fail_before_account_lookup(self):
        invalid_origins = [
            "https://@example.test",
            "https://:@example.test",
            "http://127.0.0.1:0",
            "https://example.test:0",
            "https://example.test:65536",
            "https://example.test:-1",
        ]
        for origin in invalid_origins:
            with self.subTest(origin=origin):
                with override_settings(ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN=origin):
                    with patch("admin_auth.password_reset.recipient", return_value=None) as lookup:
                        response = self.post("request", {"email": self.user.email})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {"code": "reset_unavailable"})
                lookup.assert_not_called()

    def test_valid_origins_and_port_boundaries_remain_accepted(self):
        valid_origins = [
            "https://example.test",
            "https://example.test/",
            "https://example.test:1",
            "https://example.test:65535",
            "http://localhost:5173",
            "http://127.0.0.1:62944",
            "http://[::1]:62944",
        ]
        for origin in valid_origins:
            with self.subTest(origin=origin), override_settings(ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN=origin):
                self.assertEqual(frontend_origin(), origin.rstrip("/"))

    def test_target_delivery_failure_has_same_acknowledgment_and_no_sensitive_exception_logging(self):
        marker = "SYNTHETIC-sensitive-delivery-value"
        with patch("admin_auth.password_reset.send_mail", side_effect=RuntimeError(marker)):
            with self.assertLogs("admin_auth.password_reset", level="WARNING") as captured:
                response = self.post("request", {"email": self.user.email})
        self.assertEqual(response.status_code, 202)
        self.assertNotIn(marker, " ".join(captured.output))
        self.assertNotIn(self.user.email, " ".join(captured.output))

    def test_unexpected_capability_failure_is_sanitized_in_response_and_logs(self):
        capability = self.credentials()
        marker = "SYNTHETIC-sensitive-check-value"
        with patch.object(default_token_generator, "check_token", side_effect=RuntimeError(marker)):
            with self.assertLogs("admin_auth.password_reset", level="ERROR") as captured:
                response = self.post("check", capability)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"code": "reset_unavailable"})
        rendered = " ".join(captured.output)
        self.assertFalse(marker in rendered or capability["token"] in rendered or self.old_password in rendered)
