"""Provider contract unit tests: synthetic transport; no database or live LLM."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import httpx

from indicators.ai_narrative_policy import PROMPT_VERSION, NarrativeError
from indicators.ai_narrative_provider import generate


class NarrativeProviderTests(TestCase):
    def setUp(self):
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('Live network forbidden')))
        self.enterContext(patch('indicators.ai_narrative_provider.assert_outside_transaction'))
        self.config = SimpleNamespace(
            model='synthetic:1', base_url='http://127.0.0.1:11434/v1', api_key='', timeout=120,
        )
        self.package = {'facts': {'current': {}, 'comparison': None}}
        self.requests = []
        self.output = {
            'summary': 'Kegiatan ekonomi dibandingkan dengan periode tahunan sebelumnya.',
            'meaning': 'PDB menggambarkan kegiatan ekonomi, bukan pendapatan setiap keluarga.',
            'comparison': None,
            'limitations': 'Tanggal rilis belum tersedia dan penyebab perubahan tidak dapat disimpulkan.',
            'factRefs': ['facts.current'],
        }

    def transport(self, *, content=None, finish='stop'):
        def handle(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(200, json={'model': self.config.model, 'choices': [
                {'finish_reason': finish, 'message': {'role': 'assistant',
                    'content': json.dumps(self.output) if content is None else content}}]})
        return httpx.MockTransport(handle)

    def pilot_response(self, attempt):
        path = Path(__file__).parent / 'fixtures' / 'aorus_narrative_pilot_responses.json'
        response = json.loads(path.read_text(encoding='utf-8'))[attempt]
        self.config.model = response['model']
        return response

    def assert_invalid_output(self, content, *, finish='stop'):
        with self.assertRaises(NarrativeError) as error:
            generate(self.config, self.package, transport=self.transport(content=content, finish=finish))
        self.assertEqual(error.exception.code, 'invalid_output')
        self.assertEqual(len(self.requests), 1)

    def test_request_has_pinned_json_object_response_mode(self):
        result, model = generate(self.config, self.package, transport=self.transport())
        self.assertEqual(result, self.output)
        self.assertEqual(model, 'synthetic:1')
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].get('response_format'), {'type': 'json_object'})

    def test_request_has_bounded_4096_token_budget(self):
        generate(self.config, self.package, transport=self.transport())
        self.assertEqual(self.requests[0]['max_tokens'], 4096)
        self.assertEqual(len(self.requests), 1)

    def test_transmitted_prompt_explicitly_forbids_fences_and_numeric_period_copying(self):
        generate(self.config, self.package, transport=self.transport())
        prompt = self.requests[0]['messages'][0]['content']
        for instruction in ('tanpa pagar kode', 'tahun, tanggal', 'periode yang dipilih', 'Jangan mengeja angka'):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, prompt)

    def test_new_request_contract_has_a_new_prompt_identity(self):
        self.assertEqual(PROMPT_VERSION, 'pdb-plain-id.v2')

    def test_provider_failure_does_not_retry_or_fall_back_to_plain_text(self):
        def reject(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(400, json={'error': 'Synthetic JSON mode unsupported'})
        with self.assertRaises(NarrativeError) as error:
            generate(self.config, self.package, transport=httpx.MockTransport(reject))
        self.assertEqual(error.exception.code, 'provider_error')
        self.assertEqual(len(self.requests), 1)

    def test_original_truncated_operator_response_is_rejected(self):
        response = self.pilot_response('attempt1')
        self.assert_invalid_output(response['content'], finish=response['finishReason'])

    def test_original_completed_operator_response_is_not_silently_unwrapped_or_repaired(self):
        response = self.pilot_response('attempt2')
        self.assertEqual(hashlib.sha256(response['content'].encode()).hexdigest(), response['contentSha256'])
        self.assert_invalid_output(response['content'], finish=response['finishReason'])

    def test_diagnostic_unwrapped_copy_of_operator_response_still_fails_numeric_contract(self):
        response = self.pilot_response('attempt2')
        self.assertTrue(response['content'].startswith('```json\n'))
        self.assertTrue(response['content'].endswith('\n```'))
        diagnostic_only = response['content'][len('```json\n'):-len('\n```')]
        self.assertIn('2025', json.loads(diagnostic_only)['summary'])
        self.assert_invalid_output(diagnostic_only)

    def test_valid_looking_json_with_length_finish_is_still_rejected(self):
        self.assert_invalid_output(json.dumps(self.output), finish='length')

    def test_duplicate_json_keys_are_not_accepted_in_json_mode(self):
        duplicate = '{"summary":"Tidak boleh ditimpa",' + json.dumps(self.output)[1:]
        self.assert_invalid_output(duplicate)

    def test_non_ascii_numeric_characters_are_not_a_bypass(self):
        self.output['summary'] = 'Periode ٢٠٢٥ tidak boleh disalin.'
        self.assert_invalid_output(json.dumps(self.output))
