"""QA contract checks, separate from executed application BDD results."""
import ast
import hashlib
import json
from pathlib import Path
import re
import unittest

from behave.parser import parse_file

QA = Path(__file__).resolve().parents[1]


class SuiteContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((QA / 'as-built-manifest.json').read_text(encoding='utf-8'))

    def test_catalogue_has_exactly_72_unique_executable_ids(self):
        ids = []
        files = sorted((QA / 'features/as-built').glob('*.feature'))
        self.assertEqual(len(files), 9)
        for path in files:
            feature = parse_file(str(path))
            self.assertIn('as_built', feature.tags)
            self.assertNotIn('not_run', feature.tags)
            ids.extend(scenario.name.split(' - ')[0] for scenario in feature.scenarios)
        self.assertEqual(len(ids), 72)
        self.assertEqual(len(set(ids)), 72)
        self.assertEqual(set(ids), set(self.manifest['expected_ids']))
        self.assertEqual(len(self.manifest['replacements']), 3)
        for change in self.manifest['replacements']:
            self.assertNotIn(change['baseline'], ids)
            self.assertIn(change['as_built'], ids)

    def test_baseline_and_pinned_product_sources_remain_unchanged(self):
        for relative, digest in self.manifest['baseline_feature_hashes'].items():
            self.assertEqual(hashlib.sha256((QA / 'features' / relative).read_bytes()).hexdigest(), digest)
        for relative, digest in self.manifest['product_source_hashes'].items():
            self.assertEqual(hashlib.sha256((QA.parent / relative).read_bytes()).hexdigest(), digest)
        for relative, digest in self.manifest['feature_hashes'].items():
            self.assertEqual(hashlib.sha256((QA / relative).read_bytes()).hexdigest(), digest)

    def test_actual_runner_filters_keep_both_catalogues_separate(self):
        tree = ast.parse((QA / 'run_bdd.py').read_text(encoding='utf-8'))
        filters = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'command':
                values = ast.literal_eval(node.value)
                if values[0] in ('--include', '--exclude'):
                    filters[values[0]] = re.compile(values[1])
        self.assertEqual(set(filters), {'--include', '--exclude'})
        for separator in ['/', '\\']:
            original = separator.join(['E:', 'qa', 'features', 'f06_detail.feature'])
            actual = separator.join(['E:', 'qa', 'features', 'as-built', 'f06_detail.feature'])
            regression = separator.join(['E:', 'qa', 'features', 'regression_empty_year.feature'])
            self.assertIsNone(filters['--include'].search(original))
            self.assertIsNotNone(filters['--include'].search(actual))
            self.assertIsNotNone(filters['--include'].search(regression))
            self.assertIsNone(filters['--exclude'].search(original))
            self.assertIsNotNone(filters['--exclude'].search(actual))


if __name__ == '__main__':
    unittest.main(verbosity=2)
