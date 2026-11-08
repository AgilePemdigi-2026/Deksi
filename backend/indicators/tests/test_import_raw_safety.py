import os
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import override_settings

from indicators.lifecycle import stage_observation
from indicators.models import Observation
from indicators.storage import save_raw
from indicators.tests.support import IndicatorCase


class ImportRawSafetyTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(dir=os.environ["HERMES_TEST_SCRATCH"], prefix="deksi-candidate-raw-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "guard" / "raw"
        override = override_settings(DEKSI_RAW_DIR=self.root)
        override.enable()
        self.addCleanup(override.disable)

    def test_staging_reused_document_name_preserves_active_raw_bytes(self):
        first, _ = save_raw(self.source, b"UJI FIRST", "same-release.pdf")
        row = self.observation(value=Decimal("5"), raw_file=first, observation_date=date(2020, 1, 31))
        second, _ = save_raw(self.source, b"UJI SECOND", "same-release.pdf")
        candidate = stage_observation(indicator_id=row.indicator_id, source_id=row.source_id,
            observation_date=row.observation_date, period_label=row.period_label, frequency=row.frequency,
            data_type=row.data_type, value=Decimal("6"), unit=row.unit, raw_file_id=second.pk)
        self.assertIsNotNone(candidate)
        self.assertEqual(Path(first.stored_path).read_bytes(), b"UJI FIRST")
        row.refresh_from_db()
        self.assertEqual(row.raw_file_id, first.pk)
        self.assertEqual(row.value, Decimal("5"))
        self.assertNotEqual(first.stored_path, second.stored_path)
        self.assertEqual(Observation.objects.count(), 1)

    def test_reimport_does_not_reuse_corrupt_existing_raw(self):
        raw, _ = save_raw(self.source, b"UJI FIRST", "release.pdf")
        Path(raw.stored_path).write_bytes(b"UJI DAMAGED")
        with self.assertRaises(ValueError):
            save_raw(self.source, b"UJI FIRST", "release.pdf")
