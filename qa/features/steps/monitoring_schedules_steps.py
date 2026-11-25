"""Executable BDD bindings for Admin monitoring (F19) and schedules (F23).

All records are synthetic and live only in the runner-owned disposable database.
Shared generic steps (anonymous session, staff session, generic 404) live here
and are reused by the config suite; do not redefine the same sentences elsewhere.
"""
import json
import uuid
from datetime import timedelta

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from indicators.models import DataUpdateLog, Indicator, Observation, Source
from indicators.notification_model import (
    NotificationAudit,
    NotificationEvent,
    NotificationPreference,
)
from indicators.schedule_model import ScheduleAudit, ScheduleConfig
from indicators.sync_history_model import SyncRun
from indicators.threshold_model import DiagnosticThreshold, DiagnosticThresholdAudit


def _staff(context, username="synthetic-bdd-ops"):
    context.admin = get_user_model().objects.create_user(
        username=f"{username}-{uuid.uuid4().hex[:12]}",
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


def _clean_monitoring():
    for model in (Observation, SyncRun, DataUpdateLog):
        model.objects.all().delete()
    ScheduleAudit.objects.all().delete()
    ScheduleConfig.objects.all().delete()
    Source.objects.all().delete()
    Indicator.objects.all().delete()


def _source(source_id, status="active"):
    return Source.objects.create(
        source_id=source_id,
        source_name=f"SYNTHETIC BDD {source_id}",
        institution="INSTANSI UJI SINTETIS",
        primary_url="https://example.test/sumber",
        status=status,
    )


def _run(source, status, **overrides):
    now = timezone.now()
    values = {
        "source": source,
        "source_id_snapshot": source.source_id,
        "source_name_snapshot": source.source_name,
        "status": status,
        "started_at": now,
        "safe_message": "",
    }
    values.update(overrides)
    return SyncRun.objects.create(**values)


def _clean_all_bdd():
    for model in (Observation, SyncRun, DataUpdateLog):
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


@given("Admin telah masuk dengan token CSRF valid")
def staff_with_csrf(context):
    _clean_all_bdd()
    _staff(context)
    _csrf(context)


@given("Admin memiliki dua sumber sintetis aktif dan nonaktif dengan riwayat sinkronisasi sukses gagal dan berjalan")
def monitoring_summary_fixture(context):
    _clean_monitoring()
    _staff(context)
    active = _source("BDDMON-AKTIF", status="active")
    _source("BDDMON-ARSIP", status="inactive")
    _run(active, SyncRun.Status.SUCCESS)
    _run(active, SyncRun.Status.FAILED)
    _run(active, SyncRun.Status.RUNNING)
    indicator = Indicator.objects.create(
        code="bddmon", name="SYNTHETIC BDD Mon", category="Uji", unit="%",
    )
    Observation.objects.create(
        indicator=indicator, source=active, observation_date="2026-01-31",
        period_label="SYNTHETIS BDD 01", frequency="monthly", data_type="level",
        value=1, unit="%", validation_status=Observation.Status.PUBLISHED,
    )
    Observation.objects.create(
        indicator=indicator, source=active, observation_date="2026-02-28",
        period_label="SYNTHETIS BDD 02", frequency="monthly", data_type="level",
        value=2, unit="%", validation_status=Observation.Status.PENDING,
    )


@when("Admin meminta ringkasan monitoring")
def request_monitoring_summary(context):
    context.response = context.client.get("/api/admin/monitoring/summary/")


@then("ringkasan memuat hitungan sumber dan status sinkronisasi serta label kualitas")
def assert_monitoring_summary(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["totalSources"] == 2, body
    assert body["activeSources"] == 1, body
    assert body["inactiveSources"] == 1, body
    assert body["syncSuccess"] == 1, body
    assert body["syncFailed"] == 1, body
    assert body["syncRunning"] == 1, body
    assert body["quality"] == {"label": "Perlu perhatian", "validated": 1, "total": 2}, body
    assert body["lastSyncAt"], body


@given("Admin memiliki sumber sintetis dengan satu observasi terpublikasi dan satu riwayat sukses")
def monitoring_sources_fixture(context):
    _clean_monitoring()
    _staff(context)
    context.source = _source("BDDMON-SATU")
    _run(context.source, SyncRun.Status.SUCCESS, safe_message="SYNTHETIC BDD selesai.")
    indicator = Indicator.objects.create(
        code="bddmon", name="SYNTHETIC BDD Mon", category="Uji", unit="%"
    )
    Observation.objects.create(
        indicator=indicator, source=context.source, observation_date="2026-03-31",
        period_label="SYNTHETIS BDD Q1", frequency="quarterly", data_type="level",
        value=3, unit="%", validation_status=Observation.Status.PUBLISHED,
    )


@when("Admin meminta daftar sumber monitoring")
def request_monitoring_sources(context):
    context.response = context.client.get("/api/admin/monitoring/sources/")


@then("daftar memuat status sinkronisasi terakhir dan hitungan observasi sumber tersebut")
def assert_monitoring_sources(context):
    assert context.response.status_code == 200, context.response.content[:300]
    items = {row["sourceId"]: row for row in context.response.json()["sources"]}
    row = items["BDDMON-SATU"]
    assert row["lastSyncStatus"] == SyncRun.Status.SUCCESS, row
    assert row["lastSyncAt"], row
    assert row["observationCount"] == 1, row
    assert row["lastPeriod"] == "SYNTHETIS BDD Q1", row


@given("Admin memiliki dua riwayat sinkronisasi dengan status berbeda")
def monitoring_history_fixture(context):
    _clean_monitoring()
    _staff(context)
    context.source = _source("BDDMON-RIWAYAT")
    _run(context.source, SyncRun.Status.SUCCESS)
    _run(context.source, SyncRun.Status.FAILED, safe_message="SYNTHETIC BDD gagal.")


@when("Admin meminta halaman riwayat dengan filter status gagal")
def request_monitoring_history_filtered(context):
    context.response = context.client.get(
        "/api/admin/monitoring/history/?page=1&pageSize=20&status=failed"
    )


@then("halaman hanya memuat riwayat gagal dengan total yang benar")
def assert_monitoring_history_filtered(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["total"] == 1, body
    assert [item["status"] for item in body["items"]] == [SyncRun.Status.FAILED], body


@given("Admin memiliki satu riwayat sinkronisasi selesai dengan pesan aman")
def monitoring_run_fixture(context):
    _clean_monitoring()
    _staff(context)
    context.source = _source("BDDMON-RUN")
    started = timezone.now()
    context.run = _run(
        context.source, SyncRun.Status.SUCCESS, started_at=started,
        finished_at=started + timedelta(seconds=60),
        safe_message="SYNTHETIC BDD selesai tanpa data sensitif.",
    )


@when("Admin meminta detail riwayat tersebut")
def request_monitoring_run_detail(context):
    context.response = context.client.get(
        f"/api/admin/monitoring/runs/{context.run.pk}/"
    )


@then("detail memuat durasi hitung dan pesan aman tanpa data sensitif")
def assert_monitoring_run_detail(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["durationSeconds"] == 60, body
    assert body["message"] == "SYNTHETIC BDD selesai tanpa data sensitif.", body
    assert body["sourceId"] == "BDDMON-RUN", body


@given("Admin telah masuk tanpa riwayat sinkronisasi")
def staff_without_runs(context):
    _clean_monitoring()
    _staff(context)


@when("Admin meminta detail riwayat yang tidak ada")
def request_monitoring_run_missing(context):
    context.response = context.client.get("/api/admin/monitoring/runs/999999/")


@then("server menolak dengan status 404")
def assert_not_found(context):
    assert context.response.status_code == 404, context.response.content[:300]


@when("pengunjung meminta ringkasan monitoring")
def anonymous_monitoring_summary(context):
    context.response = context.client.get("/api/admin/monitoring/summary/")


@then("server menolak akses monitoring dengan status 401")
def assert_monitoring_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]


@given("Admin memiliki sumber sintetis aktif tanpa konfigurasi jadwal")
def schedule_list_fixture(context):
    _clean_monitoring()
    _staff(context)
    _source("BDDSCHED-SATU", status="active")


@when("Admin meminta daftar jadwal")
def request_schedule_list(context):
    context.response = context.client.get("/api/admin/schedules/")


@then("daftar memuat sumber tersebut dengan interval default dan status aktif")
def assert_schedule_list(context):
    assert context.response.status_code == 200, context.response.content[:300]
    items = {row["sourceId"]: row for row in context.response.json()["schedules"]}
    row = items["BDDSCHED-SATU"]
    assert row["intervalDays"] == 30, row
    assert row["enabled"] is True, row
    assert row["configured"] is False, row
    assert row["version"] == 0, row


@given("Admin memiliki sumber sintetis aktif dan token CSRF valid")
def schedule_source_fixture(context):
    _clean_monitoring()
    _staff(context)
    _csrf(context)
    context.source = _source("BDDSCHED-UBAH", status="active")


def _put(context, path, payload):
    return context.client.put(
        path, data=json.dumps(payload), content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


@when("Admin menyimpan jadwal interval 7 hari nonaktif dengan jam jalan")
def save_schedule_valid(context):
    context.response = _put(
        context, f"/api/admin/schedules/{context.source.source_id}/",
        {"intervalDays": 7, "runTime": "08:30", "enabled": False,
         "reason": "SYNTHETIC BDD uji jadwal"},
    )


@then("jadwal tersimpan berversi dengan audit dan teks jadwal sumber ikut berubah")
def assert_schedule_saved(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()["schedule"]
    assert body["intervalDays"] == 7, body
    assert body["enabled"] is False, body
    assert body["version"] == 1, body
    assert body["runTime"] == "08:30", body
    assert ScheduleAudit.objects.filter(
        source_id_snapshot=context.source.source_id).count() == 1
    context.source.refresh_from_db()
    assert context.source.update_schedule == "Setiap 7 hari pukul 08:30 (nonaktif)"


@when("Admin menyimpan jadwal dengan interval di luar rentang dan format jam salah")
def save_schedule_invalid(context):
    context.response = _put(
        context, f"/api/admin/schedules/{context.source.source_id}/",
        {"intervalDays": 0, "runTime": "25:00", "enabled": "yes"},
    )


@then("server menolak dengan status 400 dan konfigurasi tetap kosong")
def assert_schedule_rejected(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert ScheduleConfig.objects.count() == 0
    assert ScheduleAudit.objects.count() == 0


@given("Admin memiliki sumber sintetis nonaktif dan token CSRF valid")
def schedule_inactive_fixture(context):
    _clean_monitoring()
    _staff(context)
    _csrf(context)
    context.source = _source("BDDSCHED-MATI", status="inactive")


@when("Admin menyimpan jadwal untuk sumber nonaktif dan sumber tidak ada")
def save_schedule_inactive(context):
    context.inactive_response = _put(
        context, f"/api/admin/schedules/{context.source.source_id}/",
        {"intervalDays": 7},
    )
    context.missing_response = _put(
        context, "/api/admin/schedules/BDD-TIDAK-ADA/",
        {"intervalDays": 7},
    )


@then("server menolak sumber nonaktif dan yang tidak ada tanpa audit baru")
def assert_schedule_inactive_rejected(context):
    assert context.inactive_response.status_code == 400, context.inactive_response.content[:300]
    assert context.missing_response.status_code == 404, context.missing_response.content[:300]
    assert ScheduleAudit.objects.count() == 0


@when("pengunjung meminta daftar jadwal")
def anonymous_schedule_list(context):
    context.response = context.client.get("/api/admin/schedules/")


@then("server menolak akses jadwal dengan status 401")
def assert_schedule_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]


@given("Admin memiliki dua sumber sintetis dengan jadwal aktif dan nonaktif")
def schedule_next_fixture(context):
    _clean_monitoring()
    _staff(context)
    first = _source("BDDSCHED-A", status="active")
    _source("BDDSCHED-B", status="active")
    now = timezone.now()
    ScheduleConfig.objects.create(
        source=first, interval_days=7, enabled=True,
        next_run=now + timedelta(days=1), version=1, updated_by=context.admin,
    )
    ScheduleConfig.objects.create(
        source=Source.objects.get(source_id="BDDSCHED-B"), interval_days=30,
        enabled=False, next_run=now + timedelta(hours=1), version=1,
        updated_by=context.admin,
    )


@when("Admin meminta jadwal berikutnya")
def request_schedule_next(context):
    context.response = context.client.get("/api/admin/schedules/next/")


@then("daftar hanya memuat sumber aktif terurut waktu jalan")
def assert_schedule_next(context):
    assert context.response.status_code == 200, context.response.content[:300]
    upcoming = context.response.json()["upcoming"]
    assert [row["sourceId"] for row in upcoming] == ["BDDSCHED-A"], upcoming


@given("dashboard publik menampilkan satu observasi terpublikasi")
def public_dashboard_fixture(context):
    _clean_monitoring()
    _staff(context)
    _csrf(context)
    context.source = _source("BDDSCHED-PUBLIK", status="active")
    indicator = Indicator.objects.create(
        code="pdb", name="SYNTHETIC BDD PDB", category="Uji", unit="%"
    )
    Observation.objects.create(
        indicator=indicator, source=context.source, observation_date="2026-04-30",
        period_label="SYNTHETIS BDD PUBLIK", frequency="monthly", data_type="level",
        value=9, unit="%", reviewed_by=context.admin, reviewed_at=timezone.now(),
        validation_status=Observation.Status.PUBLISHED,
    )
    anonymous = Client(enforce_csrf_checks=False)
    before = anonymous.get("/api/indicators/dashboard/")
    assert before.status_code == 200, before.content[:300]
    assert "SYNTHETIS BDD PUBLIK" in before.content.decode(), before.content[:300]


@when("Admin menyimpan jadwal baru untuk sumber observasi tersebut")
def save_schedule_for_public_source(context):
    context.response = _put(
        context, f"/api/admin/schedules/{context.source.source_id}/",
        {"intervalDays": 1},
    )
    assert context.response.status_code == 200, context.response.content[:300]


@then("dashboard publik tetap menampilkan observasi yang sama")
def assert_public_dashboard_stable(context):
    anonymous = Client(enforce_csrf_checks=False)
    after = anonymous.get("/api/indicators/dashboard/")
    assert after.status_code == 200, after.content[:300]
    assert "SYNTHETIS BDD PUBLIK" in after.content.decode(), after.content[:300]
