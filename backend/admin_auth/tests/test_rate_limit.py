from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class RateLimitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "SYNTHETIC-rate-test-only-583!"
        cls.admin = get_user_model().objects.create_user(
            username="admin-rate", email="admin-rate@example.test", password=cls.password, is_staff=True
        )

    def attempt(self, identifier="admin-rate", password="SYNTHETIC-wrong-password", ip="192.0.2.10", **extra):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        return client.post(
            "/api/auth/login/",
            {"identifier": identifier, "password": password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            REMOTE_ADDR=ip,
            **extra,
        )

    def test_fifth_failure_locks_out_even_correct_password(self):
        for _unused in range(4):
            self.assertEqual(self.attempt().status_code, 401)
        response = self.attempt()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "rate_limited")
        self.assertEqual(self.attempt(password=self.password).status_code, 429)

    def test_username_email_aliases_share_limit_across_ips(self):
        for index in range(4):
            identifier = "admin-rate" if index % 2 else "ADMIN-RATE@EXAMPLE.TEST"
            self.assertEqual(self.attempt(identifier, ip=f"192.0.2.{index + 1}").status_code, 401)
        self.assertEqual(self.attempt("admin-rate@example.test", ip="192.0.2.99").status_code, 429)

    def test_ip_limit_cannot_be_bypassed_by_unknown_names_user_agents_or_forwarded_headers(self):
        for index in range(4):
            response = self.attempt(
                f"unknown-{index}", HTTP_USER_AGENT=f"fixture-{index}", HTTP_X_FORWARDED_FOR=f"192.0.2.{index + 1}"
            )
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.attempt("another-unknown", HTTP_X_FORWARDED_FOR="192.0.2.99").status_code, 429)

    def test_lockout_attempt_does_not_extend_cooloff_and_expired_counter_recovers(self):
        from datetime import timedelta

        from axes.models import AccessAttempt
        from django.utils import timezone

        for _unused in range(5):
            self.attempt()
        before = list(AccessAttempt.objects.values_list("attempt_time", flat=True))
        self.assertEqual(self.attempt(password=self.password).status_code, 429)
        self.assertEqual(list(AccessAttempt.objects.values_list("attempt_time", flat=True)), before)
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.attempt(password=self.password).status_code, 200)

    def test_native_admin_and_json_api_share_failure_limit(self):
        for _unused in range(4):
            self.attempt()
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.post(
            "/admin/login/",
            {"username": "admin-rate", "password": "SYNTHETIC-wrong"},
            HTTP_X_CSRFTOKEN=token,
            REMOTE_ADDR="192.0.2.10",
        )
        self.assertEqual(response.status_code, 429)

    def test_native_admin_login_still_authenticates_staff(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.post(
            "/admin/login/", {"username": "admin-rate", "password": self.password}, HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(client.get("/api/auth/session/").json()["authenticated"])

    def test_attempt_storage_and_logs_do_not_contain_password_or_raw_identifier(self):
        from axes.models import AccessAttempt, AccessFailureLog, AccessLog

        wrong_password = "SYNTHETIC-private-wrong-password"
        with self.assertLogs("axes", level="WARNING") as logged:
            self.attempt(password=wrong_password)
        row = AccessAttempt.objects.get()
        self.assertRegex(row.username, r"^[0-9a-f]{64}$")
        stored = repr([row.username, row.get_data, row.post_data, logged.output])
        self.assertFalse(wrong_password in stored)
        self.assertFalse(self.admin.email in stored)
        self.assertFalse(self.admin.username in stored)
        self.assertEqual(AccessFailureLog.objects.count(), 0)
        self.assertEqual(AccessLog.objects.count(), 0)

    def test_native_admin_session_has_same_absolute_eight_hour_expiry(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.post(
            "/admin/login/", {"username": "admin-rate", "password": self.password}, HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 302)
        self.assertLessEqual(client.session.get_expiry_age(), 8 * 60 * 60)
        self.assertIsInstance(client.session.get("_session_expiry"), str)
