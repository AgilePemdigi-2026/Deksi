"""Explicit concurrency suite: requires file-backed, owned SQLite via test_settings_reset_concurrency."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.db import close_old_connections, connections
from django.test import Client, TransactionTestCase
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from admin_auth import password_reset
from admin_auth.models import ResetRateBucket
from admin_auth.reset_limits import consume


class ResetConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.assertNotIn("memory", connections["default"].settings_dict["NAME"])

    def test_two_real_request_threads_commit_exactly_once(self):
        user = get_user_model().objects.create_user(
            username="race-admin",
            email="race@example.test",
            password="SYNTHETIC-original-concurrent-password-819!",
            is_staff=True,
        )
        capability = {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
        barrier = Barrier(2)
        original = password_reset.commit_password

        def coordinated(instance, form):
            barrier.wait(timeout=15)
            return original(instance, form)

        def submit(index):
            close_old_connections()
            try:
                client = Client(enforce_csrf_checks=True)
                csrf = client.get("/api/auth/csrf/").json()["csrfToken"]
                value = f"SYNTHETIC-parallel-candidate-{index}-983!"
                response = client.post(
                    "/api/auth/password-reset/confirm/",
                    {**capability, "newPassword": value, "confirmPassword": value},
                    content_type="application/json",
                    HTTP_X_CSRFTOKEN=csrf,
                )
                return response.status_code, value
            finally:
                connections["default"].close()

        with (
            patch.object(password_reset, "commit_password", side_effect=coordinated),
            patch.object(password_validation, "password_changed") as changed,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, range(2)))
            self.assertEqual(sorted(status for status, _ in results), [200, 400])
            self.assertEqual(changed.call_count, 1)
        user.refresh_from_db()
        winner = next(value for status, value in results if status == 200)
        loser = next(value for status, value in results if status != 200)
        self.assertTrue(user.check_password(winner))
        self.assertFalse(user.check_password(loser))
        self.assertFalse(default_token_generator.check_token(user, capability["token"]))

    def test_eight_connections_share_atomic_identity_limit(self):
        barrier = Barrier(8)

        def take(_):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return consume("concurrency-test", "synthetic-identity", 3)
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(take, range(8)))
        self.assertEqual(sum(results), 3)
        self.assertEqual(ResetRateBucket.objects.count(), 1)
        self.assertEqual(ResetRateBucket.objects.get().count, 3)

    def test_fixed_window_resets_and_expired_cleanup_is_bounded(self):
        now = timezone.now()
        ResetRateBucket.objects.bulk_create(
            [
                ResetRateBucket(key=f"expired-{index}", count=1, expires_at=now - timedelta(seconds=1))
                for index in range(250)
            ]
        )
        with patch("admin_auth.reset_limits.timezone.now", return_value=now):
            self.assertTrue(consume("window-test", "synthetic-identity", 1))
            self.assertEqual(ResetRateBucket.objects.filter(key__startswith="expired-").count(), 50)
            self.assertFalse(consume("window-test", "synthetic-identity", 1))
        with patch("admin_auth.reset_limits.timezone.now", return_value=now + timedelta(seconds=901)):
            self.assertTrue(consume("window-test", "synthetic-identity", 1))
