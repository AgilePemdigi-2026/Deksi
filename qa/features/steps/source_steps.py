"""Executable API steps for F09/F10/F11 (disposable DB only, no external network).

File_xlsx/file_zip_csv tanpa endpoint http tidak memicu probing.
Endpoint http pada skenario negatif menunjuk 127.0.0.1:9 (loopback,
refused cepat, diizinkan audit hook BDD).
"""
import json
from datetime import date

from behave import given, when, then
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from indicators.models import Indicator, Observation, Source, SourceRevision
from indicators.source_admin_views import _record_revision

PASSWORD = "SYNTHETIC-Src-Admin-7351!"
STAFF_USERNAME = "synthetic-src-admin"


def api(context):
    if getattr(context, "api", None) is None:
        context.api = Client(enforce_csrf_checks=True)
    return context.api


def make_staff(username=STAFF_USERNAME, staff=True):
    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.test",
        password=PASSWORD, is_staff=staff,
    )


def staff_user(context):
    user = getattr(context, "staff_user", None)
    if user is None:
        user = context.staff_user = make_staff()
    return user


def login_as(context, username):
    response = api(context).post(
        "/api/admin/login/",
        data=json.dumps({"username": username, "password": PASSWORD}),
        content_type="application/json",
    )
    assert response.status_code == 200, (response.status_code, response.content[:200])
    assert response.json().get("isStaff") is True


def make_source(source_id, name="Dataset Uji", institution="BPS",
                method="file_xlsx", fmt="xlsx", freq="monthly"):
    return Source.objects.create(
        source_id=source_id, source_name=name, institution=institution,
        primary_url="https://example.test/sumber", acquisition_method=method,
        data_format=fmt, frequency=freq, update_schedule="Bulanan", status="active",
    )


def revise_create(source, user):
    return _record_revision(source, SourceRevision.Action.CREATE, {}, user)


def publish_obs(source, code, day, value="3", reviewed=True):
    indicator, _ = Indicator.objects.get_or_create(
        code=code, defaults={"name": f"SYNTHETIC {code}", "category": "Inflasi", "unit": "%"})
    kwargs = {"validation_status": "pending"}
    if reviewed:
        reviewer = get_user_model().objects.create_user(username=f"reviewer-{code}-{day}")
        kwargs = {"validation_status": "published", "reviewed_by": reviewer, "reviewed_at": timezone.now()}
    return Observation.objects.create(
        indicator=indicator, source=source, observation_date=day,
        period_label=f"SYNTHETIC {day.isoformat()}", frequency="monthly",
        data_type="yoy", value=value, unit="%", **kwargs)


def create_payload(source_id="SRC_F10_NEW"):
    return {
        "sourceId": source_id, "sourceName": "Dataset Uji", "institution": "BPS",
        "primaryUrl": "https://example.test/sumber", "description": "",
        "acquisitionMethod": "file_xlsx", "endpointUrl": "", "dataFormat": "xlsx",
        "frequency": "monthly", "updateSchedule": "Bulanan", "status": "active",
    }


# ------------------------------------------------------------------ umum

@when('client meminta GET "{path}"')
def get_path(context, path):
    context.response = api(context).get(path)


# ------------------------------------------------------------------ F09

@given("katalog dua sumber publik dengan observasi reviewed tersedia")
def two_sources(context):
    api(context)
    for sid, code in (("TEST_A", "ind_a"), ("TEST_B", "ind_b")):
        publish_obs(make_source(sid, name=f"Dataset {sid}", institution="BPS" if sid == "TEST_A" else "BI"),
                    code, date(2025, 1, 31))


@then("respons daftar sumber berstatus 200 dengan 2 sumber dan field lengkap")
def assert_list(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["count"] == 2 and len(body["sources"]) == 2
    for entry in body["sources"]:
        for field in ("sourceId", "sourceName", "institution", "acquisitionMethod", "status"):
            assert field in entry, field


@given('sumber "{sid}" dengan satu observasi published-direview dan satu draft')
def one_reviewed_one_draft(context, sid):
    api(context)
    source = make_source(sid)
    publish_obs(source, "ind_a", date(2025, 1, 31), reviewed=True)
    publish_obs(source, "ind_b", date(2025, 1, 31), reviewed=False)


@then('respons detail sumber "{sid}" berstatus 200 dengan {count:d} indikator')
def assert_detail(context, sid, count):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["sourceId"] == sid
    assert len(body["indicatorDetails"]) == count, body["indicatorDetails"]


@given('sumber "{sid}" dengan dua indikator published-direview')
def two_indicators(context, sid):
    api(context)
    source = make_source(sid)
    publish_obs(source, "ind_a", date(2025, 1, 31))
    publish_obs(source, "ind_b", date(2025, 1, 31))


@then('respons indikator sumber "{sid}" berstatus 200 dengan {count:d} indikator')
def assert_source_indicators(context, sid, count):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["sourceId"] == sid and body["count"] == count
    assert len(body["indicators"]) == count


@given('tidak ada sumber "{sid}"')
def no_source(context, sid):
    api(context)
    assert not Source.objects.filter(source_id=sid).exists()


@then("respons berstatus 404 tanpa daftar sumber")
def assert_404(context):
    assert context.response.status_code == 404
    assert "sources" not in context.response.json()


@given('sumber baru "{sid}" tanpa observasi')
def empty_source(context, sid):
    api(context)
    make_source(sid)


@given('sumber "{sid}" hanya dengan observasi draft')
def draft_only(context, sid):
    api(context)
    publish_obs(make_source(sid), "ind_a", date(2025, 1, 31), reviewed=False)


# ------------------------------------------------------------------ F10

@given("admin staf sudah login")
def staff_login(context):
    context.staff_user = make_staff()
    login_as(context, STAFF_USERNAME)


@given("payload tambah sumber file_xlsx valid")
def valid_create_payload(context):
    api(context)
    context.payload = create_payload()


@when('client POST ke "{path}" dengan payload tambah')
def post_payload(context, path):
    context.response = api(context).post(path, data=json.dumps(context.payload),
                                         content_type="application/json")


@then("respons 201 dengan revision tambah version 1")
def assert_created(context):
    assert context.response.status_code == 201, context.response.content[:500]
    body = context.response.json()
    assert body["source"]["sourceId"] == context.payload["sourceId"]
    assert body["revision"]["version"] == 1
    assert body["revision"]["action"] == "tambah"


@given("client anonim tanpa session admin")
def anonymous(context):
    context.api = Client(enforce_csrf_checks=True)


@when('client POST ke "{path}" dengan payload valid')
def post_valid(context, path):
    context.response = api(context).post(path, data=json.dumps(create_payload()),
                                         content_type="application/json")


@then('respons {status:d} dan sumber "{sid}" tidak tersimpan')
def assert_denied(context, status, sid):
    assert context.response.status_code == status, context.response.content[:300]
    assert not Source.objects.filter(source_id=sid).exists()


@given("session login milik akun non-staf yang valid")
def nonstaff_login(context):
    api(context).force_login(make_staff(username="synthetic-src-user", staff=False))


@given('sumber "{sid}" revision 1 sudah ada')
def source_rev1(context, sid):
    api(context)
    revise_create(make_source(sid, name=f"Dataset {sid}"), staff_user(context))


@when('client POST ke "{path}" dengan sourceId "{sid}" yang sama')
def post_same_id(context, path, sid):
    context.response = api(context).post(path, data=json.dumps(create_payload(sid)),
                                         content_type="application/json")


@then("respons 409 dan revision tetap 1")
def assert_conflict(context):
    assert context.response.status_code == 409, context.response.content[:300]
    assert SourceRevision.objects.count() == 1


@given("payload tambah sumber api_bps dengan endpoint tak terjangkau")
def unreachable_payload(context):
    api(context)
    context.payload = create_payload("SRC_F10_UNREACH")
    context.payload.update(acquisitionMethod="api_bps", dataFormat="json",
                            endpointUrl="http://127.0.0.1:9/tidak-ada")


@then("respons 400 menyebut endpoint dan sumber tidak tersimpan")
def assert_unreachable(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert "endpoint" in context.response.json()["error"].lower()
    assert not Source.objects.filter(source_id=context.payload["sourceId"]).exists()


@given('payload tambah sumber dengan sourceId "{sid}"')
def custom_id_payload(context, sid):
    api(context)
    context.payload = create_payload(sid)


@then("respons 400 dan tidak ada sumber baru tersimpan")
def assert_400_no_source(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert Source.objects.count() == 0


@given('sumber bernama "{name}" dari "{institution}" sudah terdaftar')
def named_source(context, name, institution):
    api(context)
    revise_create(make_source("SRC_F10_EX", name=name, institution=institution), staff_user(context))


@when("client POST ke \"{path}\" dengan nama dan institusi sama tetapi sourceId berbeda")
def post_same_name(context, path):
    payload = create_payload("SRC_F10_OTHER")
    payload.update(sourceName="Data Investasi", institution="BKPM")
    context.response = api(context).post(path, data=json.dumps(payload),
                                         content_type="application/json")


@then("respons 400 menyebut kombinasi sudah terdaftar")
def assert_combo(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert "sudah terdaftar" in context.response.json()["error"]


@then("respons 200 memuat metode file_xlsx")
def assert_methods(context):
    assert context.response.status_code == 200, context.response.content[:300]
    values = [m["value"] for m in context.response.json()["methods"]]
    assert "file_xlsx" in values


# ------------------------------------------------------------------ F11

@given('field "{field}" diubah menjadi "{value}"')
def change_field(context, field, value):
    context.changes = {field: value}


@when('client PATCH ke "{path}" dengan payload ubah')
def patch_changes(context, path):
    context.response = api(context).patch(path, data=json.dumps(context.changes),
                                          content_type="application/json")


@then('respons 200 revision naik ke {version:d} dan changedFields memuat "{field}"')
def assert_updated(context, version, field):
    assert context.response.status_code == 200, context.response.content[:500]
    body = context.response.json()
    assert body["revision"]["version"] == version
    assert field in body["revision"]["changedFields"]


@when('client PATCH ke "{path}" dengan payload valid')
def patch_valid(context, path):
    context.response = api(context).patch(path, data=json.dumps({"description": "Uji anonim"}),
                                          content_type="application/json")


@then("respons 401 dan revision tetap 1")
def assert_401_rev1(context):
    assert context.response.status_code == 401, context.response.content[:300]
    assert SourceRevision.objects.count() == 1


@given('payload ubah memuat sourceId "{sid}"')
def change_id(context, sid):
    context.changes = {"sourceId": sid}


@then("respons 400 menyebut sourceId dan revision tetap 1")
def assert_immutable(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert "sourceId" in context.response.json()["error"]
    assert SourceRevision.objects.count() == 1


@given("endpointUrl baru tak terjangkau")
def change_endpoint_bad(context):
    context.changes = {"acquisitionMethod": "api_bps", "dataFormat": "json",
                       "endpointUrl": "http://127.0.0.1:9/tidak-ada"}


@then("respons 400 menyebut endpoint dan revision tetap 1")
def assert_edit_unreachable(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert "endpoint" in context.response.json()["error"].lower()
    assert SourceRevision.objects.count() == 1


@given("payload ubah sama dengan konfigurasi tersimpan")
def no_change(context):
    source = Source.objects.get(source_id="BPS_T")
    context.changes = {"description": source.description or ""}


@then("respons 200 changedFields kosong dan revision tetap 1")
def assert_noop(context):
    assert context.response.status_code == 200, context.response.content[:300]
    assert context.response.json()["changedFields"] == []
    assert SourceRevision.objects.count() == 1


@then("respons 400 dan revision tetap 1")
def assert_400_rev1(context):
    assert context.response.status_code == 400, context.response.content[:300]
    assert SourceRevision.objects.count() == 1


@given("edit deskripsi sudah tersimpan sebagai revision 2")
def edit_saved(context):
    from indicators.models import source_config_snapshot
    source = Source.objects.get(source_id="BPS_T")
    before = source_config_snapshot(source)
    source.description = "Deskripsi revisi uji"
    source.save()
    _record_revision(source, SourceRevision.Action.UPDATE, before, context.staff_user)


@then("respons 200 dengan 2 revisi berurutan dan before sama dengan after sebelumnya")
def assert_history(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["count"] == 2, body
    revs = sorted(body["revisions"], key=lambda r: r["version"])
    assert [r["version"] for r in revs] == [1, 2]
    assert revs[1]["before"] == revs[0]["after"]
