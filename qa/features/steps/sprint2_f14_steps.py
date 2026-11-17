"""F14-only executable bindings; all state is synthetic and disposable.

Browser scenarios use the existing isolated Chrome -> React/Vite -> Django path.
API scenarios use Django's real views, CSRF-enabled clients and database.
Provider requests are stubbed; the isolated worker is exercised where specified.
"""
import json
import secrets
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from indicators.models import Indicator, Observation, ObservationCandidate, Source
from indicators.resync_model import ResyncJob
from indicators.sync_history_model import SyncRun

BPS_ID = "BPS"
OTHER_ID = "SYNTHETIC_F14_OTHER"


def _source(source_id=BPS_ID, *, status=Source.SourceStatus.ACTIVE,
            method="api_bps", institution="BPS"):
    return Source.objects.update_or_create(
        source_id=source_id,
        defaults={
            "source_name": f"SYNTHETIC F14 {source_id}",
            "institution": institution,
            "primary_url": "https://example.test/f14-synthetic",
            "description": "SYNTHETIC F14 disposable fixture only",
            "acquisition_method": method,
            "endpoint_url": "",
            "data_format": "json" if method == "api_bps" else "xlsx",
            "frequency": "monthly",
            "update_schedule": "SYNTHETIC manual",
            "status": status,
        },
    )[0]


def _admin(context, *, password=None):
    user = get_user_model().objects.create_user(
        username=f"synthetic-f14-{uuid.uuid4().hex[:10]}",
        email="synthetic-f14-admin@example.test",
        password=password,
        is_staff=True,
    )
    context.f14_admin = user
    return user


def _api(context, *, authenticated=True):
    client = Client(enforce_csrf_checks=True)
    if authenticated:
        user = getattr(context, "f14_admin", None) or _admin(context)
        client.force_login(user)
    csrf = client.get("/api/auth/csrf/")
    assert csrf.status_code == 200, csrf.content[:300]
    client.defaults["HTTP_X_CSRFTOKEN"] = csrf.json()["csrfToken"]
    context.f14_api = client
    return client


def _browser_setup(context):
    # Reuse the established real React/Django startup fixture; it creates a
    # synthetic public observation and starts only loopback services.
    context.execute_steps(
        "Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah "
        "dan periode Q1 2025 sudah direview dan dipublikasikan"
    )
    password = secrets.token_urlsafe(24)
    context.user = _admin(context, password=password)
    _source()
    _api(context)
    context.browser.call("Page.navigate", {"url": context.frontend_url + "/admin/login"})
    context.browser.wait("Boolean(document.querySelector('#login-submit')) && !document.querySelector('#login-submit').disabled")
    context.browser.type_text("#identifier", context.user.username)
    context.browser.type_text("#password", password)
    context.browser.click("#login-submit")
    context.browser.wait("Boolean(document.querySelector('#admin-session'))")
    context.browser.wait("location.pathname === '/admin/sumber' && document.readyState === 'complete'")
    context.browser.wait("Boolean(document.querySelector('.resync-action__button'))")
    context.evidence["f14_browser_stack"] = "real Chrome/CDP + React/Vite + Django; synthetic DB; provider disabled"


def _request_job(context, source_id=BPS_ID, key=None):
    key = key or uuid.uuid4()
    response = context.f14_api.post(
        f"/api/admin/sources/{source_id}/resync/",
        data=json.dumps({"requestId": str(key)}),
        content_type="application/json",
    )
    return response, key


def _running_job(context):
    source = getattr(context, "f14_source", None) or _source()
    run = SyncRun.objects.create(
        source=source,
        source_id_snapshot=source.source_id,
        source_name_snapshot=source.source_name,
        status=SyncRun.Status.RUNNING,
        started_at=timezone.now(),
        actor=context.f14_admin,
    )
    job = ResyncJob.objects.create(
        source=source,
        requested_by=context.f14_admin,
        request_key=uuid.uuid4(),
        status=ResyncJob.Status.RUNNING,
        run=run,
    )
    context.f14_source, context.f14_run, context.f14_job = source, run, job
    return job


# ------------------------------ browser: explicit submit / cancellation

@given("Admin browser F14 masuk dan sumber BPS sintetis aktif tanpa pekerjaan aktif")
def f14_browser_ready_unchecked(context):
    _browser_setup(context)
    context.browser.wait("Boolean(document.querySelector('.resync-action input[type=checkbox]'))")
    context.f14_browser_post_count = 0


@given("Admin browser F14 masuk dan sumber BPS sintetis aktif siap disinkronkan")
def f14_browser_ready_checked(context):
    _browser_setup(context)
    context.browser.wait("Boolean(document.querySelector('.resync-action input[type=checkbox]'))")
    context.browser.click(".resync-action input[type=checkbox]")
    assert context.browser.js("document.querySelector('.resync-action input').checked") is True
    context.f14_browser_post_count = 0


@given("Admin F14 telah memeriksa riwayat dan menandai pernyataan pemeriksaan")
def f14_history_checked(context):
    context.browser.click(".resync-action input[type=checkbox]")
    assert context.browser.js("document.querySelector('.resync-action input').checked") is True


@when("Admin F14 memilih sinkronkan dan mengonfirmasi permintaan")
def f14_confirm_request(context):
    context.browser.js("window.confirm = () => true")
    context.browser.wait("Boolean(document.querySelector('.resync-action__button')) && !document.querySelector('.resync-action__button').disabled")
    context.browser.click(".resync-action__button")
    context.browser.wait("Boolean(document.querySelector('.resync-action [role=status]')?.textContent.includes('ID:'))")


@when("Admin F14 membatalkan dialog konfirmasi")
def f14_cancel_request(context):
    context.browser.js("window.__f14ConfirmCount = 0; window.confirm = () => { window.__f14ConfirmCount++; return false }")
    context.browser.wait("Boolean(document.querySelector('.resync-action__button')) && !document.querySelector('.resync-action__button').disabled")
    before = len([r for r in context.browser.requests if r["method"] == "POST" and "/resync/" in r["url"]])
    context.browser.click(".resync-action__button")
    assert context.browser.js("window.__f14ConfirmCount") == 1
    after = len([r for r in context.browser.requests if r["method"] == "POST" and "/resync/" in r["url"]])
    context.f14_browser_post_count = after - before


@then("browser F14 menampilkan identitas pekerjaan dan status server")
def f14_browser_job_visible(context):
    body = context.browser.js("document.querySelector('.resync-action').innerText")
    assert "ID:" in body and "Status server:" in body, body
    assert any("/api/admin/resync-jobs/" in r["url"] for r in context.browser.requests)
    assert any(r["method"] == "POST" and "/resync/" in r["url"] for r in context.browser.requests)
    context.evidence["f14_job_status_ui"] = body


@then("pekerjaan F14 yang baru diterima tidak langsung disebut berhasil")
def f14_not_success(context):
    response = next(r for r in context.browser.requests if r["method"] == "POST" and "/resync/" in r["url"])
    body = context.browser.js("document.querySelector('.resync-action [role=status]').innerText")
    assert response["url"]
    assert "queued" in body.lower() or "antrean" in body.lower()
    assert "Berhasil" not in body and "success" not in body.lower()


@then("browser F14 tidak mengirim permintaan sinkronisasi baru")
def f14_no_cancelled_post(context):
    assert context.f14_browser_post_count == 0
    assert not ResyncJob.objects.exists()


# ------------------------------ API: request guards/idempotency/active job

@given("Admin API F14 login dan tersedia sumber BPS nonaktif serta sumber lain aktif")
def f14_api_sources_negative(context):
    _admin(context)
    _api(context)
    _source(status=Source.SourceStatus.INACTIVE)
    _source(OTHER_ID, institution="SYNTHETIC non-BPS", method="file_xlsx")


@when("Admin API F14 meminta sinkronisasi ulang untuk masing-masing sumber")
def f14_request_unsupported_sources(context):
    context.f14_negative_responses = [
        _request_job(context, BPS_ID)[0],
        _request_job(context, OTHER_ID)[0],
    ]


@then("server F14 menolak setiap permintaan dan tidak membuat pekerjaan")
def f14_assert_no_unsupported_jobs(context):
    assert [response.status_code for response in context.f14_negative_responses] == [409, 400], [
        (response.status_code, response.content[:300]) for response in context.f14_negative_responses
    ]
    assert ResyncJob.objects.count() == 0


@given("Admin API F14 login dan sumber BPS sintetis aktif dengan requestId valid")
def f14_api_idempotency_setup(context):
    _admin(context)
    _api(context)
    _source()
    context.f14_request_key = uuid.uuid4()


@when("Admin API F14 mengirim dua kali requestId yang sama untuk sumber yang sama")
def f14_request_twice(context):
    first, _ = _request_job(context, key=context.f14_request_key)
    second, _ = _request_job(context, key=context.f14_request_key)
    context.f14_responses = first, second


@then("server F14 mengembalikan identitas pekerjaan yang sama tanpa pekerjaan kedua")
def f14_assert_same_job(context):
    first, second = context.f14_responses
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == second.json()["status"] == ResyncJob.Status.QUEUED
    assert ResyncJob.objects.count() == 1


@given("Admin API F14 login dan pekerjaan BPS sintetis sudah aktif")
def f14_api_active_job(context):
    _admin(context)
    _api(context)
    context.f14_source = _source()
    context.f14_original_job = _running_job(context)


@when("Admin API F14 mengirim permintaan baru dengan requestId berbeda")
def f14_request_during_active(context):
    context.f14_response, _ = _request_job(context, key=uuid.uuid4())


@then("server F14 menolak permintaan karena terdapat pekerjaan aktif")
def f14_active_conflict(context):
    assert context.f14_response.status_code == 409, context.f14_response.content[:300]


@then("hanya pekerjaan F14 aktif semula yang dipertahankan")
def f14_original_job_kept(context):
    jobs = list(ResyncJob.objects.filter(source=context.f14_source))
    assert len(jobs) == 1 and jobs[0].pk == context.f14_original_job.pk
    assert jobs[0].status == ResyncJob.Status.RUNNING


# ------------------------------ browser: reload persistence / uncertainty

@given("Admin browser F14 masuk dan pekerjaan BPS sintetis diterima serta masih dalam antrean")
def f14_browser_queued_job(context):
    _browser_setup(context)
    response, _ = _request_job(context, key=uuid.uuid4())
    assert response.status_code == 202, response.content[:300]
    context.f14_job_id = response.json()["id"]
    context.f14_initial_posts = len([r for r in context.browser.requests if r["method"] == "POST" and "/resync/" in r["url"]])


@when("Admin F14 memuat ulang halaman Kelola Sumber")
def f14_reload_sources(context):
    before = context.browser.js("performance.timeOrigin")
    context.browser.call("Page.navigate", {"url": context.frontend_url + "/admin/sumber"})
    context.browser.wait(f"performance.timeOrigin > {before}")
    context.browser.wait("document.querySelector('.resync-action [role=status]')?.textContent.includes('ID:')")


@then("browser F14 menampilkan pekerjaan aktif dan status antrean yang sama")
def f14_assert_reload_job(context):
    body = context.browser.js("document.querySelector('.resync-action [role=status]').innerText")
    assert context.f14_job_id in body and ("queued" in body.lower() or "antrean" in body.lower()), body
    context.evidence["f14_reloaded_job"] = body


@then("pemuatan ulang F14 tidak mengirim permintaan baru secara otomatis")
def f14_assert_no_reload_post(context):
    posts = [r for r in context.browser.requests if r["method"] == "POST" and "/resync/" in r["url"]]
    assert len(posts) == context.f14_initial_posts
    assert ResyncJob.objects.count() == 1


@when("Admin F14 mengonfirmasi permintaan dan koneksi permintaan terputus")
def f14_disconnect_request(context):
    browser = context.browser
    target = "/api/admin/sources/" + BPS_ID + "/resync/"
    original_event = browser.event

    def drop_resync_response(message):
        params = message.get("params", {})
        request = params.get("request", {})
        if (message.get("method") == "Fetch.requestPaused"
                and params.get("responseStatusCode") is not None
                and target in request.get("url", "")):
            browser.faults.append({"url": request["url"], "action": "drop accepted response"})
            browser._send("Fetch.failRequest", {
                "requestId": params["requestId"], "errorReason": "Failed",
            })
            return
        original_event(message)

    browser.event = drop_resync_response
    browser.call("Fetch.disable")
    browser.call("Fetch.enable", {"patterns": [
        {"urlPattern": "*", "requestStage": "Request"},
        {"urlPattern": "*" + target + "*", "requestStage": "Response"},
    ]})
    browser.js("window.confirm = () => true")
    browser.wait("Boolean(document.querySelector('.resync-action__button')) && !document.querySelector('.resync-action__button').disabled")
    browser.click(".resync-action__button")
    browser.wait("Boolean(document.querySelector('.resync-action [role=alert]'))")
    browser.call("Fetch.disable")
    browser.event = original_event
    browser.call("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})
    browser.wait("Boolean(document.querySelector('.resync-action [role=alert]'))")
    assert ResyncJob.objects.filter(source__source_id=BPS_ID, status=ResyncJob.Status.QUEUED).count() == 1


@then("browser F14 menampilkan hasil tidak diketahui dan meminta pemeriksaan antrean atau riwayat")
def f14_uncertain_message(context):
    body = context.browser.js("document.querySelector('.resync-action [role=alert]').innerText")
    assert "tidak diketahui" in body.lower() and ("antrean" in body.lower() or "riwayat" in body.lower())
    context.evidence["f14_uncertain_ui"] = body


@then("browser F14 tidak mengirim ulang permintaan secara otomatis")
def f14_no_retry(context):
    posts = [r for r in context.browser.requests if r["method"] == "POST" and "/resync/" in r["url"]]
    assert len(posts) == 1
    jobs = list(ResyncJob.objects.filter(source__source_id=BPS_ID))
    assert len(jobs) == 1 and jobs[0].status == ResyncJob.Status.QUEUED


# ------------------------------ API: reconciliation and worker fence

@given("Admin API F14 login dan pekerjaan serta run BPS sintetis berstatus running")
def f14_api_running_pair(context):
    _admin(context)
    _api(context)
    context.f14_source = _source()
    _running_job(context)


@when("Admin API F14 merekonsiliasi pekerjaan dengan konfirmasi dan alasan valid")
def f14_reconcile_valid(context):
    context.f14_response = context.f14_api.post(
        f"/api/admin/resync-jobs/{context.f14_job.pk}/reconcile/",
        data=json.dumps({"confirmed": True, "reason": "SYNTHETIC BDD pemeriksaan manual status antrean."}),
        content_type="application/json",
    )


@then("pekerjaan dan run F14 berstatus unknown dengan pemeriksa waktu dan alasan tercatat")
def f14_assert_reconciled(context):
    assert context.f14_response.status_code == 200, context.f14_response.content[:300]
    context.f14_job.refresh_from_db()
    context.f14_run.refresh_from_db()
    assert context.f14_job.status == ResyncJob.Status.UNKNOWN
    assert context.f14_run.status == SyncRun.Status.UNKNOWN
    assert context.f14_job.resolved_by_id == context.f14_admin.pk
    assert context.f14_job.resolved_at is not None
    assert context.f14_job.resolution_reason == "SYNTHETIC BDD pemeriksaan manual status antrean."


@then("rekonsiliasi F14 tidak mengarang waktu selesai atau hasil sukses maupun gagal")
def f14_assert_unknown_not_final(context):
    assert context.f14_job.finished_at is None and context.f14_run.finished_at is None
    assert context.f14_job.status not in (ResyncJob.Status.SUCCESS, ResyncJob.Status.FAILED)
    assert context.f14_run.status not in (SyncRun.Status.SUCCESS, SyncRun.Status.FAILED)


@when("Admin API F14 mengirim rekonsiliasi tanpa konfirmasi atau dengan alasan tidak valid")
def f14_reconcile_invalid(context):
    path = f"/api/admin/resync-jobs/{context.f14_job.pk}/reconcile/"
    invalid = [
        context.f14_api.post(path, data=json.dumps({"confirmed": False, "reason": "alasan valid sintetis"}), content_type="application/json"),
        context.f14_api.post(path, data=json.dumps({"confirmed": True, "reason": "x"}), content_type="application/json"),
    ]
    context.f14_invalid_responses = invalid


@then("server F14 menolak rekonsiliasi dan status pekerjaan serta run tidak berubah")
def f14_assert_invalid_reconcile(context):
    assert [r.status_code for r in context.f14_invalid_responses] == [400, 400]
    context.f14_job.refresh_from_db()
    context.f14_run.refresh_from_db()
    assert context.f14_job.status == ResyncJob.Status.RUNNING
    assert context.f14_run.status == SyncRun.Status.RUNNING
    assert context.f14_job.resolved_at is None and context.f14_run.finished_at is None


@given("Admin API F14 login dan pekerjaan BPS sintetis telah direkonsiliasi menjadi unknown")
def f14_reconciled_setup(context):
    _admin(context)
    _api(context)
    context.f14_source = _source()
    job = _running_job(context)
    job.status = ResyncJob.Status.UNKNOWN
    job.resolved_by = context.f14_admin
    job.resolved_at = timezone.now()
    job.resolution_reason = "SYNTHETIC BDD pemeriksaan manual worker fence."
    job.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_reason"])
    context.f14_run.status = SyncRun.Status.UNKNOWN
    context.f14_run.save(update_fields=["status"])
    context.f14_job = job
    context.f14_indicator = Indicator.objects.create(
        code="f14_worker_synthetic", name="SYNTHETIC F14 worker guard", category="Uji", unit="%",
    )
    context.f14_candidate_count = ObservationCandidate.objects.count()
    context.f14_indicator_count = Indicator.objects.count()


@when("worker lama F14 mencoba menulis metadata atau kandidat melalui jalur BPS yang dipagari")
def f14_stale_worker_write(context):
    from indicators import bps
    from indicators.lifecycle import stage_observation
    from indicators.resync_worker import JobFencedError, _job_write_guard

    failures = 0
    try:
        with _job_write_guard(context.f14_job.pk, context.f14_run.pk):
            bps._get_or_create_indicator(bps.BPS_SERIES[0])
    except JobFencedError:
        failures += 1
    try:
        with _job_write_guard(context.f14_job.pk, context.f14_run.pk):
            stage_observation(
                indicator_id=context.f14_indicator.pk,
                source_id=context.f14_source.pk,
                observation_date=date(2025, 1, 31), period_label="SYNTHETIC F14",
                frequency="monthly", data_type="yoy", value="1", unit="%",
            )
    except JobFencedError:
        failures += 1
    context.f14_write_result = {
        "fenced_writes": failures,
        "indicator_count_before": context.f14_indicator_count,
        "indicator_count_after": Indicator.objects.count(),
        "candidate_count_before": context.f14_candidate_count,
        "candidate_count_after": ObservationCandidate.objects.count(),
    }


@then("pagar worker F14 menolak penulisan dan tidak membuat kandidat baru")
def f14_assert_worker_fenced(context):
    assert context.f14_write_result["fenced_writes"] == 2
    assert context.f14_write_result["indicator_count_after"] == context.f14_write_result["indicator_count_before"]
    assert context.f14_write_result["candidate_count_after"] == context.f14_write_result["candidate_count_before"]
    assert ResyncJob.objects.get(pk=context.f14_job.pk).status == ResyncJob.Status.UNKNOWN


@then("hasil F14 tidak mengklaim request jaringan yang telah dikirim sudah dibatalkan")
def f14_no_claim_network_cancelled(context):
    assert "dibatalkan" not in context.f14_job.safe_message.lower()
    context.evidence["f14_network_boundary"] = "worker write fence checked; already-issued provider request is not claimed cancelled"


# ------------------------------ API: candidate/publication boundary

@given("Admin API F14 login dan tersedia nilai publik terakhir yang sudah direview")
def f14_published_baseline(context):
    from indicators import bps

    _admin(context)
    _api(context)
    context.f14_source = bps._get_or_create_source()
    context.f14_series = {
        "code": "f14_synthetic", "var_id": 9999, "name": "SYNTHETIC F14 indicator",
        "category": "Uji", "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
        "frequency": "monthly", "data_type": "yoy", "subperiods": {1: 1},
    }
    context.f14_indicator = bps._get_or_create_indicator(context.f14_series)
    context.f14_reviewer = get_user_model().objects.create_user(username="synthetic-f14-reviewer")
    context.f14_public = Observation.objects.create(
        indicator=context.f14_indicator, source=context.f14_source,
        observation_date=date(2025, 1, 31), period_label="SYNTHETIC F14 baseline",
        frequency="monthly", data_type="yoy", value="3.25", unit="%",
        validation_status=Observation.Status.PUBLISHED, reviewed_by=context.f14_reviewer,
        reviewed_at=timezone.now(),
    )


@when("sinkronisasi F14 menstage kandidat sintetis baru yang belum direview")
def f14_stage_candidate(context):
    from django.core.management import call_command
    from indicators import bps

    job = ResyncJob.objects.create(source=context.f14_source, requested_by=context.f14_admin, request_key=uuid.uuid4())
    point = {
        "observation_date": date(2025, 2, 28), "period_label": "SYNTHETIC F14 candidate",
        "frequency": "monthly", "data_type": "yoy", "value": Decimal("9.87"), "unit": "%",
    }
    with patch.object(bps, "BPS_SERIES", [context.f14_series]), patch.object(bps, "fetch_series", return_value=[point]) as fetch:
        call_command("process_resync", once=True)
    fetch.assert_called_once()
    job.refresh_from_db()
    assert job.status == ResyncJob.Status.SUCCESS
    context.f14_candidate = ObservationCandidate.objects.get(indicator=context.f14_indicator)


@then("nilai publik terakhir F14 tetap tersedia dan kandidat baru tidak dipublikasikan")
def f14_assert_candidate_private(context):
    context.f14_public.refresh_from_db()
    context.f14_candidate.refresh_from_db()
    assert context.f14_public.value == Decimal("3.25"), context.f14_public.value
    assert context.f14_public.validation_status == Observation.Status.PUBLISHED
    assert context.f14_candidate.status == ObservationCandidate.Status.PENDING
    assert not Observation.objects.filter(
        indicator=context.f14_indicator, observation_date=date(2025, 2, 28),
        validation_status=Observation.Status.PUBLISHED,
    ).exists()
    public = context.f14_api.get("/api/indicators/", {"code": context.f14_indicator.code})
    assert public.status_code == 200, public.content[:300]
    public_row = public.json()["indicators"][0]
    assert public_row["available"] is True
    assert public_row["value"] == "3.25" and public_row["period"] == "SYNTHETIC F14 baseline"
    context.evidence["f14_publication_boundary"] = {
        "public_value": public_row["value"], "candidate_status": context.f14_candidate.status,
        "public_api_status": public.status_code,
    }


# ------------------------------ API: anonymous rejection

@given("client anonim F14 dan sumber BPS sintetis aktif")
def f14_anonymous_setup(context):
    _source()
    _api(context, authenticated=False)


@when("pengunjung anonim F14 meminta sinkronisasi ulang")
def f14_anonymous_request(context):
    context.f14_response, _ = _request_job(context)


@then("server F14 menolak permintaan tanpa membuat pekerjaan")
def f14_anonymous_rejected(context):
    assert context.f14_response.status_code == 401, context.f14_response.content[:300]
    assert ResyncJob.objects.count() == 0
