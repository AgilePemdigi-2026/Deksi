"""Independent API BDD slices; all mutations are restricted to the disposable DB."""
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json

from pathlib import Path
from unittest.mock import patch


from behave import given, when, then
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator, PasswordResetTokenGenerator
from django.core import mail
from django.test import Client, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from indicators.models import Indicator, Observation, Source, RawFile, DataUpdateLog
from indicators.feedback_model import Feedback

PASSWORD = "SYNTHETIC-Bdd-Original-9472!"
NEW_PASSWORD = "SYNTHETIC-Bdd-Changed-5829!"


def user(context, staff=True):
    context.client = Client(enforce_csrf_checks=True)
    context.user = get_user_model().objects.create_user(
        username="synthetic-bdd-admin", email="synthetic-bdd@example.test",
        password=PASSWORD, is_staff=staff,
    )


def csrf(context):
    response = context.client.get("/api/auth/csrf/")
    assert response.status_code == 200
    return response.json()["csrfToken"]


def post(context, path, payload, token=None):
    return context.client.post(path, data=json.dumps(payload), content_type="application/json",
                               **({"HTTP_X_CSRFTOKEN": token} if token else {}))


def login(context):
    response = post(context, "/api/auth/login/", {"identifier": context.user.username, "password": PASSWORD}, csrf(context))
    assert response.status_code == 200, response.status_code
    return response.json()["csrfToken"]


@given("akun sintetis aktif tanpa role staff dan cookie CSRF yang valid")
def nonstaff(context):
    user(context, staff=False)
    context.token = csrf(context)


@when("client mengirim kredensial akun itu ke endpoint Login")
def reject_nonstaff(context):
    context.response = post(context, "/api/auth/login/", {"identifier": context.user.username, "password": PASSWORD}, context.token)


@then("respons berstatus 401 dengan code invalid_credentials dan sesi Admin tidak terbentuk")
def assert_nonstaff(context):
    assert context.response.status_code == 401
    assert context.response.json()["code"] == "invalid_credentials"
    assert context.client.get("/api/auth/session/").json()["authenticated"] is False


@given("akun uji dan IP uji terisolasi dengan lima kegagalan Login pada jendela limiter aktif")
def five_failures(context):
    user(context)
    context.token = csrf(context)
    for _ in range(5):
        r = post(context, "/api/auth/login/", {"identifier": context.user.username, "password": "SYNTHETIC-WRONG"}, context.token)
        assert r.status_code in (401, 429)


@when("client mencoba Login lagi sebelum cooloff berakhir")
def try_locked(context):
    context.response = post(context, "/api/auth/login/", {"identifier": context.user.username, "password": PASSWORD}, context.token)


@then("respons berstatus 429 dengan code rate_limited tanpa membuat sesi Admin")
def assert_locked(context):
    assert context.response.status_code == 429
    assert context.response.json()["code"] == "rate_limited"
    assert context.client.get("/api/auth/session/").json()["authenticated"] is False


@given("sesi Admin sintetis sudah melewati expiry absolut delapan jam memakai jam uji terkontrol")
def expired_session(context):
    user(context)
    login(context)
    context.future = timezone.now() + timedelta(hours=8, seconds=1)


@when("client meminta status sesi")
def check_expiry(context):
    with patch("django.utils.timezone.now", return_value=context.future):
        context.response = context.client.get("/api/auth/session/")


@then("respons menyatakan authenticated false dan user null tanpa memperpanjang sesi")
def assert_expiry(context):
    assert context.response.status_code == 200
    body = context.response.json()
    assert body["authenticated"] is False and body["user"] is None


@given("client anonim belum mempunyai pasangan cookie dan header CSRF yang valid")
def no_csrf(context):
    user(context)


@when("client mengirim POST Login dengan kredensial uji valid")
def login_without_csrf(context):
    context.response = post(context, "/api/auth/login/", {"identifier": context.user.username, "password": PASSWORD})


@then("server merespons 403 dan tidak membentuk sesi Admin")
def assert_login_csrf(context):
    assert context.response.status_code == 403
    assert context.client.get("/api/auth/session/").json()["authenticated"] is False


@given("mailer locmem dan akun Admin sintetis unik tersedia pada settings uji")
def reset_fixture(context):
    user(context)
    context.token = csrf(context)
    assert settings.MAILERS["default"]["BACKEND"] == "django.core.mail.backends.locmem.EmailBackend"


@when("client mengirim permintaan reset untuk email akun lalu email sintetis yang tidak dikenal dengan CSRF valid")
def request_known_unknown(context):
    context.responses = [post(context, "/api/auth/password-reset/request/", {"email": value}, context.token)
                         for value in (context.user.email, "unknown-synthetic@example.test")]


@then("kedua respons berstatus 202 dengan reset_request_accepted tanpa mengungkap keberadaan akun")
def assert_generic_reset(context):
    assert [r.status_code for r in context.responses] == [202, 202]
    assert context.responses[0].json() == context.responses[1].json()
    assert context.responses[0].json()["code"] == "reset_request_accepted"
    assert len(mail.outbox) == 1


def capability(account):
    return {"uid": urlsafe_base64_encode(force_bytes(account.pk)), "token": default_token_generator.make_token(account)}


@given("tersedia token reset yang sudah lewat timeout kandidat dan token lain yang telah dipakai sukses")
def expired_used_tokens(context):
    reset_fixture(context)
    old_time = datetime.now() - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 2)
    with patch.object(PasswordResetTokenGenerator, "_now", return_value=old_time):
        old = capability(context.user)
    other = get_user_model().objects.create_user(username="synthetic-second", email="second@example.test", password=PASSWORD, is_staff=True)
    used = capability(other)
    response = post(context, "/api/auth/password-reset/confirm/", {**used, "newPassword": NEW_PASSWORD, "confirmPassword": NEW_PASSWORD}, context.token)
    assert response.status_code == 200
    context.capabilities = [old, used]
    context.hashes = {u.pk: get_user_model().objects.get(pk=u.pk).password for u in (context.user, other)}


@when("client mengonfirmasi reset menggunakan masing-masing token")
def confirm_bad_tokens(context):
    context.responses = [post(context, "/api/auth/password-reset/confirm/", {**cap, "newPassword": NEW_PASSWORD, "confirmPassword": NEW_PASSWORD}, context.token)
                         for cap in context.capabilities]


@then("kedua request ditolak sebagai invalid_reset_link dan hash password tidak berubah")
def assert_invalid_tokens(context):
    assert all(r.status_code == 400 and r.json()["code"] == "invalid_reset_link" for r in context.responses)
    assert all(get_user_model().objects.get(pk=pk).password == digest for pk, digest in context.hashes.items())


@given("token valid dan password baru yang ditolak validator kandidat tersedia")
def weak_password(context):
    reset_fixture(context)
    context.cap = capability(context.user)


@when("client mengonfirmasi reset dengan CSRF valid")
def weak_confirm(context):
    context.response = post(context, "/api/auth/password-reset/confirm/", {**context.cap, "newPassword": "123", "confirmPassword": "123"}, context.token)


@then("respons berstatus 400 dengan password_validation_failed dan password lama tetap berlaku")
def assert_weak(context):
    assert context.response.status_code == 400
    assert context.response.json()["code"] == "password_validation_failed"
    context.user.refresh_from_db()
    assert context.user.check_password(PASSWORD)


@given("reset disabled pada konfigurasi yang dipilih untuk skenario uji")
def reset_disabled(context):
    reset_fixture(context)


@when("client mengirim permintaan reset dengan payload dan CSRF valid")
def disabled_request(context):
    context.outbox_before = len(getattr(mail, "outbox", []))
    with override_settings(ADMIN_PASSWORD_RESET_ENABLED=False):
        context.response = post(context, "/api/auth/password-reset/request/", {"email": context.user.email}, context.token)


@then("respons berstatus 503 dengan reset_unavailable dan outbox locmem tidak bertambah")
def assert_disabled(context):
    assert context.response.status_code == 503
    assert context.response.json()["code"] == "reset_unavailable"
    assert len(getattr(mail, "outbox", [])) == context.outbox_before


def indicator(context, code="inflasi", value="3", day=date(2025, 1, 31), unit="%", **extra):
    context.client = Client(enforce_csrf_checks=True)
    context.reviewer = get_user_model().objects.create_user(username="SYNTHETIC-reviewer", is_staff=True)
    context.source = Source.objects.create(source_id="SYNTHETIC_API", source_name="SYNTHETIC dataset", institution="SYNTHETIC institution", primary_url="https://example.test/synthetic")
    context.indicator = Indicator.objects.create(code=code, name=f"SYNTHETIC {code}", category="Inflasi" if code == "inflasi" else "PDB", unit=unit)
    context.observation = Observation.objects.create(indicator=context.indicator, source=context.source,
        observation_date=day, period_label=f"SYNTHETIC {day.isoformat()}", frequency="monthly", data_type="yoy", value=value,
        unit=unit, validation_status="published", reviewed_by=context.reviewer, reviewed_at=timezone.now(), **extra)


def add_observation(context, day, value, **extra):
    fields = dict(indicator=context.indicator, source=context.source, observation_date=day, period_label=f"SYNTHETIC {day.isoformat()}",
                  frequency=context.observation.frequency, data_type=context.observation.data_type, value=value,
                  unit=context.observation.unit, validation_status="published", reviewed_by=context.reviewer, reviewed_at=timezone.now())
    fields.update(extra)
    return Observation.objects.create(**fields)


@given("observasi terpilih mempunyai source unit frequency dan dataType yang diketahui fixture")
def comparable(context):
    indicator(context)
    add_observation(context, date(2024, 12, 31), "2", period_label="SYNTHETIC COMPARISON")


@then("nilai serta metadata dan pembanding berasal dari konteks pengukuran fixture yang sebanding")
def assert_metadata(context):
    row = context.response.json()["indicators"][0]
    assert row["sourceId"] == "SYNTHETIC_API" and row["frequency"] == "monthly" and row["dataType"] == "yoy"
    assert row["unit"] == "%" and Decimal(row["value"]) == Decimal("3")
    assert row["previousPeriod"] == "SYNTHETIC COMPARISON" and Decimal(row["changeValue"]) == Decimal("1")


@given("tersedia observasi reviewed-published A dan percobaan pembaruan gagal setelahnya pada fixture log")
def last_valid(context):
    indicator(context)
    DataUpdateLog.objects.all().delete()  # Disposable fixture only; remove unrelated seed log.
    moment = timezone.now()
    DataUpdateLog.objects.create(updated_at=moment - timedelta(hours=1), source="SYNTHETIC-success", status="success", observation_count=1)
    DataUpdateLog.objects.create(updated_at=moment, source="SYNTHETIC-failed", status="failed", message="SYNTHETIC provider failure, no network")


@when("client meminta ringkasan dan status pembaruan tersimpan")
def read_last_valid(context):
    context.summary = context.client.get("/api/indicators/?code=inflasi")
    context.update = context.client.get("/api/system/update-status/")


@then("nilai tetap berasal dari A dan metadata membedakan percobaan gagal dari waktu sukses terakhir")
def assert_last_valid(context):
    assert context.summary.status_code == context.update.status_code == 200
    assert Decimal(context.summary.json()["indicators"][0]["value"]) == Decimal("3")
    body = context.update.json()
    assert body["lastSuccessful"]["status"] == "success" and body["lastAttempt"]["status"] == "failed"
    assert body["lastSuccessful"]["updatedAt"] != body["lastAttempt"]["updatedAt"]


@given("seri uji memiliki exactValue 123456789012345.6789 dan metadata sumber unit tanggal frequency serta dataType")
def exact_history(context):
    indicator(context, value="123456789012345.6789")


@when("client meminta histori native indikator")
def native_history(context):
    context.response = context.client.get("/api/indicators/inflasi/trend/")


@then("payload mempertahankan exactValue dan metadata tersebut tanpa mengandalkan angka koordinat aproksimasi sebagai nilai exact")
def assert_exact(context):
    assert context.response.status_code == 200
    row = context.response.json()["points"][0]
    assert Decimal(row["exactValue"]) == Decimal("123456789012345.6789")
    assert row["sourceId"] == "SYNTHETIC_API" and row["frequency"] == "monthly" and row["dataType"] == "yoy"
    assert row["unit"] == "%" and row["observationDate"] == "2025-01-31"


@given("fixture komparabel mempunyai dua nilai 10 dan 20 pada tahun yang sama dengan aggregation_kind sum")
def aggregation(context):
    indicator(context, value="10", unit="triliun rupiah")
    context.observation.data_type = "level"
    context.observation.save()
    context.indicator.aggregation_kind = "sum"
    context.indicator.save()
    add_observation(context, date(2025, 2, 28), "20")


@when("client meminta histori Tahunan")
def annual(context):
    context.response = context.client.get("/api/indicators/inflasi/trend/", {"granularity": "Tahunan"})


@then("nilai exact agregasi adalah 30 dan metode dijelaskan sebagai jumlah tanpa pemanggilan AI")
def assert_sum(context):
    assert context.response.status_code == 200
    body = context.response.json()
    assert len(body["points"]) == 1 and Decimal(body["points"][0]["exactValue"]) == Decimal("30")
    assert "jumlah" in body["note"].lower()


@given("fixture inflasi memiliki nilai 2.50 tahun 2024 dan 3.00 tahun 2025 dengan review publik lengkap")
def yearly(context):
    indicator(context, value="3.00")
    add_observation(context, date(2024, 1, 31), "2.50")


@when("client meminta dashboard kategori Inflasi untuk tahun 2024")
def select_2024(context):
    context.response = context.client.get("/api/indicators/dashboard/", {"category": "Inflasi", "year": "2024"})


@then("kartu menampilkan 2.50 dengan metadata tahun 2024 dan activeFilters year 2024")
def assert_year(context):
    assert context.response.status_code == 200
    body = context.response.json()
    assert body["activeFilters"]["year"] == 2024
    row = body["indicators"][0]
    assert Decimal(row["value"]) == Decimal("2.50") and row["observationDate"] == "2024-01-31"


@given("indikator uji hanya memiliki observasi reviewed-published tahun 2025")
def only_2025(context):
    indicator(context)


@when("client meminta dashboard tahun 2024")
def unavailable_2024(context):
    context.response = context.client.get("/api/indicators/dashboard/", {"code": "inflasi", "year": "2024"})


@then("kartu menyatakan available false dan value null bukan angka dari tahun 2025")
def assert_no_fallback(context):
    assert context.response.status_code == 200
    row = context.response.json()["indicators"][0]
    assert row["available"] is False and row["value"] is None


@given("client menggunakan parameter year bernilai 0 lalu 10000 pada request yang terpisah")
def invalid_years(context):
    context.client = Client(enforce_csrf_checks=True)
    context.paths = ["/api/indicators/dashboard/?year=0", "/api/indicators/dashboard/?year=10000"]


@given("tersedia request kategori tidak dikenal serta request dengan dua parameter year")
def invalid_queries(context):
    context.client = Client(enforce_csrf_checks=True)
    context.paths = ["/api/indicators/dashboard/?category=UNKNOWN_SYNTHETIC", "/api/indicators/dashboard/?year=2024&year=2025"]


@when("client meminta dashboard untuk setiap nilai tersebut")
@when("client mengirim masing-masing request filter")
def invalid_filters(context):
    context.responses = [context.client.get(path) for path in context.paths]


@then("setiap respons berstatus 400 tanpa error internal dan tanpa data tahun alternatif")
@then("setiap respons berstatus 400 dan tidak diam-diam memilih nilai parameter terakhir")
def assert_invalid_filter(context):
    assert [r.status_code for r in context.responses] == [400, 400]
    assert all("indicators" not in r.json() for r in context.responses)


@given("observasi publik A dan B tersedia dengan empat selector berbeda dan B lebih baru")
def trace_pair(context):
    indicator(context, day=date(2024, 1, 31), value="2.50")
    add_observation(context, date(2025, 1, 31), "3.00")
    context.selector = {"observationDate": "2024-01-31", "frequency": "monthly", "dataType": "yoy", "sourceId": "SYNTHETIC_API"}


@when("client meminta Source Trace menggunakan selector lengkap A")
def select_trace(context):
    context.response = context.client.get("/api/indicators/inflasi/source-trace/", context.selector)


@then("nilai sumber dan periode berasal dari A meskipun B lebih baru")
def assert_old_trace(context):
    assert context.response.status_code == 200
    body = context.response.json()
    assert Decimal(body["value"]) == Decimal("2.50") and body["observationDate"] == "2024-01-31"
    assert body["source"]["sourceId"] == "SYNTHETIC_API"


@given("hanya observationDate dari selector A diberikan tanpa frequency dataType dan sourceId")
def partial_trace(context):
    indicator(context)
    context.selector = {"observationDate": "2025-01-31"}


@when("client meminta Source Trace")
def request_partial_trace(context):
    select_trace(context)


@then("respons berstatus 400 dan tidak mengembalikan trace terbaru sebagai pengganti")
def assert_partial_trace(context):
    assert context.response.status_code == 400 and "value" not in context.response.json()


@given("berkas RAW sintetis terkait observasi publik tetapi byte-nya tidak cocok checksum tersimpan")
def corrupt_raw(context):
    indicator(context)
    path = Path(settings.DEKSI_RAW_DIR) / "SYNTHETIC.raw"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"SYNTHETIC CORRUPT")
    raw = RawFile.objects.create(source=context.source, document_name="SYNTHETIC.raw", stored_path=str(path),
        checksum_sha256=hashlib.sha256(b"SYNTHETIC CORRECT").hexdigest(), file_size_bytes=path.stat().st_size)
    context.observation.raw_file = raw
    context.observation.save()
    context.raw = raw


@when("client meminta download RAW tersebut")
def raw_download(context):
    context.response = context.client.get(f"/api/indicators/inflasi/raw-file/{context.raw.pk}/")


@then("respons menolak pengiriman byte dengan status 503 dan tidak melakukan request URL sumber eksternal")
def assert_raw_corrupt(context):
    try:
        assert context.response.status_code == 503 and not context.response.streaming
        assert b"SYNTHETIC CORRUPT" not in context.response.content
    finally:
        context.response.close()


def feedback(context):
    context.client = Client(enforce_csrf_checks=True)
    context.payload = {"category": "other", "description": "SYNTHETIC BDD feedback only"}
    response = context.client.get("/api/feedback/categories/")
    assert response.status_code == 200
    context.token = response.json()["csrfToken"]


@given("payload feedback valid menyertakan status resolved dan admin_notes dari pengirim anonim")
def spoof_status(context):
    feedback(context)
    context.payload.update(status="resolved", admin_notes="SYNTHETIC attacker status")


@when("client mengirim feedback dengan CSRF valid")
@when("client mengirim feedback")
def send_feedback(context):
    context.response = post(context, "/api/feedback/", context.payload, context.token)


@then("record tersimpan pending dengan admin_notes kosong dan respons tidak mengungkap catatan Admin")
def assert_pending(context):
    assert context.response.status_code == 201
    record = Feedback.objects.get(pk=context.response.json()["id"])
    assert record.status == "pending" and record.admin_notes == ""
    assert "admin_notes" not in context.response.json()


@given("fixture request memakai kategori valid dengan deskripsi setelah trim sepanjang 9 lalu 10 lalu 2000 lalu 2001 karakter")
def description_lengths(context):
    feedback(context)


@when("client mengirim keempat request secara terpisah dengan CSRF valid")
def send_lengths(context):
    context.results = []
    for length in [9, 10, 2000, 2001]:
        before = Feedback.objects.count()
        response = post(context, "/api/feedback/", {"category": "other", "description": "S" * length}, context.token)
        context.results.append((response.status_code, Feedback.objects.count() - before))


@then("panjang 9 dan 2001 ditolak 400 tanpa row baru sedangkan 10 dan 2000 diterima 201")
def assert_lengths(context):
    assert context.results == [(400, 0), (201, 1), (201, 1), (400, 0)], context.results


@given("payload feedback valid dikirim tanpa pasangan cookie dan header CSRF")
def feedback_no_token(context):
    context.client = Client(enforce_csrf_checks=True)
    context.payload = {"category": "other", "description": "SYNTHETIC no CSRF feedback"}
    context.before_count = Feedback.objects.count()


@when("client melakukan POST feedback")
def send_no_token(context):
    context.response = post(context, "/api/feedback/", context.payload)


@then("respons berstatus 403 dan jumlah record feedback tidak bertambah")
def assert_feedback_csrf(context):
    assert context.response.status_code == 403 and Feedback.objects.count() == context.before_count


@given("request feedback memakai JSON dengan key duplikat atau field description bertipe array")
def malformed_feedback(context):
    feedback(context)
    context.bad_bodies = ['{"category":"other","category":"source","description":"SYNTHETIC BDD"}', '{"category":"other","description":[]}']


@when("client mengirim masing-masing payload dengan CSRF valid")
def send_malformed(context):
    context.responses = [context.client.post("/api/feedback/", data=body, content_type="application/json", HTTP_X_CSRFTOKEN=context.token) for body in context.bad_bodies]


@then("respons berstatus 400 tanpa record baru dan tanpa exception internal yang bocor")
def assert_malformed(context):
    assert [r.status_code for r in context.responses] == [400, 400]
    assert Feedback.objects.count() == 0
    assert all(b"Traceback" not in r.content for r in context.responses)


@given("payload valid menyertakan related_indicator_code dan related_period sintetis")
def advisory_feedback(context):
    feedback(context)
    context.payload.update(related_indicator_code="synthetic_bdd", related_period="SYNTHETIC 2024")


@then("kedua field dipertahankan sebagai konteks advisory dan tidak diklaim mengikat immutable revision analisis")
def assert_advisory(context):
    assert context.response.status_code == 201
    record = Feedback.objects.get(pk=context.response.json()["id"])
    assert record.related_indicator_code == "synthetic_bdd" and record.related_period == "SYNTHETIC 2024"
    assert "revision" not in json.dumps(context.response.json()).lower()
    context.evidence["acceptance_gate"] = "Q04 OPEN: this verifies advisory storage only, not immutable revision binding"


@given("sesi Admin uji terbentuk lalu flag staff dicabut pada fixture")
def revoked_role(context):
    user(context)
    login(context)
    context.user.is_staff = False
    context.user.save(update_fields=["is_staff"])


@when("client meminta status sesi dan mencoba operasi Admin yang memerlukan izin")
def revoked_requests(context):
    context.session_response = context.client.get("/api/auth/session/")
    context.admin_response = context.client.get("/admin/indicators/feedback/")
    context.public_response = Client(enforce_csrf_checks=True).get("/api/indicators/")


@then("sesi tidak memberi hak Admin lagi dan data publik tetap dapat diakses anonim")
def assert_revoked(context):
    assert context.session_response.status_code == 403
    assert context.admin_response.status_code in (302, 403)
    if context.admin_response.status_code == 302:
        assert "/admin/login/" in context.admin_response["Location"]
    assert context.public_response.status_code == 200


# BDD-X-07 remains undefined: whole-run isolation must be asserted against a completed
# run receipt, not substituted with a small fixture deletion that could falsely pass.
