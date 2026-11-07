"""Harness unit checks only: simulated Windows port-file races, not product E2E."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

QA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(QA))
from browser import Chrome  # noqa: E402

SCRATCH = Path('C:/Users/Pongo/AppData/Local/hermes/cache/scratch')


class ChromeStartupTests(unittest.TestCase):
    def adapter(self, folder):
        chrome = object.__new__(Chrome)
        chrome.profile = Path(folder)
        (chrome.profile / 'DevToolsActivePort').write_bytes(b'unit fixture')
        chrome.debug_port = None
        chrome.process = SimpleNamespace(poll=lambda: None)
        chrome.call = MagicMock(return_value={})
        return chrome

    def test_locked_then_partial_file_retries_without_changing_deadline(self):
        with tempfile.TemporaryDirectory(prefix='deksi-bdd-startup-unit-', dir=SCRATCH) as folder:
            chrome = self.adapter(folder)
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps([
                {'type': 'page', 'webSocketDebuggerUrl': 'ws://127.0.0.1:12345/devtools/page/synthetic'}
            ]).encode()
            with patch.object(Path, 'read_text', side_effect=[PermissionError('SYNTHETIC Windows writer lock'), '', '12345\n/devtools/browser/synthetic\n']) as reader, \
                 patch('browser.time.sleep') as sleep, \
                 patch('browser.urlopen', return_value=response) as http, \
                 patch('browser.websocket.create_connection') as websocket:
                chrome.connect()
                self.assertEqual(reader.call_count, 3)
                self.assertEqual(chrome.debug_port, 12345)
                self.assertEqual(sleep.call_count, 2)
                http.assert_called_once_with('http://127.0.0.1:12345/json/list', timeout=5)
                websocket.assert_called_once()
                chrome.call.assert_any_call('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}]})

    def test_permanent_lock_still_times_out(self):
        with tempfile.TemporaryDirectory(prefix='deksi-bdd-startup-unit-', dir=SCRATCH) as folder:
            chrome = self.adapter(folder)
            with patch.object(Path, 'read_text', side_effect=PermissionError('SYNTHETIC permanent lock')), \
                 patch('browser.time.monotonic', side_effect=[0, 0, 16]), \
                 patch('browser.time.sleep'), \
                 patch('browser.urlopen') as http:
                with self.assertRaisesRegex(TimeoutError, 'did not provide a debug port'):
                    chrome.connect()
                self.assertIsNone(chrome.debug_port)
                http.assert_not_called()


class ChromeCallTests(unittest.TestCase):
    def adapter(self):
        chrome = object.__new__(Chrome)
        chrome._send = MagicMock(return_value=7)
        chrome.event = MagicMock()
        chrome.ws = MagicMock()
        chrome.ws.gettimeout.return_value = 15
        return chrome

    def test_unsolicited_events_do_not_extend_command_deadline(self):
        chrome = self.adapter()
        chrome.ws.recv.side_effect = [json.dumps({'method': 'Synthetic.event'}),
                                      json.dumps({'method': 'Synthetic.event'}),
                                      AssertionError('No overall deadline was enforced')]
        with patch('browser.time.monotonic', side_effect=[0, 1, 31]):
            with self.assertRaisesRegex(TimeoutError, 'CDP Runtime.evaluate'):
                chrome.call('Runtime.evaluate', {'expression': 'synthetic'})
        chrome.ws.settimeout.assert_called_with(15)

    def test_matching_command_response_returns_and_restores_timeout(self):
        chrome = self.adapter()
        chrome.ws.recv.return_value = json.dumps({'id': 7, 'result': {'synthetic': True}})
        with patch('browser.time.monotonic', side_effect=[0, 1]):
            self.assertEqual(chrome.call('Runtime.evaluate'), {'synthetic': True})
        chrome.ws.settimeout.assert_called_with(15)


if __name__ == '__main__':
    unittest.main(verbosity=2)
