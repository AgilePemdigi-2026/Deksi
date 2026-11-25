"""Executable BDD bindings for analysis review (F21) and publication decisions (F22).

All records are synthetic and live only in the runner-owned disposable database.
"""
import json
import uuid
from datetime import date
from decimal import Decimal

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from indicators.lifecycle import review_candidate, stage_observation
from indicators.models import (
    AnalysisReviewAudit,
    Indicator,
    Observation,
    ObservationCandidate,
    Source,
)


def _staff(context):
    context.admin = get_user_model().objects.create_user(
        username=f"synthetic-bdd-review-{uuid.uuid4().hex[:12]}",
        email="peninjau@example.test",
        is_staff=True,
    )
    context.admin.is_superuser = True
    context.admin.save(update_fields=["is_superuser"])
    context.client = Client(enforce_csrf_checks=True)
    context.client.force_login(context.admin)
    context.csrf_token = context.client.get("/api/auth/csrf/").json()["csrfToken"]
    return context.client


def _clean_review():
    AnalysisReviewAudit.objects.all().delete()
    ObservationCandidate.objects.all().delete()
    Observation.objects.all().delete()
    Source.objects.all().delete()
    Indicator.objects.all().delete()


def _source(source_id="BDDREVIEW-SRC"):
    return Source.objects.create(
        source_id=source_id, source_name=f"SYNTHETIC BDD {source_id}",
        institution="INSTANSI UJI SINTETIS",
        primary_url="https://example.test/sumber",
    )


def _indicator(code="bddreview"):
    return Indicator.objects.create(
        code=code, name=f"SYNTHETIC BDD {code}", category="Uji", unit="%",
    )


def _stage(indicator, source, day=15, value="2.5"):
    candidate = stage_observation(
        indicator_id=indicator.pk, source_id=source.pk,
        observation_date=date(2026, 3, day), period_label=f"SYNTHETIS BDD Q1-{day}",
        frequency="quarterly", data_type="level", value=Decimal(value), unit="%",
    )
    assert candidate is not None
    return candidate


def _post_decision(context, candidate_id, decision, fingerprint, notes):
    return context.client.post(
        f"/api/admin/analysis-results/{candidate_id}/decision/",
        data=json.dumps({"decision": decision, "fingerprint": fingerprint, "notes": notes}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=context.csrf_token,
    )


@given("Admin memiliki versi analisis pending tanpa riwayat keputusan")
def pending_version_fixture(context):
    _clean_review()
    _staff(context)
    context.source = _source()
    context.indicator = _indicator()
    context.candidate = _stage(context.indicator, context.source)


@when("Admin meminta daftar hasil analisis pending")
def request_analysis_pending(context):
    context.response = context.client.get("/api/admin/analysis-results/?page=1&status=pending")


@then("daftar memuat versi tersebut dengan status pending")
def assert_analysis_pending(context):
    assert context.response.status_code == 200, context.response.content[:300]
    body = context.response.json()
    assert body["total"] == 1, body
    item = body["items"][0]
    assert item["id"] == context.candidate.pk, item
    assert item["status"] == "pending", item


@given("Admin memiliki versi analisis published dan needs_revision")
def mixed_versions_fixture(context):
    _clean_review()
    _staff(context)
    context.source = _source()
    context.indicator = _indicator()
    first = _stage(context.indicator, context.source, day=10)
    second = _stage(context.indicator, context.source, day=20)
    review_candidate(first.pk, context.admin, decision="publish", notes="")
    review_candidate(second.pk, context.admin, decision="needs_revision",
                     notes="SYNTHETIC BDD sumber belum cocok")


@when("Admin meminta daftar hasil analisis semua status")
def request_analysis_all(context):
    context.response = context.client.get("/api/admin/analysis-results/?page=1&status=all")


@then("daftar memuat kedua versi dengan status masing-masing")
def assert_analysis_mixed(context):
    assert context.response.status_code == 200, context.response.content[:300]
    by_id = {item["id"]: item["status"] for item in context.response.json()["items"]}
    assert sorted(by_id.values()) == ["needs_revision", "published"], by_id
    assert context.response.json()["total"] == 2


@given("Admin memiliki versi analisis pending dengan payload lengkap")
def pending_payload_fixture(context):
    _clean_review()
    _staff(context)
    context.source = _source()
    context.indicator = _indicator()
    context.candidate = _stage(context.indicator, context.source)


@when("Admin meminta detail versi tersebut")
def request_analysis_detail(context):
    context.response = context.client.get(
        f"/api/admin/sources/{context.source.source_id}/candidates/{context.candidate.pk}/"
    )


@then("detail memuat nilai satuan periode sumber dan riwayat kosong")
def assert_analysis_detail(context):
    assert context.response.status_code == 200, context.response.content[:300]
    candidate = context.response.json()["candidate"]
    assert candidate["fingerprint"] == context.candidate.fingerprint, candidate
    assert candidate["value"] == "2.500000", candidate
    assert candidate["unit"] == "%", candidate
    assert candidate["sourceId"] == context.source.source_id, candidate
    assert candidate["reviewHistory"] == [], candidate


@given("Admin telah masuk")
def staff_signed_in(context):
    _clean_review()
    _staff(context)


@when("Admin meminta detail versi analisis yang tidak ada")
def request_analysis_detail_missing(context):
    context.response = context.client.get("/api/admin/sources/BDDREVIEW-SRC/candidates/999999/")


@when("pengunjung meminta daftar hasil analisis")
def anonymous_analysis_list(context):
    context.response = context.client.get("/api/admin/analysis-results/?page=1&status=pending")


@then("server menolak akses hasil analisis dengan status 401")
def assert_analysis_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]


@given("Admin memiliki versi analisis pending dan token CSRF valid")
def pending_csrf_fixture(context):
    _clean_review()
    _staff(context)
    context.source = _source()
    context.indicator = _indicator()
    context.candidate = _stage(context.indicator, context.source)
    context.candidate.refresh_from_db()


@when("Admin menetapkan keputusan publish tanpa catatan")
def decide_publish(context):
    context.response = _post_decision(
        context, context.candidate.pk, "publish", context.candidate.fingerprint, "")


@then("versi menjadi published observasi terbit dan audit publish tercatat")
def assert_published(context):
    assert context.response.status_code == 200, context.response.content[:300]
    assert context.response.json()["status"] == "published"
    context.candidate.refresh_from_db()
    assert context.candidate.status == "published", context.candidate.status
    assert Observation.objects.filter(
        indicator=context.indicator,
        validation_status=Observation.Status.PUBLISHED).count() == 1
    assert AnalysisReviewAudit.objects.filter(
        candidate=context.candidate, decision="publish").count() == 1


@when("Admin menetapkan keputusan perlu revisi dengan catatan ketidaksesuaian")
def decide_needs_revision(context):
    context.response = _post_decision(
        context, context.candidate.pk, "needs_revision",
        context.candidate.fingerprint, "SYNTHETIC BDD sumber tidak sesuai")


@then("versi menjadi needs_revision tanpa observasi baru dan audit tercatat")
def assert_needs_revision(context):
    assert context.response.status_code == 200, context.response.content[:300]
    assert context.response.json()["status"] == "needs_revision"
    context.candidate.refresh_from_db()
    assert context.candidate.status == "needs_revision", context.candidate.status
    assert Observation.objects.count() == 0
    assert AnalysisReviewAudit.objects.filter(
        candidate=context.candidate, decision="needs_revision").count() == 1


@when("Admin menetapkan keputusan reject tanpa catatan")
def decide_reject_without_notes(context):
    context.response = _post_decision(
        context, context.candidate.pk, "reject",
        context.candidate.fingerprint, "   ")


@then("server menolak dengan status 400 dan versi tetap pending")
def assert_reject_needs_notes(context):
    assert context.response.status_code == 400, context.response.content[:300]
    context.candidate.refresh_from_db()
    assert context.candidate.status == "pending", context.candidate.status
    assert AnalysisReviewAudit.objects.count() == 0


@when("Admin menetapkan keputusan dua kali dan dengan fingerprint salah")
def decide_twice_and_tampered(context):
    context.second = _stage(context.indicator, context.source, day=21)
    context.first_ok = _post_decision(
        context, context.candidate.pk, "publish", context.candidate.fingerprint, "")
    assert context.first_ok.status_code == 200, context.first_ok.content[:300]
    context.repeat = _post_decision(
        context, context.candidate.pk, "publish", context.candidate.fingerprint, "")
    tampered = "0" * 63 + ("1" if context.second.fingerprint[-1] != "1" else "2")
    assert len(tampered) == 64
    context.tampered = _post_decision(
        context, context.second.pk, "publish", tampered, "")


@then("pengulangan dan fingerprint salah ditolak dengan status 409")
def assert_double_decision_rejected(context):
    assert context.repeat.status_code == 409, context.repeat.content[:300]
    assert context.tampered.status_code == 409, context.tampered.content[:300]
    context.second.refresh_from_db()
    assert context.second.status == "pending", context.second.status


@when("pengunjung menetapkan keputusan publikasi")
def anonymous_decision(context):
    token_response = context.client.get("/api/auth/csrf/")
    assert token_response.status_code == 200, token_response.content[:300]
    context.response = context.client.post(
        "/api/admin/analysis-results/1/decision/",
        data=json.dumps({"decision": "publish", "fingerprint": "0" * 64, "notes": ""}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token_response.json()["csrfToken"],
    )


@then("server menolak akses keputusan dengan status 401")
def assert_decision_unauthorized(context):
    assert context.response.status_code == 401, context.response.content[:300]
