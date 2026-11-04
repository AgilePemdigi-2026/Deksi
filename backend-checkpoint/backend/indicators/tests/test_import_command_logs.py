from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from indicators.models import DataUpdateLog
from indicators.tests.support import IndicatorCase


class ImportCommandLogTests(IndicatorCase):
    def test_staging_bps_does_not_advance_last_successful_public_update(self):
        count = DataUpdateLog.objects.filter(status="success").count()
        with patch("indicators.bps.sync_bps_indicators", return_value={"observations": 1, "errors": [], "latest": {}}):
            call_command("sync_bps", stdout=StringIO())
        self.assertEqual(DataUpdateLog.objects.filter(status="success").count(), count)

    def test_staging_local_datasets_does_not_advance_last_successful_public_update(self):
        count = DataUpdateLog.objects.filter(status="success").count()
        summary = {"bi_rows": 1, "bkpm_quarters": 0, "errors": [], "scraping_dir": "UJI"}
        with patch("indicators.management.commands.ingest_datasets.ingest_local_datasets", return_value=summary):
            call_command("ingest_datasets", stdout=StringIO())
        self.assertEqual(DataUpdateLog.objects.filter(status="success").count(), count)

    def test_staging_fiscal_does_not_advance_last_successful_public_update(self):
        count = DataUpdateLog.objects.filter(status="success").count()
        summary = {"metrics": ["UJI"], "period_label": "UJI", "document_name": "UJI", "publication_date": None,
                   "checksum": "UJI"}
        with patch("indicators.fiscal.ingest_kita_pdf_url", return_value=summary):
            call_command("fetch_kemenkeu", stdout=StringIO())
        self.assertEqual(DataUpdateLog.objects.filter(status="success").count(), count)
