"""Offline preview artifact reader checks, without databases, credentials or network."""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


class NarrativePreviewTests(unittest.TestCase):
    def setUp(self):
        self.saved = Path(__file__).parent / 'fixtures/gemini_engine_preview'
        self.snapshot = Path(__file__).resolve().parents[2] / 'docs/bps-economic-inputs/ui-readability-batch2-20261125/real-preview-engine-packet.json'

    def test_original_response_can_bind_exactly_to_archived_engine_snapshot(self):
        spec = importlib.util.find_spec('indicators.tests.engine_narrative_preview')
        self.assertIsNotNone(spec, 'Read-only narrative reader is not implemented')
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        snapshot, saved = self.snapshot, self.saved
        packet, payload, reviewed_at = load_preview_narrative(saved, snapshot)
        original = json.loads((saved / 'result.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['narrative'], original['narrative'])
        self.assertEqual(payload['period'], 'Q1 2025')
        self.assertIs(payload['humanApproval'], False)
        self.assertEqual(payload['metricsBinding']['pmtb_share']['resultDigest'], packet['metrics']['pmtb_share']['resultDigest'])
        self.assertEqual(reviewed_at, packet['metrics']['pmtb_share']['inputs']['pdb_nominal']['trace']['reviewedAt'])

    def copy_case(self):
        directory = tempfile.TemporaryDirectory(prefix='deksi-narrative-reader-test-', dir=os.environ['HERMES_TEST_SCRATCH'])
        self.addCleanup(directory.cleanup)
        base = Path(directory.name)
        for name in ('request.json', 'prepared.json', 'facts.json', 'result.json', 'response-original.bin'):
            shutil.copyfile(self.saved / name, base / name)
        snapshot = base / 'snapshot.json'
        shutil.copyfile(self.snapshot, snapshot)
        return base, snapshot

    def test_modified_original_response_rejected(self):
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        base, snapshot = self.copy_case()
        (base / 'response-original.bin').write_bytes(b'{}')
        with self.assertRaises(ValueError):
            load_preview_narrative(base, snapshot)

    def test_duplicate_json_key_rejected(self):
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        base, snapshot = self.copy_case()
        (base / 'result.json').write_text('{"model":"one","model":"two"}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate_preview_json_key'):
            load_preview_narrative(base, snapshot)

    def test_changed_snapshot_rejected(self):
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        base, snapshot = self.copy_case()
        packet = json.loads(snapshot.read_text())
        packet['metrics']['pmtb_share']['value'] = '29.00'
        snapshot.write_text(json.dumps(packet))
        with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
            load_preview_narrative(base, snapshot)

    def test_resealed_result_prose_still_must_match_original_response(self):
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        base, snapshot = self.copy_case()
        result = json.loads((base / 'result.json').read_text())
        result['narrative']['summary'] = 'Prosa yang diubah setelah diterima.'
        (base / 'result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'original_response_mismatch'):
            load_preview_narrative(base, snapshot)

    def test_false_is_not_interchangeable_with_zero_in_review_flags(self):
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        base, snapshot = self.copy_case()
        result = json.loads((base / 'result.json').read_text())
        result['humanApproval'] = 0
        (base / 'result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
            load_preview_narrative(base, snapshot)

    def test_oversized_artifact_rejected_before_parsing(self):
        from indicators.tests.engine_narrative_preview import load_preview_narrative
        base, snapshot = self.copy_case()
        (base / 'response-original.bin').write_bytes(b'x' * (128 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, 'artifact_too_large'):
            load_preview_narrative(base, snapshot)


if __name__ == '__main__':
    unittest.main()
