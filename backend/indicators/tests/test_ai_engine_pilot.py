"""Engine explanation pilot: public archived fixture, never a live provider in tests."""
import importlib
import importlib.util
import contextlib
import io
import json
import runpy
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import httpx


class EngineFactsTests(TestCase):
    def test_two_backend_ratios_become_sanitized_facts_without_becoming_growth_rates(self):
        spec = importlib.util.find_spec('indicators.ai_engine_pilot')
        self.assertIsNotNone(spec, 'Economic Engine facts adapter has not been implemented')
        api = importlib.import_module('indicators.ai_engine_pilot')
        packet = json.loads((Path(__file__).parent / 'fixtures/engine_gdp_preview.json').read_text())
        before = json.dumps(packet, sort_keys=True)
        facts = api.build_engine_package(packet, workflow_simulated=True)
        self.assertEqual(facts['metrics']['pmtb_share']['value'], '28.03')
        self.assertEqual(facts['metrics']['household_consumption_share']['value'], '54.56')
        self.assertEqual(facts['period'], 'Q1 2025')
        self.assertTrue(facts['workflowStateSimulated'])
        self.assertEqual(facts['revisionStatus'], 'unknown')
        self.assertEqual(facts['officialVerification'], 'unassessed')
        self.assertNotIn('trace', json.dumps(facts))
        self.assertNotIn('https://', json.dumps(facts))
        self.assertNotIn('reviewedAt', json.dumps(facts))
        self.assertEqual(json.dumps(packet, sort_keys=True), before)
        self.assertEqual(len(facts['inputDigest']), 64)

    def test_unqualified_changed_or_mismatched_snapshots_fail_closed(self):
        from indicators.ai_engine_pilot import build_engine_package
        from indicators.ai_narrative_policy import digest
        mutations = [
            lambda p: p['metrics']['pmtb_share'].update(value='29.00'),
            lambda p: p['metrics']['pmtb_share'].update(available=False),
            lambda p: p['metrics']['pmtb_share'].update(priceBasis=None),
            lambda p: p['metrics']['pmtb_share'].update(period='Q2 2025'),
            lambda p: p['metrics']['pmtb_share'].update(revisionStatus='final'),
            lambda p: p['metrics']['pmtb_share']['inputs']['pmtb_nominal'].update(sourceId='OTHER'),
            lambda p: p['metrics']['pmtb_share']['inputs']['pmtb_nominal'].update(bindingStatus='mismatch'),
            lambda p: p['metrics']['pmtb_share']['inputs']['pmtb_nominal']['trace'].update(validationStatus='pending'),
            lambda p: p['metrics']['pmtb_share']['inputs']['pmtb_nominal']['trace'].update(value='99'),
            lambda p: p['metrics']['pmtb_share'].update(inputs={}),
        ]
        for index, mutate in enumerate(mutations):
            packet = json.loads((Path(__file__).parent / 'fixtures/engine_gdp_preview.json').read_text())
            mutate(packet)
            # Preserve the intentionally broken checksum in the first control only.
            if index:
                metric = packet['metrics']['pmtb_share']
                metric['resultDigest'] = digest({key: value for key, value in metric.items() if key != 'resultDigest'})
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, '^invalid_engine_packet$'):
                build_engine_package(packet, workflow_simulated=True)

    def test_missing_and_forged_workflow_context_are_not_silently_accepted(self):
        from indicators.ai_engine_pilot import build_engine_package
        for packet in [{}, {'metrics': {}}, None, []]:
            with self.subTest(packet=packet), self.assertRaisesRegex(ValueError, '^invalid_engine_packet$'):
                build_engine_package(packet, workflow_simulated=True)


class EngineProviderTests(TestCase):
    def test_gemini_request_uses_engine_prompt_and_preserves_the_raw_response(self):
        api = importlib.import_module('indicators.ai_engine_pilot')
        generate = getattr(api, 'generate_engine_narrative', None)
        self.assertTrue(callable(generate), 'Gemini engine adapter has not been implemented')
        packet = json.loads((Path(__file__).parent / 'fixtures/engine_gdp_preview.json').read_text())
        package = api.build_engine_package(packet, workflow_simulated=True)
        output = {'summary': 'Paket ini membandingkan bagian kegiatan ekonomi dalam total PDB.',
            'meaning': 'PMTB mencakup pembentukan modal tetap bruto. Konsumsi rumah tangga adalah komponen yang berbeda.',
            'comparison': None, 'limitations': 'Status revisi dan tanggal rilis belum diketahui. Ini simulasi alur review.',
            'factRefs': ['metrics.pmtb_share', 'metrics.household_consumption_share']}
        config = SimpleNamespace(model='gemini-test-only', base_url='https://generativelanguage.googleapis.com/v1beta/openai',
            api_key='synthetic-test-key', timeout=120)
        requests, raw = [], []
        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={'model': config.model, 'choices': [
                {'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(output)}}]})
        with patch('socket.socket.connect', side_effect=AssertionError('Offline only')):
            result, reported = generate(config, package, transport=httpx.MockTransport(handle), response_sink=raw.append)
        self.assertEqual(result, output)
        self.assertEqual(reported, config.model)
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions')
        self.assertEqual(requests[0].headers['Authorization'], 'Bearer synthetic-test-key')
        body = json.loads(requests[0].content)
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertEqual(body['max_tokens'], 4096)
        self.assertIn('bukan pertumbuhan', body['messages'][0]['content'])
        self.assertIn('tersedia. Jangan menambahkan', body['messages'][0]['content'])
        self.assertNotIn('YoY membandingkan', body['messages'][0]['content'])
        self.assertEqual(json.loads(body['messages'][1]['content']), package)
        self.assertEqual(json.loads(raw[0])['model'], config.model)

    def test_old_yoy_references_numeric_prose_and_fake_comparisons_are_refused(self):
        from indicators.ai_engine_pilot import validate_engine_narrative
        from indicators.ai_narrative_policy import NarrativeError
        valid = {'summary': 'Porsi komponen terhadap total PDB.', 'meaning': 'Bukan pertumbuhan.',
            'comparison': None, 'limitations': 'Status revisi belum diketahui.',
            'factRefs': ['metrics.pmtb_share', 'metrics.household_consumption_share']}
        for change in [{'factRefs': ['facts.current']}, {'summary': 'Porsi 28,03 persen'},
                       {'comparison': 'Meningkat dari sebelumnya'}, {'factRefs': [[], 'metrics.pmtb_share']},
                       {'meaning': '<b>Modal</b>'}, {'limitations': 'https://example.test'}]:
            with self.subTest(change=change), self.assertRaises(NarrativeError):
                validate_engine_narrative({**valid, **change}, {})

    def test_credential_and_model_validation_are_local_and_do_not_change_aorus(self):
        from indicators.ai_engine_pilot import gemini_config
        from indicators.ai_narrative_policy import NarrativeError
        for key, model in [('', 'gemini-test'), ('key\nleak', 'gemini-test'), ('key', 'aorus:model'), ('key', 'gemini-x/path')]:
            with self.subTest(model=model), self.assertRaises(NarrativeError):
                gemini_config(key, model)

    def test_unknown_fact_fields_are_refused_before_any_transport(self):
        from indicators.ai_engine_pilot import build_engine_package, gemini_config, generate_engine_narrative
        from indicators.ai_narrative_policy import digest
        packet = json.loads((Path(__file__).parent / 'fixtures/engine_gdp_preview.json').read_text())
        package = build_engine_package(packet, workflow_simulated=True)
        package['privateMetadata'] = 'must never reach a remote provider'
        package['inputDigest'] = digest({key: value for key, value in package.items() if key != 'inputDigest'})
        with self.assertRaisesRegex(ValueError, '^invalid_engine_package$'):
            generate_engine_narrative(gemini_config('test-key', 'gemini-test'), package,
                transport=httpx.MockTransport(lambda request: self.fail('Invalid package was transmitted')))


class EngineCliTests(TestCase):
    def test_dry_run_never_calls_provider_and_leaves_a_bound_readable_request(self):
        script = Path(__file__).parents[2] / 'tools/run_engine_gemini_pilot.py'
        self.assertTrue(script.is_file(), 'Local Gemini pilot command is missing')
        namespace = runpy.run_path(str(script), run_name='offline_cli_test')
        with tempfile.TemporaryDirectory(prefix='engine-cli-', dir=tempfile.gettempdir()) as folder:
            output = Path(folder) / 'prepared'
            fixture = Path(__file__).parent / 'fixtures/engine_gdp_preview.json'
            with patch.dict(namespace['main'].__globals__,
                    {'generate_engine_narrative': lambda *a, **k: self.fail('Dry-run must not call Gemini')}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = namespace['main'](['--snapshot', str(fixture), '--output-dir', str(output),
                        '--model', 'gemini-placeholder', '--workflow-simulated'])
            self.assertEqual(code, 0)
            receipt = json.loads((output / 'prepared.json').read_text())
            self.assertEqual(receipt['status'], 'prepared_no_inference')
            self.assertEqual(receipt['providerPosts'], 0)
            package = json.loads((output / 'facts.json').read_text())
            self.assertEqual(package['metrics']['pmtb_share']['value'], '28.03')
            self.assertFalse((output / 'dispatch-once.json').exists())

    def test_one_mocked_inference_is_saved_and_second_send_is_refused(self):
        from indicators.ai_engine_pilot import generate_engine_narrative
        namespace = runpy.run_path(str(Path(__file__).parents[2] / 'tools/run_engine_gemini_pilot.py'), run_name='qa_cli')
        requests = []
        narrative = {'summary': 'Komponen dalam total PDB.', 'meaning': 'Porsi bukan pertumbuhan.',
            'comparison': None, 'limitations': 'Revisi belum diketahui. Simulasi lokal.',
            'factRefs': ['metrics.pmtb_share', 'metrics.household_consumption_share']}
        def handle(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={'model': 'gemini-test', 'choices': [
                {'finish_reason': 'stop', 'message': {'content': json.dumps(narrative)}}]})
        def generate(config, package, **kwargs):
            return generate_engine_narrative(config, package, transport=httpx.MockTransport(handle), **kwargs)
        with tempfile.TemporaryDirectory(prefix='engine-send-', dir=tempfile.gettempdir()) as folder:
            output = Path(folder) / 'prepared'
            arguments = ['--snapshot', str(Path(__file__).parent / 'fixtures/engine_gdp_preview.json'),
                '--output-dir', str(output), '--model', 'gemini-test', '--workflow-simulated']
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(namespace['main'](arguments), 0)
                prepared = json.loads((output / 'prepared.json').read_text())
                send = arguments + ['--send-once', '--approve-request-sha256', prepared['requestSha256'], '--acknowledge-api-billing']
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'fake-test-key'}), patch.dict(namespace['main'].__globals__,
                        {'generate_engine_narrative': generate}):
                    self.assertEqual(namespace['main'](send), 0)
                    self.assertEqual(namespace['main'](send), 2)
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0], json.loads((output / 'request.json').read_text())['request'])
            result = json.loads((output / 'result.json').read_text())
            self.assertEqual(result['status'], 'valid_contract_human_review_pending')
            self.assertEqual(result['narrative'], narrative)
            self.assertFalse(result['humanApproval'])
            self.assertTrue((output / 'response-original.bin').is_file())

    def test_missing_digest_or_billing_ack_cannot_dispatch(self):
        namespace = runpy.run_path(str(Path(__file__).parents[2] / 'tools/run_engine_gemini_pilot.py'), run_name='qa_cli')
        with tempfile.TemporaryDirectory(prefix='engine-refuse-', dir=tempfile.gettempdir()) as folder:
            output = Path(folder) / 'prepared'
            arguments = ['--snapshot', str(Path(__file__).parent / 'fixtures/engine_gdp_preview.json'),
                '--output-dir', str(output), '--model', 'gemini-test', '--workflow-simulated']
            with contextlib.redirect_stdout(io.StringIO()), patch.dict(namespace['main'].__globals__,
                    {'generate_engine_narrative': lambda *a, **k: self.fail('Unapproved inference')}):
                self.assertEqual(namespace['main'](arguments), 0)
                self.assertEqual(namespace['main'](arguments + ['--send-once']), 2)
                self.assertEqual(namespace['main'](arguments + ['--send-once', '--approve-request-sha256', '0' * 64,
                    '--acknowledge-api-billing']), 2)
            self.assertFalse((output / 'dispatch-once.json').exists())
