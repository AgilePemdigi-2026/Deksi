"""Executable BDD bindings for Admin feedback features 15-18.

All records are synthetic and live only in the runner-owned disposable database.
"""
import json
import uuid

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from indicators.feedback_model import Feedback, FeedbackAuditLog
from indicators.models import Indicator

LIST_PATH = "/api/admin/feedback/"
SYNTHETIC_NOTES = "SYNTHETIC BDD: laporan diverifikasi untuk pengujian."


def _client(context, authenticated=True):
    context.client = Client(enforce_csrf_checks=True)
    if authenticated:
        context.admin = get_user_model().objects.create_user(
            username=f"synthetic-feedback-admin-{uuid.uuid4().hex[:12]}",
            email="synthetic-feedback-admin@example.test",
            is_staff=True,
        )
        context.client.force_login(context.admin)
    return context.client


def _feedback(**overrides):
    values = {
        "category": Feedback.Category.DATA_ERROR,
        "description": "SYNTHETIC BDD laporan umpan balik.",
        "sender_name": "Penguji BDD",
        "sender_email": "penguji@example.test",
        "status": Feedback.Status.PENDING,
    }
    values.update(overrides)
    return Feedback.objects.create(**values)


def _clean_feedback():
    Feedback.objects.all().delete()


def _csrf_token(context, feedback):
    response = context.client.get(f"{LIST_PATH}{feedback.pk}/")
    assert response.status_code == 200, response.content[:300]
    return response.json()["csrfToken"]


def _bootstrap_anonymous_csrf(context):
    response = context.client.get("/api/auth/csrf/")
    assert response.status_code == 200, response.content[:300]
    return response.json()["csrfToken"]


@given("Admin memiliki dua laporan umpan balik sintetis dengan kategori dan status berbeda")
def feedback_list_fixture(context):
    _clean_feedback()
    _client(context)
    context.feedback_pending = _feedback(
        description="SYNTHETIC BDD laporan data menunggu.",
        category=Feedback.Category.DATA_ERROR,
    )
    context.feedback_review = _feedback(
        description="SYNTHETIC BDD laporan visual ditinjau.",
        category=Feedback.Category.VISUALIZATION,
        status=Feedback.Status.IN_REVIEW,
    )


@when("Admin meminta daftar umpan balik")
def request_feedback_list(context):
    context.response = context.client.get(LIST_PATH)


@then("daftar berisi kedua laporan dengan kategori tanggal dan status")
def assert_feedback_list(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["count"] == 2
    by_id = {item["id"]: item for item in body["feedbacks"]}
    pending = by_id[context.feedback_pending.pk]
    review = by_id[context.feedback_review.pk]
    for item in (pending, review):
        assert item["category_label"]
        assert item["created_at"]
        assert item["status_label"]
    assert pending["category"] == Feedback.Category.DATA_ERROR
    assert pending["status"] == Feedback.Status.PENDING
    assert review["category"] == Feedback.Category.VISUALIZATION
    assert review["status"] == Feedback.Status.IN_REVIEW


@given("Admin memiliki daftar umpan balik kosong")
def empty_feedback_fixture(context):
    _clean_feedback()
    _client(context)


@then("respons sukses menampilkan daftar kosong tanpa error")
def assert_empty_list(context):
    assert context.response.status_code == 200
    assert context.response.json()["count"] == 0
    assert context.response.json()["feedbacks"] == []


@given("pengunjung anonim belum memiliki sesi Admin")
def anonymous_feedback_client(context):
    _clean_feedback()
    _client(context, authenticated=False)


@when("pengunjung meminta daftar umpan balik Admin")
def anonymous_list(context):
    context.response = context.client.get(LIST_PATH)


@then("server menolak akses daftar dengan status 401")
def assert_list_unauthorized(context):
    assert context.response.status_code == 401


@given("Admin memiliki laporan sintetis terkait indikator PDB")
def related_indicator_fixture(context):
    _clean_feedback()
    _client(context)
    indicator, _ = Indicator.objects.get_or_create(
        code="pdb",
        defaults={
            "name": "PDB SYNTHETIC BDD",
            "category": "PDB",
            "unit": "%",
            "aggregation_kind": "yoy",
            "sort_order": 1,
        },
    )
    context.feedback = _feedback(
        description="SYNTHETIC BDD laporan terkait PDB.",
        related_indicator_code=indicator.code,
        related_period="Q1 2025",
    )


@when("Admin membuka detail laporan tersebut")
def request_feedback_detail(context):
    context.response = context.client.get(f"{LIST_PATH}{context.feedback.pk}/")


@then("detail menunjukkan indikator terkait dan status yang sama dengan daftar")
def assert_feedback_detail(context):
    assert context.response.status_code == 200
    detail = context.response.json()["feedback"]
    assert detail["id"] == context.feedback.pk
    assert detail["related_indicator"] == {
        "code": "pdb",
        "name": "PDB SYNTHETIC BDD",
        "category": "PDB",
        "unit": "%",
    }
    assert detail["related_period"] == "Q1 2025"
    assert detail["status"] == Feedback.Status.PENDING
    list_response = context.client.get(LIST_PATH)
    assert list_response.status_code == 200
    listed = next(item for item in list_response.json()["feedbacks"] if item["id"] == detail["id"])
    assert listed["status"] == detail["status"]


@given("Admin memiliki sesi valid tanpa laporan terpilih")
def valid_admin_no_feedback(context):
    _clean_feedback()
    _client(context)


@when("Admin meminta detail laporan yang tidak ada")
def request_missing_feedback(context):
    context.response = context.client.get(f"{LIST_PATH}999999/")


@then("server mengembalikan status 404 tanpa detail laporan")
def assert_missing_feedback(context):
    assert context.response.status_code == 404
    assert "feedback" not in context.response.json()


@given("Admin memiliki laporan dengan kata kunci indikator dan laporan pembanding")
def feedback_search_fixture(context):
    _clean_feedback()
    _client(context)
    context.feedback = _feedback(
        description="SYNTHETIC BDD verifikasi angka ekonomi.",
        related_indicator_code="pdb",
        related_period="Q1 2025",
        sender_name="Penguji Pencarian",
    )
    _feedback(
        category=Feedback.Category.VISUALIZATION,
        description="SYNTHETIC BDD laporan grafik lain.",
        sender_name="Penguji Kedua",
    )


@given("Admin memiliki laporan umpan balik sintetis")
def one_feedback_fixture(context):
    _clean_feedback()
    _client(context)
    _feedback()


@when("Admin mencari umpan balik menggunakan kata kunci indikator")
def search_feedback_indicator(context):
    context.response = context.client.get(LIST_PATH, {"search": "PDB"})


@then("hanya laporan yang cocok ditampilkan")
def assert_feedback_search_hit(context):
    assert context.response.status_code == 200
    body = context.response.json()
    assert body["search_query"] == "PDB"
    assert body["count"] == 1
    assert [item["id"] for item in body["feedbacks"]] == [context.feedback.pk]


@when("Admin mencari umpan balik menggunakan kata kunci yang tidak ada")
def search_feedback_empty(context):
    context.response = context.client.get(LIST_PATH, {"search": "SYNTHETIC-no-match-98765"})


@then("pencarian sukses menampilkan nol hasil")
def assert_feedback_search_empty(context):
    assert context.response.status_code == 200
    body = context.response.json()
    assert body["count"] == 0
    assert body["feedbacks"] == []


@given("Admin memiliki laporan pending dan token CSRF valid")
def pending_feedback_with_csrf(context):
    _clean_feedback()
    _client(context)
    context.feedback = _feedback()
    context.csrf_token = _csrf_token(context, context.feedback)


@when("Admin mengubah status menjadi resolved dengan catatan penanganan sintetis")
def update_feedback_status(context):
    context.response = context.client.post(
        f"{LIST_PATH}{context.feedback.pk}/status/",
        data=json.dumps({"status": Feedback.Status.RESOLVED, "notes": SYNTHETIC_NOTES}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


@then("status catatan waktu pembaruan dan audit log tersimpan")
def assert_status_audit(context):
    assert context.response.status_code == 200, context.response.content[:300]
    context.feedback.refresh_from_db()
    audit = FeedbackAuditLog.objects.get(feedback=context.feedback)
    detail = context.response.json()["feedback"]
    assert context.feedback.status == Feedback.Status.RESOLVED
    assert context.feedback.admin_notes == SYNTHETIC_NOTES
    assert context.feedback.updated_at is not None
    assert audit.old_status == Feedback.Status.PENDING
    assert audit.new_status == Feedback.Status.RESOLVED
    assert audit.notes == SYNTHETIC_NOTES
    assert audit.changed_by == context.admin.username
    assert audit.changed_at is not None
    assert detail["status"] == context.feedback.status
    assert detail["updated_at"] == context.feedback.updated_at.isoformat()
    assert detail["audit_logs"][0]["changed_at"] == audit.changed_at.isoformat()


@when("Admin mengirim perubahan dengan status yang tidak valid")
def invalid_feedback_status(context):
    context.response = context.client.post(
        f"{LIST_PATH}{context.feedback.pk}/status/",
        data=json.dumps({"status": "SYNTHETIC-invalid-status", "notes": SYNTHETIC_NOTES}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


@then("server menolak perubahan dan tidak membuat audit log")
def assert_invalid_status(context):
    assert context.response.status_code == 400
    context.feedback.refresh_from_db()
    assert context.feedback.status == Feedback.Status.PENDING
    assert not FeedbackAuditLog.objects.filter(feedback=context.feedback).exists()


@given("laporan pending tersedia tanpa sesi Admin dan token CSRF valid")
def anonymous_pending_feedback(context):
    _clean_feedback()
    _client(context, authenticated=False)
    context.feedback = _feedback()
    context.csrf_token = _bootstrap_anonymous_csrf(context)


@when("pengunjung anonim mengirim perubahan status")
def anonymous_update(context):
    context.response = context.client.post(
        f"{LIST_PATH}{context.feedback.pk}/status/",
        data=json.dumps({"status": Feedback.Status.RESOLVED, "notes": SYNTHETIC_NOTES}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


@then("server menolak perubahan dan status laporan tetap pending")
def assert_anonymous_update(context):
    assert context.response.status_code == 401, context.response.content[:300]
    context.feedback.refresh_from_db()
    assert context.feedback.status == Feedback.Status.PENDING
    assert not FeedbackAuditLog.objects.filter(feedback=context.feedback).exists()
