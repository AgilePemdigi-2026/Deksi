"""Feature 24: threshold tersimpan berversi, tervalidasi, dipakai Diagnostic Engine."""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client

from indicators.diagnostic_engine import evaluate_observation
from indicators.models import Indicator
from indicators.tests.support import IndicatorCase
from indicators.threshold_model import DiagnosticThreshold, DiagnosticThresholdAudit


class ThresholdApiTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        um = get_user_model()
        self.admin = um.objects.create_user(username="threshold-admin", password="x", is_staff=True)
        self.client = Client()
        self.client.force_login(self.admin)
        Indicator.objects.get_or_create(
            code="pdb", defaults={"name": "PDB", "category": "PDB", "unit": "%"})
        Indicator.objects.get_or_create(
            code="fiskal", defaults={"name": "Fiskal", "category": "Fiskal", "unit": "Rp triliun"})
        Indicator.objects.get_or_create(
            code="investasi", defaults={"name": "Investasi", "category": "Investasi", "unit": "Rp triliun"})
        Indicator.objects.get_or_create(
            code="birate", defaults={"name": "BI-Rate", "category": "Moneter", "unit": "%"})
        Indicator.objects.get_or_create(
            code="tpt", defaults={"name": "Pengangguran", "category": "Tenaga Kerja", "unit": "%"})

    def test_list_requires_auth(self):
        r = Client().get("/api/admin/thresholds/")
        self.assertEqual(r.status_code, 401)

    def test_list_shows_supported_params(self):
        r = self.client.get("/api/admin/thresholds/")
        self.assertEqual(r.status_code, 200)
        codes = {(t["indicatorCode"], t["paramKey"]) for t in r.json()["thresholds"]}
        self.assertIn(("inflasi", "batas_inflasi_yoy"), codes)

    def test_detail_unknown_indicator_rejected(self):
        r = self.client.get("/api/admin/thresholds/unknown/batas_x/")
        self.assertEqual(r.status_code, 404)

    def test_invalid_value_rejected_previous_kept(self):
        r = self.client.put(
            "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
            data=json.dumps({"value": "-10", "unit": "%"}), content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Nilai batas tidak valid", r.json()["error"])
        self.assertFalse(DiagnosticThreshold.objects.filter(
            indicator_code="inflasi", param_key="batas_inflasi_yoy").exists())

    def test_wrong_unit_rejected(self):
        r = self.client.put(
            "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
            data=json.dumps({"value": "6", "unit": "Rp triliun"}), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_valid_update_persist_version_audit(self):
        r = self.client.put(
            "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
            data=json.dumps({"value": "6", "unit": "%"}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "Konfigurasi tersimpan")
        row = DiagnosticThreshold.objects.get(indicator_code="inflasi", param_key="batas_inflasi_yoy")
        self.assertEqual(row.value, Decimal("6"))
        self.assertEqual(row.version, 1)
        self.assertEqual(DiagnosticThresholdAudit.objects.filter(
            indicator_code="inflasi", param_key="batas_inflasi_yoy").count(), 1)
        r2 = self.client.put(
            "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
            data=json.dumps({"value": "5", "unit": "%"}), content_type="application/json")
        self.assertEqual(r2.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.version, 2)

    def test_engine_reads_active_config(self):
        DiagnosticThreshold.objects.create(
            indicator_code="inflasi", param_key="batas_inflasi_yoy",
            value=Decimal("6"), unit="%", min_allowed=Decimal("0"),
            max_allowed=Decimal("20"), updated_by=self.admin)
        below = evaluate_observation("inflasi", "batas_inflasi_yoy", Decimal("5"))
        above = evaluate_observation("inflasi", "batas_inflasi_yoy", Decimal("7"))
        self.assertEqual(below["status"], "normal")
        self.assertTrue(above["exceeded"])
        self.assertEqual(above["status"], "melebihi")

    def test_economic_observation_untouched_by_threshold_change(self):
        obs = self.observation(value=Decimal("2.5"), unit="%", data_type="yoy")
        before = Decimal(obs.value)
        self.client.put(
            "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
            data=json.dumps({"value": "6", "unit": "%"}), content_type="application/json")
        obs.refresh_from_db()
        self.assertEqual(Decimal(obs.value), before)

    def test_history_endpoint(self):
        self.client.put(
            "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
            data=json.dumps({"value": "6", "unit": "%"}), content_type="application/json")
        r = self.client.get("/api/admin/thresholds/inflasi/batas_inflasi_yoy/history/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)
