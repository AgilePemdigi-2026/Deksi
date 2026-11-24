from unittest.mock import Mock, patch

import httpx
from django.test import SimpleTestCase, override_settings

from indicators import bps


class BpsTransportSafetyTests(SimpleTestCase):
    @override_settings(BPS_API_KEY="synthetic", BPS_API_BASE_URL="https://example.test/v1")
    def test_untrusted_base_is_rejected_before_request(self):
        with patch("indicators.bps.httpx.get", side_effect=AssertionError("unexpected outbound request")) as get:
            with self.assertRaises(bps.BpsError):
                bps._request("/synthetic")
        get.assert_not_called()

    @override_settings(BPS_API_KEY="synthetic", BPS_API_BASE_URL="https://webapi.bps.go.id/v1")
    def test_redirect_is_rejected_without_following_it(self):
        response = Mock(status_code=302)
        with patch("indicators.bps.httpx.get", return_value=response) as get:
            with self.assertRaises(bps.BpsError):
                bps._request("/synthetic")
        self.assertFalse(get.call_args.kwargs["follow_redirects"])
        response.json.assert_not_called()

    @override_settings(BPS_API_KEY="synthetic", BPS_API_BASE_URL="https://webapi.bps.go.id/v1")
    def test_provider_status_text_is_not_exposed(self):
        response = Mock(status_code=200)
        response.json.return_value = {"status": "private-synthetic-data"}
        with patch("indicators.bps.httpx.get", return_value=response):
            with self.assertRaises(bps.BpsError) as failure:
                bps._request("/synthetic")
        self.assertNotIn("private-synthetic-data", str(failure.exception))

    @override_settings(BPS_API_KEY="synthetic-log-secret", BPS_API_BASE_URL="https://webapi.bps.go.id/v1")
    def test_httpx_info_log_does_not_expose_api_key(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "OK"}))
        with httpx.Client(transport=transport) as client:
            with patch("indicators.bps.httpx.get", side_effect=client.get):
                with self.assertLogs("httpx", level="INFO") as captured:
                    bps._request("/synthetic")
        self.assertNotIn("synthetic-log-secret", " ".join(captured.output))
