import unittest
from unittest.mock import patch

import httpx


class OfficialHTTPTests(unittest.TestCase):
    def test_valid_official_response_and_unsafe_redirect(self):
        try:
            from indicators.online_http import AcquisitionError, OfficialHTTP
        except ImportError:
            self.fail('Bounded official-source HTTP client has not been implemented')
        transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b'official'))
        with httpx.Client(transport=transport) as client:
            with OfficialHTTP(client=client, pause=0) as official:
                self.assertEqual(official.get_bytes('https://data.bkpm.go.id/dataset'), b'official')
        transport = httpx.MockTransport(lambda request: httpx.Response(302,
            headers={'location': 'http://127.0.0.1/private'}))
        with httpx.Client(transport=transport) as client:
            with OfficialHTTP(client=client, pause=0) as official:
                with self.assertRaises(AcquisitionError):
                    official.get_bytes('https://data.bkpm.go.id/dataset')

    def test_unsafe_urls_fail_before_transport(self):
        from indicators.online_http import AcquisitionError, OfficialHTTP
        transport = httpx.MockTransport(lambda request: self.fail('Unsafe URL reached transport'))
        with httpx.Client(transport=transport) as client, OfficialHTTP(client=client, pause=0) as official:
            for url in ['https://evil.test/', 'https://data.bkpm.go.id.evil.test/',
                        'https://user@data.bkpm.go.id/', 'http://data.bkpm.go.id/',
                        'https://data.bkpm.go.id:444/', 'https://127.0.0.1/',
                        'https://data.bkpm.go.id/\\bad', 'https://data.bkpm.go.id/#fragment']:
                with self.subTest(url=url), self.assertRaises(AcquisitionError):
                    official.get_bytes(url)
            self.assertEqual(official.requests, 0)

    def test_size_request_deadline_limits_and_safe_errors(self):
        from indicators.online_http import AcquisitionError, OfficialHTTP
        transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b'12345'))
        with httpx.Client(transport=transport) as client:
            with OfficialHTTP(client=client, pause=0, max_bytes=4) as official:
                with self.assertRaises(AcquisitionError):
                    official.get_bytes('https://data.bkpm.go.id/dataset')
            with OfficialHTTP(client=client, pause=0, max_requests=0) as official:
                with self.assertRaises(AcquisitionError):
                    official.get_bytes('https://data.bkpm.go.id/dataset')
            with OfficialHTTP(client=client, pause=0, deadline_seconds=-1) as official:
                with self.assertRaises(AcquisitionError):
                    official.get_bytes('https://data.bkpm.go.id/dataset')
        with patch('httpx.Client.stream', side_effect=httpx.ConnectError('private-marker')):
            with OfficialHTTP(pause=0) as official, self.assertRaises(AcquisitionError) as caught:
                official.get_bytes('https://data.bkpm.go.id/dataset')
        self.assertNotIn('private-marker', str(caught.exception))

    def test_redirect_cannot_switch_official_institution(self):
        from indicators.online_http import AcquisitionError, OfficialHTTP
        transport = httpx.MockTransport(lambda request: httpx.Response(302,
            headers={'location': 'https://www.bi.go.id/'}))
        with httpx.Client(transport=transport) as client, OfficialHTTP(client=client, pause=0) as official:
            with self.assertRaises(AcquisitionError):
                official.get_bytes('https://data.bkpm.go.id/dataset')
