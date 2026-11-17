"""Alternative as-built tests; original reachability requirements remain unchanged."""
import json
from unittest.mock import patch

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.test import Client
from indicators.models import Source, SourceRevision

ENDPOINT = "http://127.0.0.1:9/never-probed"


def client(context):
    user = context.user = get_user_model().objects.create_user(username="synthetic-asbuilt", is_staff=True)
    context.client = Client(enforce_csrf_checks=True)
    context.client.force_login(user)
    context.token = context.client.get("/api/auth/csrf/").json()["csrfToken"]
    context.probe = patch("indicators.source_admin_views._probe_endpoint_reachable", side_effect=AssertionError("unexpected network probe"))
    context.probe_mock = context.probe.start()
    context.overrides.append(context.probe)


@given("Admin sumber sintetis siap membuat endpoint tanpa probe")
def prepare_create(context):
    client(context)


@when("Admin menyimpan sumber sintetis dengan endpoint yang belum diverifikasi")
def create(context):
    context.response = context.client.post("/api/admin/sources/create/", data=json.dumps({
        "sourceId": "ASBUILT_BDD", "sourceName": "As-built BDD synthetic", "institution": "Synthetic",
        "primaryUrl": "https://example.test/", "acquisitionMethod": "api_bps", "endpointUrl": ENDPOINT,
        "dataFormat": "json", "frequency": "monthly", "status": "active"}),
        content_type="application/json", HTTP_X_CSRFTOKEN=context.token)


@then("sumber dan revisi pertama tersimpan tanpa memanggil probe")
def assert_created(context):
    assert context.response.status_code == 201, context.response.content[:300]
    source = Source.objects.get(source_id="ASBUILT_BDD")
    assert source.endpoint_url == ENDPOINT
    assert list(SourceRevision.objects.filter(source=source).values_list("version", flat=True)) == [1]
    context.probe_mock.assert_not_called()


@given("Admin sumber sintetis siap mengubah endpoint tanpa probe")
def prepare_edit(context):
    client(context)
    from indicators.source_admin_views import _record_revision
    source = Source.objects.create(source_id="ASBUILT_BDD", source_name="As-built BDD synthetic",
                                   institution="Synthetic", primary_url="https://example.test/",
                                   acquisition_method="api_bps", data_format="json", frequency="monthly",
                                   endpoint_url="https://example.test/original", status="active")
    _record_revision(source, SourceRevision.Action.CREATE, {}, context.user)


@when("Admin menyimpan perubahan endpoint yang belum diverifikasi dengan versi revisi")
def update(context):
    context.response = context.client.patch("/api/admin/sources/ASBUILT_BDD/update/", data=json.dumps({
        "endpointUrl": ENDPOINT, "expectedRevision": 1}), content_type="application/json", HTTP_X_CSRFTOKEN=context.token)


@then("endpoint baru dan revisi kedua tersimpan tanpa memanggil probe")
def assert_updated(context):
    assert context.response.status_code == 200, context.response.content[:300]
    source = Source.objects.get(source_id="ASBUILT_BDD")
    assert source.endpoint_url == ENDPOINT
    assert set(SourceRevision.objects.filter(source=source).values_list("version", flat=True)) == {1, 2}
    context.probe_mock.assert_not_called()
