"""Kontrak Gherkin + Behat cheatsheet untuk F09/F10/F11.

Jalan tanpa server Django: hanya parse teks tiga file fitur dan
pastikan struktur Gherkin + cheatsheet + cakupan endpoint benar.

Run:
    python -m pytest qa/tests/test_f09_f11_cheatsheet.py -v
atau:
    python -m unittest qa.tests.test_f09_f11_cheatsheet -v
"""
import re
import unittest
from pathlib import Path

QA = Path(__file__).resolve().parents[1]
FEATURES = {
    "f09": QA / "features" / "f09_Daftar.Sumber.Data",
    "f10": QA / "features" / "f10_Tambah.Sumber.Data",
    "f11": QA / "features" / "f11_Edit.Sumber.Data",
}
EXPECTED_MIN_SCENARIOS = {"f09": 6, "f10": 7, "f11": 7}
EXPECTED_ENDPOINTS = {
    "f09": ["/api/sources/", "/api/sources/<id>/", "/api/sources/<id>/indicators/"],
    "f10": ["/api/admin/sources/create/"],
    "f11": [
        "/api/admin/sources/<id>/update/",
        "/api/admin/sources/BPS_TEST/revisions/",
    ],
}
CHEATSHEET_MARKERS = [
    "BEHAT CHEATSHEET",
    "FeatureContext",
    "behat.yml",
    "vendor/bin/behat",
]


def _read(key):
    path = FEATURES[key]
    assert path.is_file(), f"file hilang: {path}"
    text = path.read_text(encoding="utf-8")
    assert text.strip(), f"file kosong: {path}"
    return text


def _scenarios(text):
    return re.findall(r"(?m)^\s*Scenario(?: Outline)?:\s*(.+)$", text)


class F09F11CheatsheetTests(unittest.TestCase):
    def test_files_exist_and_not_empty(self):
        for key, path in FEATURES.items():
            with self.subTest(feature=key):
                self.assertTrue(path.is_file(), f"hilang: {path}")
                self.assertGreater(path.stat().st_size, 500, f"terlalu kecil: {path}")

    def test_no_conflict_markers(self):
        for key in FEATURES:
            with self.subTest(feature=key):
                text = _read(key)
                for marker in ("<<<<<<<", ">>>>>>>",):
                    self.assertNotIn(marker, text)

    def test_header_spec_and_cheatsheet(self):
        for key in FEATURES:
            with self.subTest(feature=key):
                text = _read(key)
                head = "\n".join(text.splitlines()[:45])
                self.assertIn("SPECIFICATION ONLY", head)
                for marker in CHEATSHEET_MARKERS:
                    self.assertIn(marker, head, f"cheatsheet kurang '{marker}' di {key}")

    def test_feature_and_scenario_counts(self):
        for key in FEATURES:
            with self.subTest(feature=key):
                text = _read(key)
                self.assertRegex(text, r"(?m)^Feature: F\d\d? ")
                scenarios = _scenarios(text)
                self.assertGreaterEqual(
                    len(scenarios), EXPECTED_MIN_SCENARIOS[key],
                    f"{key} hanya {len(scenarios)} skenario",
                )

    def test_each_scenario_has_given_when_then(self):
        blocks = re.compile(
            r"(?ms)^\s*Scenario(?: Outline)?:.*?(?=^\s*Scenario(?: Outline)?:|\Z)"
        )
        for key in FEATURES:
            with self.subTest(feature=key):
                text = _read(key)
                found = 0
                for m in blocks.finditer(text):
                    body = m.group(0)
                    if "Examples:" in body and "Scenario Outline" not in body:
                        continue  # blok Examples, bukan skenario
                    found += 1
                    for kw in ("Given", "When", "Then"):
                        self.assertRegex(body, rf"(?m)^\s*{kw}\b", f"{kw} hilang di {key}: {body[:60]!r}")
                self.assertGreaterEqual(found, EXPECTED_MIN_SCENARIOS[key])

    def test_scenario_ids_unique_per_feature(self):
        for key in FEATURES:
            with self.subTest(feature=key):
                text = _read(key)
                headers = re.findall(r"(?m)^\s*Scenario(?: Outline)?:\s*(BDD-F\d\d-\d\d)", text)
                self.assertGreaterEqual(len(headers), EXPECTED_MIN_SCENARIOS[key])
                self.assertEqual(len(headers), len(set(headers)), f"ID ganda di {key}: {headers}")

    def test_endpoint_coverage(self):
        for key, endpoints in EXPECTED_ENDPOINTS.items():
            with self.subTest(feature=key):
                text = _read(key)
                for ep in endpoints:
                    # <id> ditulis generik di file (BPS_TEST / <id-baru> dsb),
                    # jadi cek pola longgar untuk varian berparameter.
                    pattern = re.escape(ep).replace(r"\<id\>", r"(?:<id(?:-[^>]+)?>|[A-Z_]+)")
                    self.assertRegex(text, pattern, f"endpoint {ep} tak disebut di {key}")

    def test_outlines_have_examples(self):
        for key in FEATURES:
            with self.subTest(feature=key):
                text = _read(key)
                if "Scenario Outline" in text:
                    self.assertIn("Examples:", text)
                    self.assertRegex(text, r"(?m)^\s*\|.*\|\s*$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
