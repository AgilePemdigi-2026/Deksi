import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from indicators.models import RawFile
from indicators.storage import save_raw, verified_raw_bytes
from indicators.tests.support import IndicatorCase


class RawStorageTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"], prefix="deksi-f7-storage-")
        self.addCleanup(temporary.cleanup)
        # Even the pre-fix traversal reproduction must remain inside this owned temporary directory.
        self.root = Path(temporary.name) / "guard-one" / "guard-two" / "raw"
        self.root.mkdir(parents=True)
        override = override_settings(DEKSI_RAW_DIR=self.root, DEKSI_MAX_RAW_BYTES=100)
        override.enable()
        self.addCleanup(override.disable)

    def test_same_original_filename_cannot_overwrite_previous_raw(self):
        first, created = save_raw(self.source, b"FIRST", "release.pdf")
        second, second_created = save_raw(self.source, b"SECOND", "release.pdf")
        self.assertTrue(created and second_created)
        self.assertNotEqual(first.stored_path, second.stored_path)
        self.assertEqual(verified_raw_bytes(first), b"FIRST")
        self.assertEqual(verified_raw_bytes(second), b"SECOND")

    def test_deduplication_preserves_existing_metadata_and_validates_bytes(self):
        first, _ = save_raw(self.source, b"FIRST", "release.pdf", source_url="https://example.test/original")
        second, created = save_raw(self.source, b"FIRST", "different.pdf", source_url="https://example.test/changed")
        self.assertFalse(created)
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.source_url, "https://example.test/original")
        Path(first.stored_path).write_bytes(b"TAMPERED")
        with self.assertRaises(ValueError):
            save_raw(self.source, b"FIRST", "release.pdf")
        self.assertEqual(Path(first.stored_path).read_bytes(), b"TAMPERED")

    def test_source_identifier_and_filename_cannot_escape_root(self):
        self.source.source_id = "../../source-outside"
        self.source.save()
        raw, _ = save_raw(self.source, b"FIRST", "../../evil.txt")
        self.assertTrue(Path(raw.stored_path).resolve().is_relative_to(self.root.resolve()))
        self.assertEqual(verified_raw_bytes(raw), b"FIRST")

    def test_oversized_content_never_registers_a_raw_record(self):
        with override_settings(DEKSI_MAX_RAW_BYTES=2), self.assertRaises(ValueError):
            save_raw(self.source, b"FIRST", "release.pdf")
        self.assertEqual(RawFile.objects.count(), 0)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_preexisting_content_addressed_bytes_are_never_replaced(self):
        first, _ = save_raw(self.source, b"FIRST", "release.pdf")
        path = Path(first.stored_path)
        first.delete()
        path.write_bytes(b"TAMPERED")
        with self.assertRaises(ValueError):
            save_raw(self.source, b"FIRST", "release.pdf")
        self.assertEqual(path.read_bytes(), b"TAMPERED")
        self.assertEqual(RawFile.objects.count(), 0)

    def test_open_failure_must_not_delete_a_preexisting_raw(self):
        first, _ = save_raw(self.source, b"FIRST", "release.pdf")
        path = Path(first.stored_path)
        first.delete()
        with patch.object(Path, "open", side_effect=PermissionError("Synthetic filesystem denial")):
            with self.assertRaises(PermissionError):
                save_raw(self.source, b"FIRST", "release.pdf")
        self.assertTrue(path.exists())
        self.assertEqual(path.read_bytes(), b"FIRST")
