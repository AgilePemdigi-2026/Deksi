from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class AuthAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixture_password = "SYNTHETIC-test-only-password-783!"
        cls.admin = get_user_model().objects.create_user(
            username="pengelola", email="pengelola@example.test", password=cls.fixture_password, is_staff=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def post_login(self, identifier="pengelola", password=None, **extra):
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        return self.client.post(
            "/api/auth/login/",
            {"identifier": identifier, "password": self.fixture_password if password is None else password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            **extra,
        )

    def test_csrf_bootstrap_returns_cookie_and_masked_token(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["csrfToken"])
        self.assertIn("csrftoken", self.client.cookies)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_active_admin_login_creates_real_eight_hour_session(self):
        response = self.post_login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"], {"id": self.admin.pk, "username": "pengelola", "isAdmin": True})
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(self.client.session["_auth_user_id"], str(self.admin.pk))
        self.assertLessEqual(self.client.session.get_expiry_age(), 8 * 60 * 60)
        self.assertGreater(self.client.session.get_expiry_age(), 8 * 60 * 60 - 10)
        self.assertTrue(response.cookies["sessionid"]["httponly"])
        self.assertEqual(response.cookies["sessionid"]["samesite"], "Lax")

    def test_email_alias_is_accepted_case_insensitively(self):
        self.assertEqual(self.post_login(" PENGELOLA@EXAMPLE.TEST ").status_code, 200)

    def test_nonstaff_cannot_create_admin_session(self):
        get_user_model().objects.create_user(username="member", password=self.fixture_password)
        response = self.post_login("member")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_ambiguous_email_does_not_choose_an_account(self):
        get_user_model().objects.create_user(
            username="other", email=self.admin.email, password=self.fixture_password, is_staff=True
        )
        self.assertEqual(self.post_login(self.admin.email).status_code, 401)

    def post_body(self, data, content_type="application/json"):
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.client.raise_request_exception = False
        return self.client.post("/api/auth/login/", data, content_type=content_type, HTTP_X_CSRFTOKEN=token)

    def test_malformed_json_returns_validation_error_not_server_error(self):
        response = self.post_body("{")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_request")

    def test_non_object_and_invalid_field_types_are_rejected(self):
        invalid = [[], None, {}, {"identifier": True, "password": "x"}, {"identifier": "pengelola", "password": []}]
        for payload in invalid:
            with self.subTest(payload_type=type(payload).__name__):
                self.assertEqual(self.post_body(payload).status_code, 400)

    def test_login_rejects_wrong_content_type(self):
        self.assertEqual(self.post_body("{}", "text/plain").status_code, 415)

    def test_login_input_size_is_bounded(self):
        for payload in [
            {"identifier": "x" * 255, "password": "x"},
            {"identifier": "pengelola", "password": "x" * 4097},
        ]:
            with self.subTest(field_length=max(len(value) for value in payload.values())):
                self.assertEqual(self.post_body(payload).status_code, 400)

    def test_login_does_not_trim_password(self):
        self.admin.set_password(" ")
        self.admin.save()
        self.assertEqual(self.post_login(password=" ").status_code, 200)

    def test_anonymous_session_is_explicitly_not_authenticated(self):
        response = self.client.get("/api/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})

    def test_session_check_reads_real_authenticated_user(self):
        self.post_login()
        response = self.client.get("/api/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], self.admin.pk)

    def test_revoked_staff_role_is_denied_on_next_request(self):
        self.post_login()
        self.admin.is_staff = False
        self.admin.save()
        self.assertEqual(self.client.get("/api/auth/session/").status_code, 403)

    def test_logout_invalidates_replayed_session(self):
        login = self.post_login()
        previous = self.client.cookies["sessionid"].value
        response = self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=login.json()["csrfToken"])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        replay = Client(enforce_csrf_checks=True)
        replay.cookies["sessionid"] = previous
        self.assertFalse(replay.get("/api/auth/session/").json()["authenticated"])
        self.assertEqual(replay.get("/admin/").status_code, 302)

    def test_csrf_rejection_uses_json_for_auth_api(self):
        self.client.get("/api/auth/csrf/")
        response = self.client.post("/api/auth/login/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(response.json()["code"], "csrf_failed")

    def test_native_csrf_failure_page_is_preserved(self):
        response = self.client.post("/admin/login/", {})
        self.assertEqual(response.status_code, 403)
        self.assertIn("text/html", response.headers["Content-Type"])

    def test_csrf_cookie_is_httponly(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertTrue(response.cookies["csrftoken"]["httponly"])

    def test_allowed_origin_receives_credentials_cors_header(self):
        response = self.client.options(
            "/api/auth/login/",
            HTTP_ORIGIN="http://127.0.0.1:62942",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-csrftoken",
        )
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:62942")
        self.assertEqual(response.headers.get("Access-Control-Allow-Credentials"), "true")

    def test_method_rejection_is_not_cacheable(self):
        response = self.client.get("/api/auth/login/")
        self.assertEqual(response.status_code, 405)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def test_unpaired_unicode_surrogates_are_invalid_input(self):
        for payload in [
            {"identifier": "bad\ud800", "password": "fixture"},
            {"identifier": "pengelola", "password": "bad\ud800"},
        ]:
            with self.subTest(field="identifier" if payload["identifier"] != "pengelola" else "password"):
                self.assertEqual(self.post_body(payload).status_code, 400)

    def test_unknown_wrong_inactive_and_nonstaff_errors_are_indistinguishable(self):
        model = get_user_model()
        model.objects.create_user(username="inactive", password=self.fixture_password, is_staff=True, is_active=False)
        model.objects.create_user(username="member", password=self.fixture_password)
        bodies = [
            self.post_login(name, "SYNTHETIC-wrong" if name == "pengelola" else None)
            for name in ["missing", "pengelola", "inactive", "member"]
        ]
        self.assertEqual([response.status_code for response in bodies], [401] * 4)
        self.assertTrue(all(response.json() == bodies[0].json() for response in bodies))

    def test_username_email_collision_is_rejected(self):
        get_user_model().objects.create_user(
            username="other", email="pengelola", password=self.fixture_password, is_staff=True
        )
        self.assertEqual(self.post_login("pengelola").status_code, 401)

    def test_inactive_account_loses_existing_session_access(self):
        self.post_login()
        self.admin.is_active = False
        self.admin.save()
        self.assertFalse(self.client.get("/api/auth/session/").json()["authenticated"])

    def test_expired_session_is_not_authenticated(self):
        from datetime import timedelta

        from django.utils import timezone

        self.post_login()
        session = self.client.session
        session.set_expiry(timezone.now() - timedelta(seconds=1))
        session.save()
        self.assertFalse(self.client.get("/api/auth/session/").json()["authenticated"])

    def test_reading_session_does_not_extend_absolute_expiry(self):
        self.post_login()
        expires = self.client.session.get_expiry_date()
        self.client.get("/api/auth/session/")
        self.assertEqual(self.client.session.get_expiry_date(), expires)

    def test_login_rotates_preexisting_anonymous_session(self):
        session = self.client.session
        session["fixture-marker"] = True
        session.save()
        previous = session.session_key
        self.client.cookies["sessionid"] = previous
        self.post_login()
        self.assertNotEqual(self.client.cookies["sessionid"].value, previous)
        replay = Client()
        replay.cookies["sessionid"] = previous
        self.assertFalse(replay.get("/api/auth/session/").json()["authenticated"])

    def test_old_csrf_token_cannot_logout_after_login_rotation(self):
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        login = self.client.post(
            "/api/auth/login/",
            {"identifier": "pengelola", "password": self.fixture_password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code, 403)
        self.assertEqual(
            self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=login.json()["csrfToken"]).status_code, 200
        )

    def test_anonymous_logout_is_idempotent_with_valid_csrf(self):
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        for _unused in range(2):
            self.assertEqual(self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_untrusted_origin_is_rejected_even_with_valid_csrf(self):
        response = self.post_login(HTTP_ORIGIN="https://untrusted.example.test")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "csrf_failed")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_deep_and_oversized_json_are_validation_errors(self):
        for body in ["[" * 1500 + "]" * 1500, " " * 17000]:
            self.assertEqual(self.post_body(body).status_code, 400)

    def test_anonymous_public_summary_remains_available(self):
        response = self.client.get("/api/indicators/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("indicators", response.json())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_blank_identifier_and_empty_password_are_validation_errors(self):
        for payload in [{"identifier": "   ", "password": "fixture"}, {"identifier": "pengelola", "password": ""}]:
            with self.subTest(field="identifier" if not payload["identifier"].strip() else "password"):
                self.assertEqual(self.post_body(payload).status_code, 400)

    def test_csrf_requires_matching_cookie_and_token(self):
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        fresh = Client(enforce_csrf_checks=True)
        payload = {"identifier": "pengelola", "password": self.fixture_password}
        self.assertEqual(
            fresh.post(
                "/api/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN="x" * 64
            ).status_code,
            403,
        )

    def test_public_trend_and_source_trace_remain_anonymous(self):
        from datetime import date
        from decimal import Decimal

        from indicators.models import Indicator, Observation, Source

        indicator = Indicator.objects.create(code="pdb", name="Synthetic auth test", category="fixture", unit="%")
        source = Source.objects.create(
            source_id="auth-test",
            source_name="Synthetic test source",
            institution="Fixture",
            primary_url="https://example.test",
        )
        Observation.objects.create(
            indicator=indicator,
            source=source,
            observation_date=date(2020, 3, 31),
            period_label="Q1 2020",
            frequency=Observation.Frequency.QUARTERLY,
            data_type=Observation.DataType.LEVEL,
            value=Decimal("1.25"),
            unit="%",
            validation_status=Observation.Status.PUBLISHED,
        )
        for route in [
            "/api/indicators/pdb/trend/",
            "/api/indicators/pdb/trend/?granularity=Tahunan",
            "/api/indicators/pdb/source-trace/",
        ]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
