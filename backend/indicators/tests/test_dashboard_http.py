import json
from datetime import date
from http.cookiejar import CookieJar
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.utils import timezone

from indicators.feedback_model import Feedback
from indicators.models import Indicator, Observation, Source


class DashboardHttpTests(LiveServerTestCase):
    def setUp(self):
        reviewer = get_user_model().objects.create_user(username="synthetic-http-reviewer", is_staff=True)
        indicator = Indicator.objects.create(
            code="inflasi", name="SYNTHETIC HTTP Inflasi", category="Inflasi", unit="%"
        )
        source = Source.objects.create(
            source_id="TEST_HTTP",
            source_name="SYNTHETIC HTTP dataset",
            institution="SYNTHETIC institution",
            primary_url="https://example.test/http",
        )
        for year, value in ((2000, "0.123456"), (2001, "2.000002")):
            Observation.objects.create(
                indicator=indicator,
                source=source,
                observation_date=date(year, 1, 31),
                period_label=f"Januari {year}",
                frequency="monthly",
                data_type="yoy",
                value=value,
                unit="%",
                validation_status="published",
                reviewed_by=reviewer,
                reviewed_at=timezone.now(),
            )
        Observation.objects.create(
            indicator=indicator,
            source=source,
            observation_date=date(2000, 12, 31),
            period_label="PRIVATE SYNTHETIC",
            frequency="monthly",
            data_type="yoy",
            value="999",
            unit="%",
            validation_status="published",
        )
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def get(self, path):
        with self.opener.open(self.live_server_url + path, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            return json.loads(response.read())

    @patch("indicators.bps.test_connection", side_effect=AssertionError("Provider probe is outside this test"))
    def test_public_dashboard_history_trace_and_csrf_feedback_over_real_http(self, provider_probe):
        summary = self.get("/api/indicators/?code=inflasi")
        self.assertEqual(summary["indicators"][0]["value"], "2.000002")
        selected = self.get("/api/indicators/dashboard/?category=Inflasi&year=2000")["indicators"][0]
        self.assertEqual(selected["value"], "0.123456")
        self.assertEqual(selected["sourceId"], "TEST_HTTP")
        history = self.get("/api/indicators/inflasi/trend/")
        self.assertEqual([point["exactValue"] for point in history["points"]], ["0.123456", "2.000002"])
        point = history["points"][0]
        query = urlencode({key: point[key] for key in ("observationDate", "frequency", "dataType", "sourceId")})
        trace = self.get("/api/indicators/inflasi/source-trace/?" + query)
        self.assertEqual(trace["value"], selected["value"])
        self.assertEqual(trace["observationDate"], selected["observationDate"])
        self.assertEqual(trace["officialVerification"], "unassessed")
        self.assertFalse(trace["immutableSnapshot"])
        update = self.get("/api/system/update-status/")
        self.assertIn("lastSuccessful", update)
        body = json.dumps(
            {
                "category": "data_error",
                "description": "SYNTHETIC HTTP feedback only",
                "related_indicator_code": "inflasi",
                "related_period": selected["period"],
            }
        ).encode()
        request = Request(
            self.live_server_url + "/api/feedback/", data=body, headers={"Content-Type": "application/json"}
        )
        with self.assertRaises(HTTPError) as caught:
            self.opener.open(request, timeout=10)
        try:
            self.assertEqual(caught.exception.code, 403)
        finally:
            caught.exception.close()
        self.assertEqual(Feedback.objects.count(), 0)
        bootstrap = self.get("/api/feedback/categories/")
        request = Request(
            self.live_server_url + "/api/feedback/",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": bootstrap["csrfToken"],
                "Origin": self.live_server_url,
            },
        )
        with self.opener.open(request, timeout=10) as response:
            self.assertEqual(response.status, 201)
            stored_id = json.loads(response.read())["id"]
        persisted = Feedback.objects.get(pk=stored_id)
        self.assertEqual(persisted.status, "pending")
        self.assertEqual(persisted.related_period, selected["period"])
        self.assertEqual(persisted.description, "SYNTHETIC HTTP feedback only")
        provider_probe.assert_not_called()
