"""F12/F13 bindings: synthetic fixtures, real Django views and real React browser.

Browser fault injection is limited to the isolated CDP session and is recorded as
synthetic. No provider is contacted; all database writes use the runner's disposable DB.
"""
import json
import secrets
import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from indicators.models import DataUpdateLog, Source, SourceRevision
from indicators.source_admin_views import _record_revision
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import begin_sync_run, finalize_sync_run
from journal import entries

SOURCE_ID = "SYNTHETIC_F12"
HISTORY_PATH = "/api/admin/sync-history/"


def _client(context, authenticated=True):
    client = Client(enforce_csrf_checks=True)
    if authenticated:
        user = get_user_model().objects.create_user(
            username=f"synthetic-sprint2-{timezone.now().timestamp()}-{id(context)}",
            email="synthetic-sprint2@example.test", is_staff=True,
        )
        client.force_login(user)
        context.sprint2_admin = user
    csrf = client.get("/api/auth/csrf/")
    assert csrf.status_code == 200, csrf.content[:200]
    client.defaults["HTTP_X_CSRFTOKEN"] = csrf.json()["csrfToken"]
    context.sprint2_client = client
    return client


def _source(status="active", source_id=SOURCE_ID, method="file_xlsx"):
    return Source.objects.update_or_create(source_id=source_id, defaults={
        "source_name": f"{source_id} synthetic fixture", "institution": "SYNTHETIC only",
        "primary_url": "https://example.test/synthetic", "acquisition_method": method,
        "data_format": "json" if method == "api_bps" else "xlsx",
        "endpoint_url": "https://example.test/synthetic-api" if method == "api_bps" else "",
        "frequency": "monthly", "update_schedule": "synthetic", "status": status,
    })[0]


def _revision(source, user):
    return _record_revision(source, SourceRevision.Action.CREATE, {}, user)


def _api_setup(context):
    return getattr(context, "sprint2_client", None) or _client(context)


def _history_rows(context, count=2, source_ids=None):
    SyncRun.objects.all().delete()
    source_ids = source_ids or ["SYNTHETIC_H1"] * count
    base = timezone.now().replace(microsecond=0) - timedelta(days=count + 1)
    rows = []
    for index in range(count):
        sid = source_ids[index] if index < len(source_ids) else "SYNTHETIC_H1"
        rows.append(SyncRun.objects.create(
            source_id_snapshot=sid, source_name_snapshot=f"{sid} synthetic",
            status=("success" if index % 2 == 0 else "failed"),
            started_at=base + timedelta(minutes=index),
            finished_at=base + timedelta(minutes=index, seconds=40) if index % 2 == 0 else None,
            actor=context.sprint2_admin, item_count=index + 1 if index % 2 == 0 else None,
            safe_message="SYNTHETIC fixture only",
        ))
    return rows


def _start_browser(context):
    context.execute_steps(
        "Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah "
        "dan periode Q1 2025 sudah direview dan dipublikasikan"
    )


def _browser_admin(context):
    _start_browser(context)
    password = secrets.token_urlsafe(24)
    context.sprint2_admin = get_user_model().objects.create_user(
        username=f"synthetic-sprint2-browser-{id(context)}", password=password, is_staff=True
    )
    b = context.browser
    b.call("Page.navigate", {"url": context.frontend_url + "/admin/login"})
    b.wait("Boolean(document.querySelector('#login-submit')) && !document.querySelector('#login-submit').disabled")
    b.type_text("#identifier", context.sprint2_admin.username)
    b.type_text("#password", password)
    b.click("#login-submit")
    b.wait("Boolean(document.querySelector('#admin-session'))")
    b.wait("location.pathname === '/admin/sumber' && document.readyState === 'complete'")
    b.wait("Boolean(document.querySelector('#admin-sources-title')) && !document.body.innerText.includes('Memeriksa sesi admin')")
    context.evidence["synthetic_admin_browser_session"] = True


def _browser_nav(context, path):
    b = context.browser
    prior = b.js("performance.timeOrigin")
    b.call("Page.navigate", {"url": context.frontend_url + path})
    b.wait(f"performance.timeOrigin > {prior}")
    b.wait("document.readyState === 'complete'")


def _make_run(context, source_id="SYNTHETIC_H1", status="success", started=None,
              finished=None, count=None):
    return SyncRun.objects.create(
        source_id_snapshot=source_id, source_name_snapshot=f"{source_id} synthetic",
        status=status, started_at=started or timezone.now(), finished_at=finished,
        actor=getattr(context, "sprint2_admin", None), item_count=count, safe_message="SYNTHETIC fixture only",
    )


# -------------------------- F12 browser status toggle -------------------------
@given("Admin masuk dan sumber sintetis aktif memiliki revisi 1")
def f12_active_browser(context):
    _browser_admin(context)
    context.f12_source = _source("active")
    _revision(context.f12_source, context.sprint2_admin)
    _browser_nav(context, "/admin/sumber")
    context.browser.wait(f"document.body.innerText.includes('{SOURCE_ID}')")


@when("Admin menonaktifkan sumber menggunakan revisi 1")
def f12_disable_browser(context):
    context.browser.click(f'button[aria-label="Nonaktifkan {SOURCE_ID} synthetic fixture"]')
    context.browser.wait("document.body.innerText.includes('berhasil diubah')")
    context.f12_browser_revisions_before = SourceRevision.objects.filter(source=context.f12_source).count()


@then("status sumber menjadi nonaktif dan revisi perubahan tersimpan")
def f12_disabled_saved(context):
    context.f12_source.refresh_from_db()
    assert context.f12_source.status == "inactive"
    revs = list(context.f12_source.revisions.order_by("version"))
    assert [r.version for r in revs] == [1, 2]
    assert revs[-1].after["status"] == "inactive"
    assert revs[-1].before["status"] == "active"
    context.evidence["source_revision"] = {"status": context.f12_source.status, "versions": [r.version for r in revs]}


@then("status nonaktif terlihat setelah daftar sumber dimuat ulang")
def f12_disabled_visible(context):
    context.browser.wait("document.body.innerText.includes('INACTIVE')")
    assert context.f12_source.status == "inactive"
    assert not context.browser.errors and not context.browser.blocked


@given("Admin masuk dan sumber sintetis nonaktif memiliki revisi 2")
def f12_inactive_browser(context):
    _browser_admin(context)
    context.f12_source = _source("inactive")
    _revision(context.f12_source, context.sprint2_admin)
    context.f12_source.description = "SYNTHETIC revisi kedua"
    context.f12_source.save(update_fields=["description"])
    _record_revision(context.f12_source, SourceRevision.Action.UPDATE,
                     {**_snapshot(context.f12_source), "description": ""}, context.sprint2_admin)
    _browser_nav(context, "/admin/sumber")
    context.browser.wait(f"document.body.innerText.includes('{SOURCE_ID}')")


def _snapshot(source):
    from indicators.models import source_config_snapshot
    return source_config_snapshot(source)


@when("Admin mengaktifkan sumber menggunakan revisi 2")
def f12_enable_browser(context):
    context.browser.click(f'button[aria-label="Aktifkan {SOURCE_ID} synthetic fixture"]')
    context.browser.wait("document.body.innerText.includes('berhasil diubah')")


@then("status sumber menjadi aktif dan revisi baru tercatat")
def f12_enabled_revision(context):
    context.f12_source.refresh_from_db()
    assert context.f12_source.status == "active"
    assert list(context.f12_source.revisions.order_by("version").values_list("version", flat=True)) == [1, 2, 3]
    assert context.f12_source.revisions.order_by("-version").first().after["status"] == "active"


# ----------------------------------- F12 API ----------------------------------
@given("Admin masuk dan sumber sintetis berada pada revisi 2")
def f12_rev2_api(context):
    user_client = _client(context)
    context.f12_source = _source("active")
    _revision(context.f12_source, context.sprint2_admin)
    context.f12_source.description = "SYNTHETIC revision 2"
    context.f12_source.save(update_fields=["description"])
    from indicators.models import source_config_snapshot
    _record_revision(context.f12_source, SourceRevision.Action.UPDATE,
                     {**source_config_snapshot(context.f12_source), "description": ""}, context.sprint2_admin)
    context.sprint2_client = user_client
    context.f12_before_status = context.f12_source.status
    context.f12_before_count = context.f12_source.revisions.count()


@when("Admin mengirim perubahan status tanpa expectedRevision")
def f12_missing_revision(context):
    context.response = _api_setup(context).put(
        f"/api/admin/sources/{SOURCE_ID}/update/", data=json.dumps({"status": "inactive"}),
        content_type="application/json")


@then("respons menyatakan permintaan tidak valid")
def f12_bad_request(context):
    assert context.response.status_code == 400, context.response.content[:300]


@then("status dan riwayat revisi tidak berubah")
def f12_no_revision_change(context):
    context.f12_source.refresh_from_db()
    assert context.f12_source.status == context.f12_before_status
    assert context.f12_source.revisions.count() == context.f12_before_count


@given("dua Admin membaca sumber sintetis pada revisi 2")
def f12_two_admins(context):
    f12_rev2_api(context)
    context.f12_admin2 = _client(type("Other", (), {})())
    context.f12_admin2.force_login(get_user_model().objects.create_user(
        username=f"synthetic-f12-second-{id(context)}", is_staff=True))
    context.f12_revision_seen = 2


@given("Admin pertama sudah menyimpan perubahan sehingga revisi menjadi 3")
def f12_first_admin_save(context):
    from indicators.models import source_config_snapshot
    source = context.f12_source
    before = source_config_snapshot(source)
    source.description = "SYNTHETIC first admin update"
    source.save(update_fields=["description"])
    _record_revision(source, SourceRevision.Action.UPDATE, before, context.sprint2_admin)
    context.f12_first_after = source.description


@when("Admin kedua mencoba mengganti status menggunakan revisi 2")
def f12_second_stale(context):
    context.response = context.f12_admin2.put(
        f"/api/admin/sources/{SOURCE_ID}/update/",
        data=json.dumps({"status": "inactive", "expectedRevision": context.f12_revision_seen}),
        content_type="application/json")


@then("server menolak perubahan dengan konflik revisi")
def f12_conflict(context):
    assert context.response.status_code == 409, context.response.content[:300]


@then("perubahan Admin pertama tetap tersimpan")
def f12_first_retained(context):
    context.f12_source.refresh_from_db()
    assert context.f12_source.description == context.f12_first_after and context.f12_source.status == "active"
    assert context.f12_source.revisions.order_by("-version").first().version == 3


@given("sumber sintetis nonaktif dan provider diganti dengan stub yang mencatat panggilan")
def f12_provider_fixture(context):
    _api_setup(context)
    context.f12_source = _source("inactive", "KEMENKEU")
    context.f12_provider = Mock(name="synthetic_provider")
    context.f12_runs_before = SyncRun.objects.count()
    context.f12_success_log_ids = set(DataUpdateLog.objects.filter(status="success").values_list("pk", flat=True))


@when("proses akuisisi baru untuk sumber tersebut dimulai")
def f12_start_acquisition(context):
    from django.core.management import call_command
    from indicators import fiscal

    with patch.object(fiscal, "ingest_kita_pdf_url", context.f12_provider):
        context.f12_command_output = __import__("io").StringIO()
        call_command("fetch_kemenkeu", url="https://example.test/SYNTHETIC.pdf",
                     stdout=context.f12_command_output, stderr=context.f12_command_output)
    context.f12_acquisition_output = context.f12_command_output.getvalue()


@then("proses tidak memanggil provider atau membuat run sinkronisasi baru")
def f12_skip_provider(context):
    assert context.f12_provider.call_count == 0
    assert SyncRun.objects.count() == context.f12_runs_before
    assert "tidak aktif" in context.f12_acquisition_output.lower()


@then("tidak ada catatan palsu bahwa sinkronisasi berhasil")
def f12_no_fake_success(context):
    assert not SyncRun.objects.filter(source_id_snapshot=context.f12_source.source_id, status="success").exists()
    assert set(DataUpdateLog.objects.filter(status="success").values_list("pk", flat=True)) == context.f12_success_log_ids


@given("pekerjaan sintetis sudah dimulai ketika sumber masih aktif")
def f12_running_job(context):
    _client(context)
    context.f12_source = _source("active", method="api_bps")
    context.f12_run = begin_sync_run(source=context.f12_source, actor=context.sprint2_admin)
    context.f12_job = None


@when("Admin menonaktifkan sumber")
def f12_disable_api(context):
    client = _api_setup(context)
    context.response = client.put(
        f"/api/admin/sources/{context.f12_source.source_id}/update/",
        data=json.dumps({"status": "inactive", "expectedRevision": 0}), content_type="application/json")
    assert context.response.status_code == 200, context.response.content[:300]
    context.f12_source.refresh_from_db()
    assert context.f12_source.status == "inactive"
    context.f12_runs_before_request = SyncRun.objects.count()
    # A new explicit request is refused by the actual resync endpoint once inactive.
    context.f12_resync_response = client.post(
        f"/api/admin/sources/{context.f12_source.source_id}/resync/",
        data=json.dumps({"requestId": str(uuid.uuid4())}), content_type="application/json")



@then("tidak ada pekerjaan baru dimulai untuk sumber nonaktif")
def f12_no_new_work(context):
    assert context.f12_resync_response.status_code == 409, context.f12_resync_response.content[:300]
    assert "tidak aktif" in context.f12_resync_response.json()["error"].lower()
    assert SyncRun.objects.count() == context.f12_runs_before_request
    assert context.f12_source.status == "inactive"


@then("status pekerjaan yang sudah dimulai mengikuti hasilnya sendiri")
def f12_existing_run_independent(context):
    context.f12_run.refresh_from_db()
    assert context.f12_run.status == "running"
    finalize_sync_run(context.f12_run, success=True)
    context.f12_run.refresh_from_db()
    assert context.f12_run.status == "success" and context.f12_source.status == "inactive"
    context.evidence["running_job_boundary"] = "existing SyncRun finalized independently; inactive source blocked new resync request"


@given("pengunjung tanpa sesi Admin dan sumber sintetis aktif")
def f12_anonymous_source(context):
    context.sprint2_client = _client(context, authenticated=False)
    context.f12_source = _source("active")
    context.f12_before_count = context.f12_source.revisions.count()


@when("pengunjung mengirim perubahan status")
def f12_anon_update(context):
    context.response = context.sprint2_client.put(
        f"/api/admin/sources/{SOURCE_ID}/update/",
        data=json.dumps({"status": "inactive", "expectedRevision": 0}), content_type="application/json")


@then("server menolak perubahan dan status tetap aktif")
def f12_anon_rejected(context):
    context.f12_source.refresh_from_db()
    assert context.response.status_code == 401 and context.f12_source.status == "active"


@given("Admin menonaktifkan sumber dan server mengonfirmasi penyimpanan")
def f12_save_before_reload_fault(context):
    _browser_admin(context)
    context.f12_source = _source("active")
    _revision(context.f12_source, context.sprint2_admin)
    _browser_nav(context, "/admin/sumber")
    context.browser.wait(f"document.body.innerText.includes('{SOURCE_ID}')")
    context.f12_puts_before = len([r for r in context.browser.requests if r["url"].endswith("/update/")])
    # Narrowly fail exactly the list GET after allowing detail + status PUT through.
    context.browser.js("""(()=>{
      const original=window.fetch.bind(window);
      window.fetch=(input,init={})=>{
        const url=new URL(typeof input==='string'?input:input.url,location.href);
        if(url.pathname==='/api/admin/sources/' && (init.method||'GET').toUpperCase()==='GET')
          return Promise.reject(new TypeError('SYNTHETIC list-refresh fault'));
        return original(input,init);
      };
    })()""")
    context.evidence["fault_injection"] = "browser fetch wrapper fails only GET /api/admin/sources/; detail, status PUT, and all other traffic remain live"
    context.browser.click(f'button[aria-label="Nonaktifkan {SOURCE_ID} synthetic fixture"]')
    context.browser.wait("document.body.innerText.includes('berhasil diubah')")
    context.f12_source.refresh_from_db()
    assert context.f12_source.status == "inactive"


@when("permintaan berikutnya untuk memuat daftar gagal")
def f12_list_refresh_fails(context):
    context.browser.wait("document.body.innerText.includes('SYNTHETIC list-refresh fault')")


@then("pengguna diberi tahu bahwa penyimpanan dan pembaruan tampilan memiliki hasil berbeda")
def f12_save_vs_view(context):
    context.f12_source.refresh_from_db()
    assert context.f12_source.status == "inactive"
    body = context.browser.js("document.body.innerText")
    assert "berhasil diubah" in body and "SYNTHETIC list-refresh fault" in body, body


@then("aplikasi tidak otomatis mengirim ulang perubahan status")
def f12_no_retry(context):
    put_count = len([r for r in context.browser.requests if r["url"].endswith("/update/")])
    assert put_count == context.f12_puts_before + 1


# ------------------------------ F13 API cases --------------------------------
@given("jumlah run sintetis lebih besar daripada ukuran satu halaman")
def f13_pagination_fixture(context):
    _client(context)
    _history_rows(context, 5)
    context.f13_total_before = SyncRun.objects.count()


@when("Admin membaca halaman pertama lalu halaman kedua dengan filter yang sama")
def f13_fetch_two_pages(context):
    client = _api_setup(context)
    context.f13_page1 = client.get(HISTORY_PATH, {"page": 1, "pageSize": 2})
    context.f13_page2 = client.get(HISTORY_PATH, {"page": 2, "pageSize": 2})


@then("masing-masing halaman mengikuti urutan waktu mulai terbaru")
def f13_ordered_pages(context):
    assert context.f13_page1.status_code == context.f13_page2.status_code == 200
    for response in (context.f13_page1, context.f13_page2):
        dates = [item["startedAt"] for item in response.json()["items"]]
        assert dates == sorted(dates, reverse=True), dates


@then("ID run yang sama tidak muncul di kedua halaman untuk dataset yang tidak berubah")
def f13_no_duplicate_pages(context):
    ids = [x["id"] for response in (context.f13_page1, context.f13_page2) for x in response.json()["items"]]
    assert len(ids) == len(set(ids)) == 4


@given("pengunjung tidak memiliki sesi Admin")
def f13_anonymous(context):
    context.sprint2_client = _client(context, authenticated=False)
    _make_run(context)


@when("pengunjung meminta riwayat sinkronisasi")
def f13_anonymous_request(context):
    context.response = context.sprint2_client.get(HISTORY_PATH)


@then("server menolak akses tanpa memberikan daftar run")
def f13_anonymous_denied(context):
    assert context.response.status_code == 401
    assert "items" not in context.response.json()


@given("Admin masuk")
def f13_admin_login_api(context):
    _client(context)
    _make_run(context)


@when("Admin meminta riwayat dengan status atau nomor halaman yang tidak valid")
def f13_bad_params(context):
    count = SyncRun.objects.count()
    client = _api_setup(context)
    context.f13_invalid = [client.get(HISTORY_PATH, {"status": "future"}), client.get(HISTORY_PATH, {"page": 0})]
    context.f13_count_before = count


@then("server menolak parameter tanpa mengubah run")
def f13_params_rejected(context):
    assert [r.status_code for r in context.f13_invalid] == [400, 400]
    assert SyncRun.objects.count() == context.f13_count_before


@given("terdapat log lama sintetis yang jenis peristiwanya tidak dapat dipastikan")
def f13_ambiguous_log(context):
    _client(context)
    SyncRun.objects.all().delete()
    DataUpdateLog.objects.create(source="SYNTHETIC legacy ambiguous", status="success",
                                 event_kind=DataUpdateLog.EventKind.UNKNOWN,
                                 observation_count=7, message="SYNTHETIC ambiguous legacy log")


@given("tidak ada run sinkronisasi terkait")
def f13_no_sync_run(context):
    assert not SyncRun.objects.exists()


@when("Admin meminta riwayat sinkronisasi")
def f13_request_history(context):
    context.response = _api_setup(context).get(HISTORY_PATH)


@then("log ambigu tidak disajikan sebagai run atau keberhasilan sinkronisasi")
def f13_ambiguous_excluded(context):
    assert context.response.status_code == 200
    assert context.response.json()["items"] == []
    assert DataUpdateLog.objects.filter(event_kind=DataUpdateLog.EventKind.UNKNOWN).exists()


# ---------------------------- F13 browser cases ------------------------------
@given("Admin masuk dan ada dua run sintetis dengan waktu mulai berbeda")
def f13_browser_two_runs(context):
    _browser_admin(context)
    base = timezone.now().replace(microsecond=0) - timedelta(hours=2)
    context.f13_old = _make_run(context, "SYNTHETIC_OLD", "failed", base, None, None)
    context.f13_new = _make_run(context, "SYNTHETIC_NEW", "success", base + timedelta(hours=1), base + timedelta(hours=1, minutes=1), 4)


@when("Admin membuka halaman riwayat sinkronisasi")
def f13_browser_open(context):
    _browser_nav(context, "/admin/riwayat-sinkronisasi")
    context.browser.wait("Boolean(document.querySelector('.sync-history__table'))")
    context.browser.wait("document.body.innerText.includes('SYNTHETIC_NEW')")


@then("run ditampilkan dari yang terbaru beserta sumber status dan waktu mulai")
def f13_browser_latest(context):
    rows = context.browser.js("Array.from(document.querySelectorAll('.sync-history__row')).map(r=>r.innerText)")
    assert len(rows) >= 2 and "SYNTHETIC_NEW" in rows[0] and "SYNTHETIC_OLD" in rows[1], rows
    assert "Berhasil" in rows[0] and "Gagal" in rows[1]
    assert context.f13_new.started_at.isoformat()[:10] in rows[0]


@then("waktu selesai dan jumlah hanya ditampilkan jika memang tersedia")
def f13_optional_fields(context):
    rows = context.browser.js("Array.from(document.querySelectorAll('.sync-history__row')).map(r=>r.innerText)")
    assert "4" in rows[0]
    assert "Tidak tersedia" in rows[1]


@given("riwayat sintetis berisi beberapa sumber dan status")
def f13_filter_fixture(context):
    _browser_admin(context)
    base = timezone.now().replace(microsecond=0) - timedelta(hours=3)
    _make_run(context, "SYNTHETIC_FILTER_A", "success", base, base + timedelta(minutes=1), 1)
    _make_run(context, "SYNTHETIC_FILTER_B", "failed", base + timedelta(hours=1), None, None)
    _browser_nav(context, "/admin/riwayat-sinkronisasi")
    context.browser.wait("document.querySelectorAll('.sync-history__row').length >= 2")


@when("Admin memilih satu sumber dan satu status")
def f13_apply_filters(context):
    b = context.browser
    b.type_text("#sync-source", "SYNTHETIC_FILTER_A")
    b.click(".sync-history__filters button[type=submit]")
    b.wait("document.querySelectorAll('.sync-history__row').length === 1")
    b.js("(()=>{const e=document.querySelector('#sync-status');e.value='success';e.dispatchEvent(new Event('change',{bubbles:true}))})()")
    b.wait("document.querySelectorAll('.sync-history__row').length === 1")


@then("hanya run yang cocok dengan kedua filter yang tampil")
def f13_filtered_only(context):
    rows = context.browser.js("Array.from(document.querySelectorAll('.sync-history__row')).map(r=>r.innerText)")
    assert len(rows) == 1 and "SYNTHETIC_FILTER_A" in rows[0] and "Berhasil" in rows[0]


@given("Admin masuk dan tidak ada run yang cocok dengan filter")
def f13_browser_empty(context):
    _browser_admin(context)
    SyncRun.objects.all().delete()


@when("Admin membuka riwayat dengan filter tersebut")
def f13_open_empty(context):
    _browser_nav(context, "/admin/riwayat-sinkronisasi")
    context.browser.wait("location.pathname === '/admin/riwayat-sinkronisasi' && document.readyState === 'complete'")
    context.browser.wait("Boolean(document.querySelector('#sync-history-title'))")
    context.browser.wait("document.querySelector('.sync-history__connection')?.textContent === 'Data dimuat'")
    context.browser.wait("document.body.innerText.includes('Belum ada riwayat')")


@then("halaman menampilkan kondisi kosong tanpa menciptakan run atau angka")
def f13_empty_visible(context):
    assert SyncRun.objects.count() == 0
    body = context.browser.js("document.body.innerText")
    assert "Belum ada riwayat" in body and "0 catatan" in body
    assert context.browser.js("document.querySelectorAll('.sync-history__row').length") == 0
    assert any(row["path"] == HISTORY_PATH and row["status"] == 200 for row in entries)


@given("Admin masuk dan permintaan riwayat menghasilkan kegagalan server sintetis")
def f13_browser_fault(context):
    _browser_admin(context)
    _make_run(context, "SYNTHETIC_MUST_NOT_APPEAR", "success")
    context.browser.rules = [{"match": "/api/admin/sync-history/", "action": "503"}]


@when("Admin membuka riwayat")
def f13_open_failed(context):
    _browser_nav(context, "/admin/riwayat-sinkronisasi")
    context.browser.wait("document.body.innerText.includes('Riwayat tidak dapat dimuat')")


@then("halaman menampilkan kesalahan dan menyediakan cara mencoba lagi")
def f13_error_retry(context):
    assert context.browser.js("Boolean(Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Coba lagi')))")


@then("tidak menampilkan data contoh sebagai riwayat nyata")
def f13_no_fake_rows(context):
    assert context.browser.js("document.querySelectorAll('.sync-history__row').length") == 0
    assert "SYNTHETIC_MUST_NOT_APPEAR" not in context.browser.js("document.body.innerText")


@given("Admin berada pada halaman riwayat sinkronisasi")
def f13_at_history(context):
    _browser_admin(context)
    _browser_nav(context, "/admin/riwayat-sinkronisasi")
    context.browser.wait("Boolean(document.querySelector('.sync-history__back'))")


@when("Admin memilih tautan Kelola Sumber Data")
def f13_back_sources(context):
    context.browser.click(".sync-history__back")
    context.browser.wait("location.pathname === '/admin/sumber' && document.readyState === 'complete'")
    context.browser.wait("Boolean(document.querySelector('#admin-sources-title'))")
    context.browser.wait("document.body.innerText.includes('Kelola Sumber Data')")


@then("halaman Kelola Sumber terbuka dengan sesi Admin yang sama")
def f13_same_session(context):
    assert context.browser.js("document.body.innerText.includes('Kelola Sumber Data')")
    state = context.browser.js("fetch('/api/admin/session/',{credentials:'same-origin'}).then(r=>r.json())")
    assert state["authenticated"] is True and state["username"] == context.sprint2_admin.username, state
    assert not context.browser.errors and not context.browser.blocked
