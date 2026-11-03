import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import LiveServerTestCase


class ResetLiveHTTPTests(LiveServerTestCase):
    def test_email_memory_link_through_real_http_reset_and_login(self):
        old = "SYNTHETIC-live-original-password-247!"
        new = "SYNTHETIC-live-replacement-password-698!"
        get_user_model().objects.create_user(
            username="live-reset", email="live-reset@example.test", password=old, is_staff=True
        )
        old_jar, reset_jar = CookieJar(), CookieJar()
        old_browser = build_opener(HTTPCookieProcessor(old_jar))
        browser = build_opener(HTTPCookieProcessor(reset_jar))
        origin = "http://127.0.0.1:62944"

        def exchange(opener, path, data=None, csrf=None):
            headers = {"Origin": origin}
            if data is not None:
                headers["Content-Type"] = "application/json"
            if csrf:
                headers["X-CSRFToken"] = csrf
            request = Request(
                self.live_server_url + path, data=None if data is None else json.dumps(data).encode(), headers=headers
            )
            try:
                response = opener.open(request, timeout=15)
            except HTTPError as error:
                response = error
            try:
                self.assertIn("no-store", response.headers["Cache-Control"])
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
                self.assertEqual(response.headers["Access-Control-Allow-Credentials"], "true")
                return response.status, json.load(response)
            finally:
                response.close()

        old_csrf = exchange(old_browser, "/api/auth/csrf/")[1]["csrfToken"]
        status, logged_in = exchange(
            old_browser, "/api/auth/login/", {"identifier": "live-reset", "password": old}, old_csrf
        )
        self.assertEqual(status, 200)
        self.assertTrue(logged_in["authenticated"])
        previous_cookie = next(cookie.value for cookie in old_jar if cookie.name == "sessionid")
        assert isinstance(previous_cookie, str)
        csrf = exchange(browser, "/api/auth/csrf/")[1]["csrfToken"]
        self.assertEqual(
            exchange(browser, "/api/auth/password-reset/request/", {"email": "live-reset@example.test"}, csrf)[0], 202
        )
        self.assertEqual(len(mail.outbox), 1)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        parsed = urlsplit(link)
        self.assertEqual(parsed.netloc, "127.0.0.1:62944")
        self.assertFalse(parsed.query)
        fragment = parse_qs(parsed.fragment)
        capability = {key: fragment[key][0] for key in ("uid", "token")}
        for _ in range(2):
            self.assertEqual(
                exchange(browser, "/api/auth/password-reset/check/", capability, csrf), (200, {"valid": True})
            )
        confirm = {**capability, "newPassword": new, "confirmPassword": new}
        self.assertEqual(
            exchange(browser, "/api/auth/password-reset/confirm/", confirm, csrf),
            (200, {"code": "reset_complete", "authenticated": False}),
        )
        self.assertFalse(exchange(browser, "/api/auth/session/")[1]["authenticated"])
        self.assertFalse(exchange(old_browser, "/api/auth/session/")[1]["authenticated"])
        replay = Request(
            self.live_server_url + "/api/auth/session/", headers={"Cookie": "sessionid=" + previous_cookie}
        )
        with build_opener().open(replay, timeout=15) as response:
            self.assertFalse(json.load(response)["authenticated"])
        self.assertEqual(exchange(browser, "/api/auth/password-reset/confirm/", confirm, csrf)[0], 400)
        self.assertEqual(
            exchange(browser, "/api/auth/login/", {"identifier": "live-reset", "password": old}, csrf)[0], 401
        )
        status, login = exchange(browser, "/api/auth/login/", {"identifier": "live-reset", "password": new}, csrf)
        self.assertEqual(status, 200)
        self.assertTrue(login["authenticated"])
