from decimal import Decimal
from unittest.mock import patch

from django.test import Client

from indicators import bps
from indicators.tests.support import IndicatorCase


class SourceStatusLifecycleTests(IndicatorCase):
    def test_disabling_source_preserves_public_observation_and_trace(self):
        self.observation()
        self.source.acquisition_method = "file_xlsx"
        self.source.data_format = "xlsx"
        self.source.frequency = "monthly"
        self.source.save()
        before_summary = self.client.get("/api/indicators/?code=inflasi").json()
        before_trace = self.client.get("/api/indicators/inflasi/source-trace/").json()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.reviewer)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.patch("/api/admin/sources/TEST_ONLY/update/", '{"status":"inactive","expectedRevision":0}',
                                content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/indicators/?code=inflasi").json(), before_summary)
        self.assertEqual(self.client.get("/api/indicators/inflasi/source-trace/").json(), before_trace)

    def test_bps_process_started_active_can_finish_after_deactivation(self):
        source = bps._get_or_create_source()
        series = {"code": "ongoing", "var_id": 123, "name": "Uji", "category": "Uji", "unit": "%",
                  "aggregation_kind": "avg", "sort_order": 1, "frequency": "annual", "data_type": "level"}
        from datetime import date
        point = {"observation_date": date(2020, 12, 31), "period_label": "2020", "data_type": "level",
                 "frequency": "annual", "value": Decimal("1"), "unit": "%"}

        def fetch(*args, **kwargs):
            source.status = "inactive"
            source.save(update_fields=["status"])
            return [point]

        with patch.object(bps, "BPS_SERIES", [series]), patch.object(bps, "fetch_series", side_effect=fetch):
            result = bps.sync_bps_indicators(start_year=2020, end_year=2020)
        self.assertEqual(result["observations"], 1)
        source.refresh_from_db()
        self.assertEqual(source.status, "inactive")
