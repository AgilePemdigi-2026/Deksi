"""Real React → Django bulk review with an owned synthetic SQLite test database."""
import os
import secrets
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase

from indicators.lifecycle import stage_observation
from indicators.models import (
    BulkCandidateReview,
    DataUpdateLog,
    Indicator,
    Observation,
    ObservationCandidate,
    RawFile,
    Source,
)


class BulkCandidateBrowserTests(LiveServerTestCase):
    def test_browser_preview_confirm_readback_and_public_boundary(self):
        frontend = os.environ.get("DEKSI_FRONTEND_TEST_ROOT")
        scratch = os.environ.get("HERMES_TEST_SCRATCH")
        if not frontend or not scratch:
            self.skipTest("Explicit test frontend and agent-owned scratch are required")
        self.assertTrue(Path(scratch).is_dir())
        password = secrets.token_urlsafe(24)
        reviewer = get_user_model().objects.create_superuser(username="synthetic-browser-bulk", password=password)
        source = Source.objects.create(source_id="BULK_TEST", source_name="Synthetic Bulk Source",
                                       institution="Synthetic Institution", primary_url="https://example.test/bulk")
        indicator = Indicator.objects.create(code="inflasi", name="Inflasi Bulk UJI", category="Uji", unit="%")
        ids = []
        for day in range(1, 23):
            raw = None
            if day == 21:
                raw = RawFile.objects.create(source=source, document_name="RAW UJI 21",
                    checksum_sha256="b" * 64, file_size_bytes=1)
            candidate = stage_observation(indicator_id=indicator.pk, source_id=source.pk,
                observation_date=date(2024, 1, day), period_label=f"SINTETIS {day}",
                frequency="monthly", data_type="yoy", value=Decimal(f"{day}.000000"), unit="%",
                publication_date=date(2024, 2, 1) if day == 21 else None,
                raw_file_id=raw.pk if raw else None)
            self.assertIsNotNone(candidate)
            ids.append(candidate.pk)
        env = os.environ.copy()
        env.update(DEKSI_TEST_BACKEND=self.live_server_url, DEKSI_TEST_USER=reviewer.username,
                   DEKSI_TEST_PASS=password)
        result = subprocess.run(["node", str(Path(frontend) / "tests/bulk-candidate-e2e.browser.mjs")],
                                cwd=frontend, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: real browser bulk review", result.stdout)
        batch = BulkCandidateReview.objects.get(source=source, reviewer=reviewer)
        self.assertEqual(batch.status, BulkCandidateReview.Status.COMPLETED)
        self.assertEqual(batch.items.filter(status="published").count(), 1)
        self.assertEqual(batch.items.filter(status="excluded").count(), 21)
        self.assertEqual(ObservationCandidate.objects.get(pk=ids[20]).status, "published")
        self.assertEqual(ObservationCandidate.objects.filter(source=source, status="pending").count(), 21)
        self.assertEqual(Observation.objects.filter(source=source, validation_status="published").count(), 1)
        self.assertEqual(Observation.objects.get(source=source).value, Decimal("21.000000"))
        self.assertEqual(DataUpdateLog.objects.filter(source=source.institution, event_kind="publication").count(), 1)
        print(result.stdout.strip())
