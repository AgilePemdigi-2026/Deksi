from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.views.debug import get_exception_reporter_filter


class CredentialReportingTests(TestCase):
    def test_unexpected_auth_errors_do_not_expose_password_in_exception_reports(self):
        password = "SYNTHETIC-report-only-password-415!"
        get_user_model().objects.create_user(username="report-admin", password=password, is_staff=True)
        targets = [
            "admin_auth.views.authenticate",
            "django.contrib.auth.models.User.check_password",
            "axes.backends.AxesProxyHandler.is_allowed",
        ]
        for target in targets:
            with self.subTest(target=target):
                client = Client(enforce_csrf_checks=True, raise_request_exception=False)
                token = client.get("/api/auth/csrf/").json()["csrfToken"]
                with patch(target, side_effect=RuntimeError("Synthetic internal authentication failure")):
                    response = client.post(
                        "/api/auth/login/",
                        {"identifier": "report-admin", "password": password},
                        content_type="application/json",
                        HTTP_X_CSRFTOKEN=token,
                    )
                self.assertEqual(response.status_code, 500)
                reporter_filter = get_exception_reporter_filter(response.wsgi_request)
                frame = response.exc_info[2]
                leaked = False
                while frame is not None:
                    variables = list(
                        reporter_filter.get_traceback_frame_variables(response.wsgi_request, frame.tb_frame)
                    )
                    leaked = leaked or password in repr(variables)
                    frame = frame.tb_next
                self.assertFalse(leaked, "Authentication password leaked through production traceback locals")

    def test_native_admin_exception_reports_also_hide_password(self):
        password = "SYNTHETIC-native-report-password-921!"
        get_user_model().objects.create_user(username="native-report", password=password, is_staff=True)
        client = Client(enforce_csrf_checks=True, raise_request_exception=False)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        with patch(
            "django.contrib.auth.models.User.check_password", side_effect=RuntimeError("Synthetic native auth failure")
        ):
            response = client.post(
                "/admin/login/", {"username": "native-report", "password": password}, HTTP_X_CSRFTOKEN=token
            )
        self.assertEqual(response.status_code, 500)
        reporter_filter = get_exception_reporter_filter(response.wsgi_request)
        frame = response.exc_info[2]
        leaked = False
        while frame is not None:
            leaked = leaked or password in repr(
                list(reporter_filter.get_traceback_frame_variables(response.wsgi_request, frame.tb_frame))
            )
            frame = frame.tb_next
        self.assertFalse(leaked, "Native Admin password leaked through production traceback locals")
