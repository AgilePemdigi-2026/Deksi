import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase


class AuthLiveHTTPTests(LiveServerTestCase):
    def test_real_http_login_csrf_rotation_session_and_logout_replay(self):
        password = "SYNTHETIC-live-http-fixture-679!"
        user = get_user_model().objects.create_user(username="http-admin", password=password, is_staff=True)
        jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))
        origin = "http://127.0.0.1:62942"

        def exchange(path, data=None, token=None):
            headers = {"Origin": origin}
            if token is not None:
                headers["X-CSRFToken"] = token
            if data is not None:
                headers["Content-Type"] = "application/json"
            request = Request(
                self.live_server_url + path, data=None if data is None else json.dumps(data).encode(), headers=headers
            )
            with opener.open(request, timeout=10) as response:
                self.assertIn("no-store", response.headers["Cache-Control"])
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
                self.assertEqual(response.headers["Access-Control-Allow-Credentials"], "true")
                return json.load(response)

        token = exchange("/api/auth/csrf/")["csrfToken"]
        login = exchange("/api/auth/login/", {"identifier": "http-admin", "password": password}, token)
        self.assertTrue(login["authenticated"])
        self.assertEqual(login["user"]["id"], user.pk)
        session_cookie = next(cookie for cookie in jar if cookie.name == "sessionid")
        self.assertTrue(session_cookie.has_nonstandard_attr("HttpOnly"))
        previous = session_cookie.value
        self.assertTrue(exchange("/api/auth/session/")["authenticated"])
        with self.assertRaises(HTTPError) as rejected:
            exchange("/api/auth/logout/", {}, token)
        self.assertEqual(rejected.exception.code, 403)
        rejected.exception.close()
        self.assertFalse(exchange("/api/auth/logout/", {}, login["csrfToken"])["authenticated"])
        self.assertFalse(exchange("/api/auth/session/")["authenticated"])
        replay = Request(self.live_server_url + "/api/auth/session/", headers={"Cookie": "sessionid=" + previous})
        with build_opener().open(replay, timeout=10) as response:
            self.assertFalse(json.load(response)["authenticated"])
