"""Versioned as-built contracts; no success DTO interception or product edits.

These observations do not close the stricter acceptance gaps in the legacy suite.
"""
from decimal import Decimal
import json
import re

from behave import given, when, then
from django.test import Client

from journal import entries


def actual_fixture(context):
    context.execute_steps('Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah dan periode Q1 2025 sudah direview dan dipublikasikan')
    context.evidence['suite_contract'] = 'as-built-v2; current implementation, not approval of missing acceptance behaviour'


def navigate(context, path, ready):
    browser = context.browser
    origin = browser.js('performance.timeOrigin')
    browser.call('Page.navigate', {'url': context.frontend_url + path})
    browser.wait(f'performance.timeOrigin > {origin}')
    browser.wait(ready)


def visible_warnings(context):
    browser = context.browser
    browser.wait("Boolean(document.querySelector('.fd-status details summary'))")
    browser.click('.fd-status details summary')
    browser.wait("document.querySelector('.fd-status details')?.open===true")
    return browser.js("document.querySelector('.fd-status details').innerText")


def field(context, label, area='.ft-summary'):
    return context.browser.js("Array.from(document.querySelectorAll(" + json.dumps(area + ' div') + ")).find(e=>e.querySelector('dt')?.textContent===" + json.dumps(label) + ")?.querySelector('dd')?.textContent")


@given('fixture publik PDB nyata pada database disposable dan kode asing unknown_bdd')
def unknown_fixture(context):
    actual_fixture(context)


@when('browser membuka detail unknown_bdd dan rincian ketersediaan API')
def unknown_detail(context):
    navigate(context, '/indikator/unknown_bdd', "document.querySelector('#feature-content')?.getAttribute('aria-busy')==='false'")
    context.visible_diagnostics = visible_warnings(context)


@then('kode asing dan nilai tidak tersedia tampil dengan rincian HTTP 404 tanpa angka PDB atau permintaan Login')
def assert_safe_unknown(context):
    browser = context.browser
    assert browser.js('location.pathname') == '/indikator/unknown_bdd'
    assert browser.js("document.querySelector('h1').textContent") == 'unknown_bdd'
    assert browser.js("document.querySelector('.fd-metric').textContent") == 'Belum tersedia'
    reading = browser.js("document.querySelector('.fd-reading').innerText")
    assert '1.234,5' not in reading and 'Q1 2025' not in reading
    assert 'HTTP 404' in context.visible_diagnostics
    assert any(e['status'] == 404 and '/unknown_bdd/' in e['path'] for e in entries)
    assert not browser.js("fetch('/api/auth/session/').then(r=>r.json())")['authenticated']
    context.evidence['as_built_diagnostics'] = context.visible_diagnostics
    context.evidence['acceptance_gap_retained'] = 'Dedicated not-found state is still a legacy acceptance gap; not fixed or declared compliant.'


@given('backend nyata mengirim trace sintetis unclassified tanpa formula input atau revisi immutable')
def actual_trace_contract(context):
    actual_fixture(context)
    response = Client(enforce_csrf_checks=True).get('/api/indicators/pdb/source-trace/')
    assert response.status_code == 200
    context.trace_contract = response.json()
    trace = context.trace_contract
    assert trace['valueKind'] == 'unclassified'
    assert trace['officialVerification'] == 'unassessed'
    assert trace['revisionId'] is None and trace['immutableSnapshot'] is False
    assert trace['calculation']['available'] is False
    assert trace['calculation']['formula'] is None and trace['calculation']['inputs'] is None


@when('browser membuka Source Trace PDB melalui aplikasi asli tanpa Login')
def actual_trace(context):
    navigate(context, '/indikator/pdb/sumber', "document.querySelector('.source-trace-feature')?.getAttribute('aria-busy')==='false'")


@then('nilai periode satuan sumber dan batas klasifikasi formula revisi tampil sesuai kontrak nyata tanpa DTO sukses mock')
def assert_actual_trace(context):
    browser = context.browser
    trace = context.trace_contract
    rendered = browser.js("document.querySelector('.ft-value').textContent")
    assert Decimal(rendered.replace('.', '').replace(',', '.')) == Decimal(trace['value'])
    assert browser.js("document.querySelector('.ft-value-period').textContent") == trace['period']
    assert browser.js("document.querySelector('.ft-value-unit').textContent") == trace['unit']
    assert field(context, 'Institusi sumber') == trace['source']['institution']
    assert field(context, 'Tipe kalkulasi') == 'Belum diklasifikasikan API'
    assert 'Formula belum tersedia' in browser.js("document.querySelector('.ft-formula').innerText")
    assert 'Input perhitungan belum disediakan backend' in browser.js("document.querySelector('.ft-table').innerText")
    assert 'Riwayat revisi belum tersedia' in browser.js('document.body.innerText')
    assert any(e['path'] == '/api/indicators/pdb/source-trace/' and e['status'] == 200 for e in entries)
    assert not browser.rules and not browser.faults and context.evidence['api_mocked'] is False
    assert not browser.errors and not browser.blocked
    context.evidence['actual_trace_contract'] = {'valueKind': trace['valueKind'], 'officialVerification': trace['officialVerification'], 'immutableSnapshot': False, 'revisionId': None, 'value': trace['value'], 'period': trace['period']}
    context.evidence['acceptance_gap_retained'] = 'Official/derived presentation remains outside the real supported path; legacy mock contract is separate.'


@given('fixture trace PDB nyata tersedia untuk pembanding kegagalan')
def error_fixture(context):
    actual_fixture(context)


@when('browser membuka trace kode asing lalu trace PDB dengan transport yang diputus oleh harness')
def trace_error_paths(context):
    ready = "document.querySelector('.source-trace-feature')?.getAttribute('aria-busy')==='false'"
    navigate(context, '/indikator/unknown_bdd/sumber', ready)
    context.trace_not_found = visible_warnings(context)
    context.missing_value = context.browser.js("document.querySelector('.ft-value').textContent")
    context.browser.rules = [{'match': '/api/indicators/pdb/source-trace/', 'action': 'fail'}]
    navigate(context, '/indikator/pdb/sumber', ready)
    context.trace_transport = visible_warnings(context)
    context.transport_value = context.browser.js("document.querySelector('.ft-value').textContent")


@then('rincian respons membedakan HTTP 404 dan transport gagal sementara provenance kosong serta kontrol coba lagi tetap tersedia')
def assert_trace_error_diagnostics(context):
    assert 'HTTP 404' in context.trace_not_found
    assert 'HTTP 404' not in context.trace_transport
    assert re.search(r'fetch|network|request gagal', context.trace_transport, re.I)
    assert context.trace_not_found != context.trace_transport
    assert context.missing_value == context.transport_value == 'Belum tersedia'
    assert field(context, 'Institusi sumber') == 'Belum tersedia'
    assert context.browser.js("Boolean(document.querySelector('.fd-status button'))")
    assert any(e['status'] == 404 and '/unknown_bdd/source-trace/' in e['path'] for e in entries)
    assert any(f['action'] == 'fail' for f in context.browser.faults)
    assert not context.browser.errors and not context.browser.blocked
    context.evidence['as_built_diagnostics'] = {'not_found': context.trace_not_found, 'transport': context.trace_transport}
    context.evidence['acceptance_gap_retained'] = 'Separate prominent states remain a legacy acceptance gap; diagnostics disclosure is the current implementation.'
