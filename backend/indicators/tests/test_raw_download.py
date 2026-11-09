import hashlib
import os
import tempfile
from pathlib import Path

from django.test import override_settings

from indicators.models import RawFile
from indicators.tests.support import IndicatorCase


class RawDownloadTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"], prefix="deksi-f7-raw-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "raw"
        self.root.mkdir()
        self.override = override_settings(DEKSI_RAW_DIR=self.root, DEKSI_MAX_RAW_BYTES=100)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def raw(self, content=b"UJI SINTETIS", path=None, name="test.txt", **changes):
        path = path or self.root / "test.raw"
        if not path.exists():
            path.write_bytes(content)
        fields = {"source": self.source, "document_name": name, "stored_path": str(path),
                  "checksum_sha256": hashlib.sha256(content).hexdigest(), "file_size_bytes": len(content)}
        fields.update(changes)
        raw = RawFile.objects.create(**fields)
        self.observation(raw_file=raw)
        return raw

    def download(self, raw):
        return self.client.get(f"/api/indicators/inflasi/raw-file/{raw.pk}/")

    def test_valid_bytes_and_safe_attachment_headers(self):
        raw = self.raw(name='../bad"\r\n<script>.html')
        response = self.download(raw)
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"UJI SINTETIS")
            self.assertEqual(response["X-Checksum-SHA256"], raw.checksum_sha256)
            self.assertEqual(response["Content-Type"], "application/octet-stream")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
            self.assertIn("attachment", response["Content-Disposition"])
            self.assertNotIn("<script>", response["Content-Disposition"])
            self.assertNotIn("..", response["Content-Disposition"])
            self.assertIn("no-store", response["Cache-Control"])
        finally:
            response.close()

    def test_path_outside_raw_root_is_rejected_even_if_checksum_matches(self):
        raw = self.raw(path=Path(self.temporary.name) / "outside.txt")
        response = self.download(raw)
        response.close()
        self.assertEqual(response.status_code, 404)

    def test_missing_file_and_directory_return_404(self):
        raw = self.raw()
        Path(raw.stored_path).unlink()
        self.assertEqual(self.download(raw).status_code, 404)
        raw.stored_path = str(self.root)
        raw.save()
        self.assertEqual(self.download(raw).status_code, 404)

    def test_corruption_and_wrong_size_return_503(self):
        raw = self.raw()
        Path(raw.stored_path).write_bytes(b"CORRUPT")
        self.assertEqual(self.download(raw).status_code, 503)
        Path(raw.stored_path).write_bytes(b"UJI SINTETIS")
        raw.file_size_bytes = 999
        raw.save()
        self.assertEqual(self.download(raw).status_code, 503)

    def test_bound_read_refuses_oversized_content(self):
        raw = self.raw()
        with override_settings(DEKSI_MAX_RAW_BYTES=3):
            response = self.download(raw)
            response.close()
            self.assertEqual(response.status_code, 503)

    def test_download_is_get_only_and_cannot_cross_indicator(self):
        raw = self.raw()
        self.assertEqual(self.client.post(f"/api/indicators/inflasi/raw-file/{raw.pk}/").status_code, 405)
        self.assertEqual(self.client.get(f"/api/indicators/other/raw-file/{raw.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/indicators/inflasi/raw-file/999999/").status_code, 404)

    def test_symlink_is_not_followed(self):
        raw = self.raw()
        link = self.root / "link.raw"
        try:
            link.symlink_to(Path(raw.stored_path))
        except OSError:
            self.skipTest("Creating symlinks requires privileges unavailable to this Windows test process")
        raw.stored_path = str(link)
        raw.save()
        response = self.download(raw)
        response.close()
        self.assertEqual(response.status_code, 404)
