"""Executable BDD bindings for Admin config: thresholds (F24), notifications (F26),
restore defaults (F27).

All records are synthetic and live only in the runner-owned disposable database.
Generic steps (anonymous session, staff session, generic 404) are defined once in
monitoring_schedules_steps and reused here; do not redefine them.
"""
import json
import uuid
from datetime import date
from decimal import Decimal

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from indicators.diagnostic_engine import active_threshold_value
from indicators.models import Indicator, Observation, Source
from indicators.notification_model import (
    NotificationAudit,
    NotificationEvent,
    NotificationPreference,
)
from indicators.schedule_model import ScheduleAudit, ScheduleConfig
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import finalize_sync_run
from indicators.threshold_model import DiagnosticThreshold, DiagnosticThresholdAudit


def _staff(context):
    context.admin = get_user_model().objects.create_user(
        username=f"synthetic-bdd-config-{uuid.uuid4().hex[:12]}",
        email="pengelola@example.test",
        is_staff=True,
    )
    context.client = Client(enforce_csrf_checks=True)
    context.client.force_login(context.admin)
    return context.client


def _csrf(context):
    response = context.client.get("/api/auth/csrf/")
    assert response.status_code == 200, response.content[:300]
    context.csrf_token = response.json()["csrfToken"]
    return context.csrf_token


def _clean_config():
    for model in (Observation, SyncRun):
        model.objects.all().delete()
    DiagnosticThresholdAudit.objects.all().delete()
    DiagnosticThreshold.objects.all().delete()
    ScheduleAudit.objects.all().delete()
    ScheduleConfig.objects.all().delete()
    NotificationAudit.objects.all().delete()
    NotificationEvent.objects.all().delete()
    NotificationPreference.objects.all().delete()
    Source.objects.all().delete()
    Indicator.objects.all().delete()


def _staff_csrf(context):
    _staff(context)
    _csrf(context)


def _put(context, path, payload):
    return context.client.put(
        path, data=json.dumps(payload), content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


def _post(context, path, payload):
    return context.client.post(
        path, data=json.dumps(payload), content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


def _indicator_pdb():
    return Indicator.objects.create(
        code="pdb", name="SYNTHETIC BDD PDB", category="Uji", unit="%",
    )


@given("Admin telah masuk tanpa konfigurasi threshold")
def staff_without_thresholds(context):
    _clean_config()
    _staff(context)


@when("Admin meminta daftar threshold")
def request_threshold_list(context):
    context.response = context.client.get("/api/admin/thresholds/")


@then("daftar memuat parameter registry dengan nilai default dan status aktif")
def assert_threshold_list(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["count"] > 0, body
    pdb_rows = [row for row in body["thresholds"] if row["indicatorCode"] == "pdb"]
    assert pdb_rows, body
    row = pdb_rows[0]
    assert row["value"] == "5", row
    assert row["status"] == "active", row
    assert row["configured"] is False, row


@given("Admin memiliki indikator sintetis pdb dan token CSRF valid")
def pdb_indicator_fixture(context):
    _clean_config()
    _staff_csrf(context)
    _indicator_pdb()


@when("Admin menyimpan threshold pdb dalam rentang dengan alasan")
def save_threshold_valid(context):
    context.response = _put(
        context, "/api/admin/thresholds/pdb/batas_pdb_yoy/update/",
        {"value": "6", "unit": "%", "reason": "SYNTHETIC BDD uji ambang"},
    )


@then("threshold tersimpan berversi dengan audit dan evaluasi diagnostik")
def assert_threshold_saved(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()["threshold"]
    assert body["value"] == "6", body
    assert body["version"] == 1, body
    assert active_threshold_value("pdb", "batas_pdb_yoy") == Decimal(6)
    audits = DiagnosticThresholdAudit.objects.filter(
        indicator_code="pdb", param_key="batas_pdb_yoy")
    assert audits.count() == 1, list(audits.values("reason"))
    assert audits.first().reason == "SYNTHETIC BDD uji ambang"
    assert context.response.json()["message"] == "Konfigurasi tersimpan"
    assert context.response.json()["evaluation"]["status"] == "tidak-tersedia"


@when("Admin menyimpan threshold pdb di luar rentang dan satuan salah")
def save_threshold_invalid(context):
    context.low_response = _put(
        context, "/api/admin/thresholds/pdb/batas_pdb_yoy/update/",
        {"value": "-10", "unit": "%"},
    )
    context.unit_response = _put(
        context, "/api/admin/thresholds/pdb/batas_pdb_yoy/update/",
        {"value": "6", "unit": "Rp triliun"},
    )


@then("server menolak dengan status 400 dan tidak ada baris threshold baru")
def assert_threshold_invalid_rejected(context):
    assert context.low_response.status_code == 400, context.low_response.content[:300]
    assert "Nilai batas tidak valid" in context.low_response.json()["error"]
    assert context.unit_response.status_code == 400, context.unit_response.content[:300]
    assert DiagnosticThreshold.objects.count() == 0
    assert DiagnosticThresholdAudit.objects.count() == 0


@when("Admin meminta detail threshold untuk indikator dan parameter tidak dikenal")
def request_threshold_unknown(context):
    context.response = context.client.get("/api/admin/thresholds/zzz/zzz/")


@when("Admin menyimpan threshold untuk kode registry tanpa baris indikator")
def save_threshold_missing_indicator(context):
    context.response = _put(
        context, "/api/admin/thresholds/inflasi/batas_inflasi_yoy/update/",
        {"value": "3", "unit": "%"},
    )


@then("server menolak dengan status 404 tanpa audit baru")
def assert_threshold_missing_rejected(context):
    assert context.response.status_code == 404, context.response.content[:300]
    assert DiagnosticThresholdAudit.objects.count() == 0


@given("Admin memiliki threshold pdb yang sudah diubah satu kali")
def threshold_changed_once_fixture(context):
    _clean_config()
    _staff_csrf(context)
    _indicator_pdb()
    first = _put(
        context, "/api/admin/thresholds/pdb/batas_pdb_yoy/update/",
        {"value": "6", "unit": "%", "reason": "SYNTHETIC BDD pertama"},
    )
    assert first.status_code == 200, first.content[:300]


@when("Admin meminta riwayat threshold tersebut")
def request_threshold_history(context):
    context.response = context.client.get(
        "/api/admin/thresholds/pdb/batas_pdb_yoy/history/"
    )


@then("riwayat memuat satu entri dengan nilai lama dan baru")
def assert_threshold_history(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["count"] == 1, body
    entry = body["history"][0]
    assert entry["oldValue"]["value"] == "5", entry
    assert entry["newValue"]["value"] == "6", entry


@given("Admin memiliki indikator sintetis pdb dengan observasi terpublikasi")
def pdb_published_fixture(context):
    _clean_config()
    _staff(context)
    indicator = _indicator_pdb()
    source = Source.objects.create(
        source_id="BDDTHR-SUMBER", source_name="SYNTHETIC BDD",
        institution="INSTANSI UJI SINTETIS",
        primary_url="https://example.test/sumber",
    )
    Observation.objects.create(
        indicator=indicator, source=source, observation_date=date(2026, 9, 30),
        period_label="SYNTHETIS BDD Q3", frequency="quarterly", data_type="level",
        value=Decimal("7.5"), unit="%", reviewed_by=context.admin,
        reviewed_at=timezone.now(),
        validation_status=Observation.Status.PUBLISHED,
    )


@when("Admin meminta evaluasi diagnostik pdb")
def request_threshold_evaluate(context):
    context.response = context.client.get(
        "/api/admin/thresholds/evaluate/?indicator=pdb&param=batas_pdb_yoy"
    )


@then("evaluasi memuat status terhadap ambang dan periode observasi")
def assert_threshold_evaluate(context):
    assert context.response.status_code == 200, context.response.content[:300]
    diagnostic = context.response.json()["diagnostic"]
    assert diagnostic["status"] == "melebihi", diagnostic
    assert diagnostic["observed"] == "7.500000", diagnostic
    assert diagnostic["latestPeriod"] == "SYNTHETIS BDD Q3", diagnostic


@when("pengunjung meminta daftar threshold")
def anonymous_threshold_list(context):
    context.response = context.client.get("/api/admin/thresholds/")


@then("server menolak akses threshold dengan status 401")
def assert_threshold_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]


@given("pengguna masuk tanpa hak staf pengelola")
def viewer_session(context):
    _clean_config()
    # _clean_config sudah menghapus semua baris sintetis di atas.
    viewer = get_user_model().objects.create_user(
        username=f"synthetic-bdd-viewer-{uuid.uuid4().hex[:12]}",
        email="penonton@example.test",
        is_staff=False,
    )
    context.client = Client(enforce_csrf_checks=True)
    context.client.force_login(viewer)


@when("pengguna menyimpan threshold pdb yang valid")
def viewer_save_threshold(context):
    _indicator_pdb()
    token = context.client.get("/api/auth/csrf/")
    assert token.status_code == 200, token.content[:300]
    context.csrf_token = token.json()["csrfToken"]
    context.response = _put(
        context, "/api/admin/thresholds/pdb/batas_pdb_yoy/update/",
        {"value": "6", "unit": "%"},
    )


@then("server menolak dengan status 403 dan tidak ada baris threshold baru")
def assert_viewer_forbidden(context):
    assert context.response.status_code == 403, context.response.content[:300]
    assert DiagnosticThreshold.objects.count() == 0


@when("Admin menyimpan parameter formula inti yang tak terdaftar")
def save_formula_param(context):
    context.response = _put(
        context, "/api/admin/thresholds/pdb/formula_inti/update/",
        {"value": "1", "unit": "%"},
    )


@given("Admin telah masuk tanpa preferensi notifikasi")
def staff_without_prefs(context):
    _clean_config()
    _staff(context)


@when("Admin meminta daftar notifikasi")
def request_notification_list(context):
    context.response = context.client.get("/api/admin/notifications/")


@then("daftar memuat tiga jenis dengan nilai default dan kanal event-log")
def assert_notification_list(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["channel"] == "event-log", body
    items = {row["kind"]: row for row in body["notifications"]}
    assert set(items) == {"sync_failed", "threshold_exceeded", "validation_failed"}, body
    assert items["sync_failed"]["enabled"] is True, items
    assert items["threshold_exceeded"]["enabled"] is False, items
    assert items["sync_failed"]["configured"] is False, items
    assert items["sync_failed"]["version"] == 0, items


@when("Admin menonaktifkan notifikasi gagal sinkronisasi dengan alasan")
def disable_sync_failed(context):
    context.response = _put(
        context, "/api/admin/notifications/sync_failed/",
        {"enabled": False, "reason": "SYNTHETIC BDD uji preferensi"},
    )


@then("preferensi tersimpan berversi dengan audit")
def assert_notification_saved(context):
    assert context.response.status_code == 200, context.response.content[:300]
    pref = NotificationPreference.objects.get(kind="sync_failed")
    assert pref.enabled is False
    assert pref.version == 1
    assert NotificationAudit.objects.filter(kind="sync_failed").count() == 1


@when("Admin mengubah jenis tidak dikenal dan flag bukan boolean")
def update_notification_invalid(context):
    context.unknown_response = _put(
        context, "/api/admin/notifications/sms/", {"enabled": True}
    )
    context.flag_response = _put(
        context, "/api/admin/notifications/sync_failed/", {"enabled": "yes"}
    )


@then("server menolak dengan status 404 dan 400 tanpa audit baru")
def assert_notification_invalid_rejected(context):
    assert context.unknown_response.status_code == 404, context.unknown_response.content[:300]
    assert context.flag_response.status_code == 400, context.flag_response.content[:300]
    assert NotificationAudit.objects.count() == 0


@given("Admin memiliki sumber sintetis dan preferensi gagal sinkronisasi aktif")
def notif_enabled_fixture(context):
    _clean_config()
    _staff(context)
    context.source = Source.objects.create(
        source_id="BDDNOTIF-AKTIF", source_name="SYNTHETIC BDD",
        institution="INSTANSI UJI SINTETIS",
        primary_url="https://example.test/sumber",
    )
    NotificationPreference.objects.create(kind="sync_failed", enabled=True, version=1)


@given("Admin memiliki sumber sintetis dan preferensi gagal sinkronisasi nonaktif")
def notif_disabled_fixture(context):
    _clean_config()
    _staff(context)
    context.source = Source.objects.create(
        source_id="BDDNOTIF-MATI", source_name="SYNTHETIC BDD",
        institution="INSTANSI UJI SINTETIS",
        primary_url="https://example.test/sumber",
    )
    NotificationPreference.objects.create(kind="sync_failed", enabled=False, version=1)


@when("sinkronisasi sumber gagal")
def fail_sync_run(context):
    run = SyncRun.objects.create(
        source=context.source, source_id_snapshot=context.source.source_id,
        source_name_snapshot=context.source.source_name,
        status=SyncRun.Status.RUNNING, started_at=timezone.now(),
    )
    finalize_sync_run(run, success=False)


@then("event tercatat bertanda notified")
def assert_event_notified(context):
    event = NotificationEvent.objects.filter(kind="sync_failed").first()
    assert event is not None
    assert event.notified is True


@then("event tercatat tanpa tanda notified")
def assert_event_silent(context):
    event = NotificationEvent.objects.filter(kind="sync_failed").first()
    assert event is not None
    assert event.notified is False


@when("pengunjung meminta daftar notifikasi")
def anonymous_notification_list(context):
    context.response = context.client.get("/api/admin/notifications/")


@then("server menolak akses notifikasi dengan status 401")
def assert_notification_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]


@given("Admin telah mengubah preferensi notifikasi dan jadwal sumber sintetis")
def changed_config_fixture(context):
    _clean_config()
    _staff_csrf(context)
    NotificationPreference.objects.create(kind="sync_failed", enabled=False, version=1)
    context.source = Source.objects.create(
        source_id="BKPM", source_name="SYNTHETIC BDD BKPM",
        institution="INSTANSI UJI SINTETIS",
        primary_url="https://example.test/bkpm",
    )
    ScheduleConfig.objects.create(
        source=context.source, interval_days=7, run_time=None, enabled=False,
        next_run=timezone.now(), version=5, updated_by=context.admin,
    )
    DiagnosticThreshold.objects.create(
        indicator_code="pdb", param_key="batas_pdb_yoy", value=Decimal(9),
        unit="%", min_allowed=Decimal(0), max_allowed=Decimal(15),
        status="active", version=3, updated_by=context.admin,
    )


@when("Admin meminta restore domain notifikasi dan jadwal dengan token CSRF valid")
def restore_subset(context):
    context.response = _post(
        context, "/api/admin/config/restore/",
        {"domains": ["notifications", "schedules"]},
    )


@then("nilai kembali ke default dengan audit restore dan teks jadwal sumber ikut pulih")
def assert_restore_subset(context):
    assert context.response.status_code == 200, context.response.content[:300]
    results = context.response.json()["results"]
    assert set(results) == {"notifications", "schedules"}, results
    pref = NotificationPreference.objects.get(kind="sync_failed")
    assert pref.enabled is True, (pref.enabled, pref.version)
    assert pref.version == 2
    assert NotificationAudit.objects.filter(
        kind="sync_failed", reason="restore-default").count() == 1
    context.source.refresh_from_db()
    assert context.source.update_schedule == "Triwulanan PMA/PMDN"
    assert DiagnosticThreshold.objects.get(
        indicator_code="pdb", param_key="batas_pdb_yoy").value == Decimal(9)


@when("Admin meminta restore domain threshold")
def restore_thresholds(context):
    context.response = _post(context, "/api/admin/config/restore/", {"domains": ["thresholds"]})


@then("hasil bertanda skipped tanpa baris threshold baru")
def assert_restore_thresholds_skipped(context):
    assert context.response.status_code == 200, context.response.content[:300]
    items = context.response.json()["results"]["thresholds"]
    assert items[0]["status"] == "skipped-unsupported", items
    assert DiagnosticThreshold.objects.count() == 0


@when("Admin meminta restore domain tidak dikenal dan daftar kosong")
def restore_invalid(context):
    context.unknown_response = _post(
        context, "/api/admin/config/restore/", {"domains": ["ngawur"]})
    context.empty_response = _post(
        context, "/api/admin/config/restore/", {"domains": []})


@then("server menolak dengan status 400")
def assert_restore_invalid_rejected(context):
    assert context.unknown_response.status_code == 400, context.unknown_response.content[:300]
    assert context.empty_response.status_code == 400, context.empty_response.content[:300]


@when("pengunjung meminta restore konfigurasi")
def anonymous_restore(context):
    token_response = context.client.get("/api/auth/csrf/")
    assert token_response.status_code == 200, token_response.content[:300]
    context.response = context.client.post(
        "/api/admin/config/restore/", data=json.dumps({"domains": ["notifications"]}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token_response.json()["csrfToken"],
    )


@then("server menolak akses restore dengan status 401")
def assert_restore_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]


@when("Admin meminta restore semua domain dengan token CSRF valid")
def restore_all(context):
    context.response = _post(context, "/api/admin/config/restore/", {})


@then("semua domain kembali ke default dengan pesan pengaturan awal")
def assert_restore_all(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["message"] == "Konfigurasi dikembalikan ke pengaturan awal", body
    assert set(body["results"]) == {"notifications", "schedules", "thresholds"}, body
    assert NotificationPreference.objects.get(kind="sync_failed").enabled is True
