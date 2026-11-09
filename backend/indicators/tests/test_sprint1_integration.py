"""Cross-feature regression against the real combined application stack."""

import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import LiveServerTestCase, SimpleTestCase, TestCase
from django.utils import timezone

from admin_auth.models import ResetRateBucket
from indicators.feedback_model import Feedback
from indicators.tests import test_dashboard_http


class CombinedStackTests(SimpleTestCase):
    def test_actual_auth_security_stack_and_public_apps_are_installed(self):
        for app in ("indicators", "admin_auth", "axes"):
            self.assertIn(app, settings.INSTALLED_APPS)
        for middleware in (
            "admin_auth.reporting.AuthReportingMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "axes.middleware.AxesMiddleware",
        ):
            self.assertIn(middleware, settings.MIDDLEWARE)
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS,
            ["axes.backends.AxesStandaloneBackend", "admin_auth.backends.AdminBackend"],
        )
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertTrue(settings.CORS_ALLOW_CREDENTIALS)
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(settings.MAILERS["default"]["BACKEND"], "django.core.mail.backends.locmem.EmailBackend")

    def test_complete_migration_graph_has_one_leaf_per_app(self):
        loader = MigrationLoader(None)
        self.assertEqual(loader.detect_conflicts(), {})
        for app in ("admin_auth", "axes", "indicators", "auth", "sessions"):
            self.assertEqual(len(loader.graph.leaf_nodes(app)), 1, app)


class CombinedDatabaseTests(TestCase):
    def test_auth_and_public_models_share_the_same_migrated_database(self):
        tables = connection.introspection.table_names()
        for table in (
            "feedback",
            "admin_auth_resetratebucket",
            "indicators_observationcandidate",
            "axes_accessattempt",
        ):
            self.assertIn(table, tables)
        bucket = ResetRateBucket.objects.create(key="synthetic-combined-bucket", count=1, expires_at=timezone.now())
        feedback = Feedback.objects.create(category="other", description="SYNTHETIC combined database check")
        self.assertEqual(ResetRateBucket.objects.get(pk=bucket.pk).count, 1)
        self.assertEqual(Feedback.objects.get(pk=feedback.pk).status, "pending")


class CombinedHTTPTests(LiveServerTestCase):
    def setUp(self):
        test_dashboard_http.DashboardHttpTests.setUp(self)
        self.password = "SYNTHETIC-combined-original-928!"
        self.admin_user = get_user_model().objects.create_user(
            username="combined-admin", email="combined-admin@example.test", password=self.password, is_staff=True
        )
        self.browser = build_opener(HTTPCookieProcessor(CookieJar()))
        self.origin = "http://127.0.0.1:62944"

    def exchange(self, path, data=None, csrf=None, browser=None):
        headers = {"Origin": self.origin}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if csrf:
            headers["X-CSRFToken"] = csrf
        request = Request(
            self.live_server_url + path,
            data=None if data is None else json.dumps(data).encode(),
            headers=headers,
        )
        try:
            response = (browser or self.browser).open(request, timeout=15)
        except HTTPError as error:
            response = error
        try:
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], self.origin)
            self.assertEqual(response.headers["Access-Control-Allow-Credentials"], "true")
            if "application/json" in response.headers.get("Content-Type", ""):
                body = json.load(response)
            else:
                body = response.read().decode()
            return response.status, body
        finally:
            response.close()

    def assert_public_dashboard(self):
        status, dashboard = self.exchange("/api/indicators/dashboard/?category=Inflasi&year=2000")
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["indicators"][0]["value"], "0.123456")
        self.assertNotIn("PRIVATE SYNTHETIC", json.dumps(dashboard))
        self.assertEqual(self.exchange("/api/indicators/?code=inflasi")[0], 200)
        self.assertEqual(self.exchange("/api/indicators/inflasi/trend/")[0], 200)
        self.assertEqual(self.exchange("/api/indicators/inflasi/source-trace/")[0], 200)
        self.assertEqual(self.exchange("/api/indicators/categories/")[0], 200)
        self.assertEqual(self.exchange("/api/system/update-status/")[0], 200)

    def test_login_feedback_reset_and_public_access_share_real_http_stack(self):
        self.assert_public_dashboard()
        self.assertFalse(self.exchange("/api/auth/session/")[1]["authenticated"])
        feedback = {"category": "other", "description": "SYNTHETIC combined feedback before login"}
        self.assertEqual(self.exchange("/api/feedback/", feedback)[0], 403)
        before = self.exchange("/api/feedback/categories/")[1]["csrfToken"]
        self.assertEqual(self.exchange("/api/feedback/", feedback, before)[0], 201)
        status, login = self.exchange(
            "/api/auth/login/", {"identifier": "combined-admin", "password": self.password}, before
        )
        self.assertEqual(status, 200)
        self.assertTrue(login["authenticated"])
        self.assert_public_dashboard()
        self.assertEqual(self.exchange("/api/feedback/", feedback, before)[0], 403)
        self.assertEqual(self.exchange("/api/feedback/", feedback, login["csrfToken"])[0], 201)
        reset_browser = build_opener(HTTPCookieProcessor(CookieJar()))
        csrf = self.exchange("/api/auth/csrf/", browser=reset_browser)[1]["csrfToken"]
        self.assertEqual(
            self.exchange("/api/auth/password-reset/request/", {"email": self.admin_user.email}, csrf, reset_browser)[
                0
            ],
            202,
        )
        self.assertEqual(len(mail.outbox), 1)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        fragment = parse_qs(urlsplit(link).fragment)
        capability = {key: fragment[key][0] for key in ("uid", "token")}
        self.assertEqual(self.exchange("/api/auth/password-reset/check/", capability, csrf, reset_browser)[0], 200)
        new_password = "SYNTHETIC-combined-replacement-735!"
        confirm = {**capability, "newPassword": new_password, "confirmPassword": new_password}
        self.assertEqual(self.exchange("/api/auth/password-reset/confirm/", confirm, csrf, reset_browser)[0], 200)
        self.assertFalse(self.exchange("/api/auth/session/")[1]["authenticated"])
        self.assert_public_dashboard()
        self.assertEqual(self.exchange("/api/auth/password-reset/confirm/", confirm, csrf, reset_browser)[0], 400)
        current = self.exchange("/api/auth/csrf/")[1]["csrfToken"]
        self.assertEqual(
            self.exchange("/api/auth/login/", {"identifier": "combined-admin", "password": self.password}, current)[0],
            401,
        )
        status, login = self.exchange(
            "/api/auth/login/", {"identifier": "combined-admin", "password": new_password}, current
        )
        self.assertEqual(status, 200)
        self.assertTrue(login["authenticated"])
        self.assertEqual(self.exchange("/api/auth/logout/", {}, login["csrfToken"])[0], 200)
        self.assertFalse(self.exchange("/api/auth/session/")[1]["authenticated"])
        self.assert_public_dashboard()
        self.assertEqual(Feedback.objects.count(), 2)
        self.assertEqual(set(Feedback.objects.values_list("status", flat=True)), {"pending"})
