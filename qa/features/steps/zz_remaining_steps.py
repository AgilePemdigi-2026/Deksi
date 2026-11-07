"""Remaining spec bindings: real application paths plus explicitly labelled fault injection.

Step text is loaded unchanged from the preserved feature files. This module is
loaded after existing bindings; shared steps retain their original implementations.
"""
from datetime import date, datetime
from decimal import Decimal
import hashlib
from inspect import getclosurevars
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from behave import given, when, then
from behave.parser import parse_file

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.db import DatabaseError
from django.test import Client, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from indicators.models import DataUpdateLog, Indicator, Observation, RawFile, Source
from indicators.feedback_model import Feedback
from journal import entries

QA = Path(__file__).resolve().parents[2]
PASSWORD = "SYNTHETIC-Bdd-Original-9472!"
NEW = "SYNTHETIC-Bdd-Changed-5829!"
IDS = {
    "BDD-F01-03", "BDD-F01-06", "BDD-F01-08",
    "BDD-F02-02", "BDD-F02-04", "BDD-F02-05", "BDD-F02-08",
    "BDD-F03-03", "BDD-F03-06", "BDD-F03-07", "BDD-F03-08",
    "BDD-F04-02", "BDD-F04-04", "BDD-F04-05", "BDD-F04-06", "BDD-F04-07", "BDD-F04-08",
    "BDD-F05-02", "BDD-F05-04", "BDD-F05-07", "BDD-F05-08",
    "BDD-F06-02", "BDD-F06-03", "BDD-F06-04", "BDD-F06-05", "BDD-F06-06", "BDD-F06-08",
    "BDD-F07-03", "BDD-F07-04", "BDD-F07-05", "BDD-F07-07", "BDD-F07-08", "BDD-F08-04", "BDD-F08-07",
    "BDD-X-01", "BDD-X-03", "BDD-X-04", "BDD-X-05", "BDD-X-06", "BDD-X-07", "BDD-X-08",
}


def sid(c):
    return c.scenario.name.split(" - ")[0]


def nested(c, text):
    c.execute_steps(text)


def start(c):
    nested(c, "Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah dan periode Q1 2025 sudah direview dan dipublikasikan")


def go(c, path):
    browser = c.browser
    old = browser.js("performance.timeOrigin")
    browser.call("Page.navigate", {"url": c.frontend_url + path})
    browser.wait(f"performance.timeOrigin > {old}")
    browser.wait("document.readyState === 'complete'")


def dashboard(c):
    go(c, "/")
    c.browser.wait("Boolean(document.querySelector('[data-indicator=\"pdb\"]'))")


def detail(c, code="pdb"):
    go(c, "/indikator/" + code)
    c.browser.wait("document.querySelector('#feature-content')?.getAttribute('aria-busy') === 'false'")


def trace(c, code="pdb"):
    go(c, "/indikator/" + code + "/sumber")
    c.browser.wait("document.querySelector('.source-trace-feature')?.getAttribute('aria-busy') === 'false'")


def text(c, selector="body"):
    return c.browser.js("document.querySelector(" + json.dumps(selector) + ").innerText")


def change(c, selector, value):
    c.browser.js("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.value=" + json.dumps(value) + ";e.dispatchEvent(new Event('change',{bubbles:true}))})()")


def click_text(c, fragment, area="document"):
    c.browser.js("(()=>{const e=Array.from(" + area + ".querySelectorAll('button,a')).find(e=>e.textContent.includes(" + json.dumps(fragment) + "));if(!e)throw Error('Missing control');e.click()})()")


def wait_trend(c):
    c.browser.wait("document.querySelector('#economic-trend')?.getAttribute('aria-busy') === 'false'")


def press(c, key, shift=False):
    codes = {'Tab': 9, 'Enter': 13, 'Escape': 27, 'Home': 36, 'End': 35}
    for kind in ['keyDown', 'keyUp']:
        event = {'type': kind, 'key': key, 'code': key,
            'windowsVirtualKeyCode': codes[key], 'modifiers': 8 if shift else 0}
        if key == 'Enter' and kind == 'keyDown':
            event.update(text='\r', unmodifiedText='\r')
        c.browser.call('Input.dispatchKeyEvent', event)


def tab_to(c, selector):
    for _ in range(100):
        if c.browser.js('document.activeElement.matches(' + json.dumps(selector) + ')'):
            style_js = "(e=>{const s=getComputedStyle(e);return {outline:s.outlineStyle,shadow:s.boxShadow,border:s.borderColor,stroke:s.stroke,strokeWidth:s.strokeWidth}})"
            focused = c.browser.js(style_js + '(document.activeElement)')
            state = c.browser.js("({path:location.pathname,tag:document.activeElement.tagName})")
            # SVG uses a thicker focus stroke; form controls can use box-shadow.
            # Compare against the same element without focus rather than demand outline.
            press(c, 'Tab', shift=True)
            blurred = c.browser.js(style_js + '(document.querySelector(' + json.dumps(selector) + '))')
            press(c, 'Tab')
            assert c.browser.js('document.activeElement.matches(' + json.dumps(selector) + ')')
            state.update(focused=focused, blurred=blurred, focus_visible=focused['outline'] != 'none' or focused != blurred)
            c.keyboard_checks.append(state)
            assert state['focus_visible'], 'Control has no visible focus style change: ' + selector
            return
        press(c, 'Tab')
    raise AssertionError('Control not keyboard reachable: ' + selector)


def add_point(c, day, value, **updates):
    row = c.observation
    fields = {"indicator": c.indicator, "source": row.source, "frequency": row.frequency,
              "data_type": row.data_type, "unit": row.unit, "reviewed_by": row.reviewed_by,
              "reviewed_at": row.reviewed_at, "validation_status": "published",
              "observation_date": day, "period_label": "SYNTHETIC " + day.isoformat(), "value": value}
    fields.update(updates)
    return Observation.objects.create(**fields)


def second_indicator(c):
    other = Indicator.objects.create(code="inflasi", name="INFLASI SYNTHETIC BDD", category="Inflasi", unit="%")
    for year, amount in [(2024, "2.50"), (2025, "3.00")]:
        Observation.objects.create(indicator=other, source=c.observation.source, observation_date=date(year, 1, 31),
            period_label=f"SYNTHETIC Inflasi {year}", frequency="monthly", data_type="yoy", unit="%",
            value=amount, validation_status="published", reviewed_by=c.observation.reviewed_by,
            reviewed_at=c.observation.reviewed_at)


def account(c):
    c.user = get_user_model().objects.create_user(username="synthetic-expanded-admin", email="expanded@example.test", password=PASSWORD, is_staff=True)


def login(c, password=PASSWORD):
    go(c, "/admin/login")
    c.browser.wait("Boolean(document.querySelector('#login-submit')) && !document.querySelector('#login-submit').disabled")
    c.browser.type_text("#identifier", c.user.username)
    c.browser.type_text("#password", password)
    c.browser.click("#login-submit")


def session(c):
    return c.browser.js("fetch('/api/auth/session/',{credentials:'same-origin'}).then(r=>r.json())")


def reset_form(c):
    cap = {"uid": urlsafe_base64_encode(force_bytes(c.user.pk)), "token": default_token_generator.make_token(c.user)}
    go(c, "/admin/reset-password#" + urlencode(cap))
    c.browser.wait("Boolean(document.querySelector('#recovery-confirm-form'))")


def raw_metadata(c):
    content = b"SYNTHETIC metadata fixture, not official"
    p = Path(settings.DEKSI_RAW_DIR) / "metadata.raw"
    p.parent.mkdir(exist_ok=True)
    p.write_bytes(content)
    raw = RawFile.objects.create(source=c.observation.source, document_name="SYNTHETIC raw",
        stored_path=str(p), checksum_sha256=hashlib.sha256(content).hexdigest(), file_size_bytes=len(content),
        retrieved_at=timezone.datetime(2025, 5, 2, tzinfo=timezone.get_default_timezone()))
    c.observation.raw_file = raw
    c.observation.save()


def setup(c):
    key = sid(c)
    if key == "BDD-X-07":
        assert Path(settings.DATABASES["default"]["NAME"]).is_relative_to(Path(os.environ["DEKSI_BDD_RUN_DIR"]))
        return
    start(c)
    if key.startswith("BDD-F01") or key.startswith("BDD-F02") or key in {"BDD-X-01", "BDD-X-04", "BDD-X-08"}:
        account(c)
    if key in {"BDD-F01-06", "BDD-F02-05", "BDD-X-08"}:
        login(c)
        c.browser.wait("Boolean(document.querySelector('#admin-session'))")
        c.old_cookie = next(x["value"] for x in c.browser.call("Network.getCookies")["cookies"] if x["name"] == settings.SESSION_COOKIE_NAME)
    if key == "BDD-F01-08":
        c.browser.rules = [{"match": "/api/auth/login/", "action": "fail"}]
    if key == "BDD-F02-02":
        go(c, "/admin/forgot-password")
        c.browser.wait("Boolean(document.querySelector('#recovery-email'))")
        c.browser.type_text("#recovery-email", "not-an-email")
    if key in {"BDD-F02-04", "BDD-F02-08"}:
        reset_form(c)
    if key == "BDD-F02-08":
        c.browser.rules = [{"match": "/api/auth/password-reset/confirm/", "action": "503"}]
        c.evidence["api_mocked"] = "error response only; real token check and real UI"
    if key == "BDD-F03-03":
        c.observation.value = "0"
        c.observation.save()
    if key in {"BDD-F03-06", "BDD-F06-05"}:
        raw_metadata(c)
    if key == "BDD-F03-06":
        DataUpdateLog.objects.all().delete()
        DataUpdateLog.objects.create(updated_at=timezone.datetime(2025, 6, 1, tzinfo=timezone.get_default_timezone()),
            source="SYNTHETIC stored global update, NOT provider access", status="success", observation_count=1)
    if key == "BDD-F06-05":
        c.observation.publication_date = None
        c.observation.save()
    if key in {"BDD-F03-07", "BDD-F03-08"}:
        c.browser.rules = [{"match": "/api/indicators/dashboard/", "action": "hold" if key.endswith("07") else "fail"}]
    if key == "BDD-F04-02":
        source = Source.objects.create(source_id="SYNTHETIC_OTHER", source_name="OTHER SYNTHETIC", institution="SYNTHETIC OTHER", primary_url="https://example.test/other")
        add_point(c, date(2025, 6, 30), "8", source=source)
    if key in {"BDD-F04-05", "BDD-F06-06"}:
        c.observation.observation_date = date(2025, 1, 31)
        c.observation.period_label = "SYNTHETIC Jan 2025"
        c.observation.frequency = "monthly"
        c.observation.value = "1234.123456"
        c.observation.save()
        add_point(c, date(2025, 3, 31), "2345.654321", period_label="SYNTHETIC Mar 2025")
    if key == "BDD-F04-06":
        c.observation.delete()
    if key in {"BDD-F04-07", "BDD-F05-02", "BDD-F06-08"}:
        second_indicator(c)
    if key in {"BDD-F04-07", "BDD-F04-08"}:
        c.browser.rules = [{"match": "/api/indicators/pdb/trend/", "action": "hold" if key.endswith("07") else "fail"}]
    if key in {"BDD-F05-07", "BDD-F05-08", "BDD-X-03"}:
        add_point(c, date(2024, 3, 31), "1111", period_label="SYNTHETIC Q1 2024")
    if key == "BDD-F05-08":
        c.browser.rules = [{"match": "year=2024", "action": "hold"}]
    if key == "BDD-F06-03":
        c.observation.value = "2.50"
        c.observation.unit = "%"
        c.observation.save()
        add_point(c, date(2024, 3, 31), "2.00", period_label="Q1 2024")
    if key == "BDD-F06-08":
        c.browser.rules = [{"match": "/api/indicators/?code=pdb", "action": "hold"}]
    if key == "BDD-F07-05":
        c.observation.source.source_name = '<img src=x onerror="window.__BDD_XSS=1">SYNTHETIC'
        c.observation.source.primary_url = "javascript:window.__BDD_XSS=1"
        c.observation.source.save()
    if key == "BDD-F07-07":
        c.observation.publication_date = None
        c.observation.save()
        c.observation.source.source_name = ""
        c.observation.source.save()
    if key in {"BDD-F07-03", "BDD-F07-04"}:
        payload = Client().get('/api/indicators/pdb/source-trace/').json()
        assert payload['revisionId'] is None and payload['immutableSnapshot'] is False
        if key == "BDD-F07-03":
            assert payload['valueKind'] == 'unclassified'
            payload['valueKind'] = 'official'
            c.browser.rules = [{"match": "/api/indicators/pdb/source-trace/", "action": "mock-contract", "payload": payload}]
            c.evidence['api_mocked'] = True
            c.evidence['mock_scope'] = 'Synthetic official classification only. Backend does NOT produce this classification; NOT real E2E acceptance. Numeric fixture unchanged.'
    if key in {"BDD-F08-04", "BDD-F08-07"}:
        dashboard(c)
        c.browser.wait("Boolean(document.querySelector('#fb-category option[value=\"other\"]'))")
    if key == "BDD-F08-07":
        guard = patch("indicators.feedback_views.Feedback.objects.create", side_effect=DatabaseError("SYNTHETIC storage failure"))
        guard.start()
        c.overrides.append(guard)
        c.evidence['storage_fault_injection'] = 'unittest.mock: Feedback.objects.create raises DatabaseError before commit; real HTTP/UI'
    if key == "BDD-X-06":
        c.indicator.name = "SYNTHETIC BDD " + "nama indikator panjang " * 6
        c.indicator.save()


def submit_feedback(c):
    change(c, "#fb-category", "other")
    c.browser.type_text("#fb-description", "SYNTHETIC BDD expanded feedback only")
    c.browser.click("#fb-submit")


def act(c):
    key = sid(c)
    b = c.browser
    if key in {"BDD-F01-03", "BDD-F01-08"}:
        login(c, "SYNTHETIC-WRONG" if key.endswith("03") else PASSWORD)
        b.wait("Boolean(document.querySelector('#form-status')?.textContent)")
    elif key == "BDD-F01-06":
        b.click("#auth-logout")
        b.wait("!document.querySelector('#admin-session') && !document.querySelector('#login-submit').disabled")
        go(c, "/admin/login")
        b.wait("Boolean(document.querySelector('#login-submit')) && !document.querySelector('#login-submit').disabled")
    elif key == "BDD-F02-02":
        b.click("#recovery-request-submit")
        b.wait("Boolean(document.querySelector('#recovery-email-error')?.textContent)")
    elif key in {"BDD-F02-04", "BDD-F02-08"}:
        b.type_text("#recovery-new-password", NEW)
        b.type_text("#recovery-confirm-password", "SYNTHETIC-MISMATCH" if key.endswith("04") else NEW)
        b.click("#recovery-confirm-submit")
        b.wait("Boolean(document.querySelector('#recovery-confirm-error')?.textContent)" if key.endswith("04") else "Boolean(document.querySelector('#recovery-status')?.textContent)")
    elif key in {"BDD-F02-05", "BDD-X-08"}:
        override = override_settings(ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN=c.frontend_url)
        override.enable()
        c.overrides.append(override)
        go(c, "/admin/forgot-password")
        b.wait("Boolean(document.querySelector('#recovery-email'))")
        b.type_text("#recovery-email", c.user.email)
        b.click("#recovery-request-submit")
        b.wait("Boolean(document.querySelector('#recovery-accepted'))")
        assert len(mail.outbox) == 1
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        assert urlsplit(link).netloc == urlsplit(c.frontend_url).netloc
        go(c, "/admin/reset-password#" + urlsplit(link).fragment)
        b.wait("Boolean(document.querySelector('#recovery-confirm-form'))")
        b.type_text("#recovery-new-password", NEW)
        b.type_text("#recovery-confirm-password", NEW)
        b.click("#recovery-confirm-submit")
        b.wait("Boolean(document.querySelector('#recovery-login'))")
        if key == 'BDD-X-08':
            assert b.js('location.hash') == ''
            go(c, '/admin/reset-password')
            b.wait("Boolean(document.querySelector('#recovery-new-link'))")
    elif key in {"BDD-F03-03", "BDD-F03-06", "BDD-F03-07", "BDD-F03-08"}:
        if key == "BDD-F03-07":
            go(c, "/")
            b.wait("document.querySelector('.dash-metadata')?.innerText.includes('Memuat') === true")
        elif key == "BDD-F03-08":
            go(c, "/")
            b.wait("document.querySelector('.dash-metadata')?.innerText.includes('Gagal') === true")
            c.evidence["error_visible_before_retry"] = True
            b.release()
            click_text(c, "Coba ringkasan")
            b.wait("Boolean(document.querySelector('[data-indicator=\"pdb\"]'))")
        else:
            dashboard(c)
            if key == "BDD-F03-06":
                c.before = text(c, '[data-indicator="pdb"]')
                c.global_before = text(c, '.dash-metadata')
                dashboard(c)
    elif key.startswith("BDD-F04"):
        if key == "BDD-F04-07":
            dashboard(c)
            b.js("Array.from(document.querySelectorAll('[aria-labelledby=\"series-label\"] button')).find(e=>e.textContent==='Inflasi').click()")
            b.wait("document.querySelector('#economic-trend')?.getAttribute('aria-busy')==='false' && document.querySelector('#chart-current-period')?.textContent.includes('Inflasi')")
            b.release()
        else:
            dashboard(c)
            wait_trend(c)
            if key == "BDD-F04-08":
                b.wait("Boolean(document.querySelector('.dash-chart-empty[role=\"alert\"]'))")
                c.evidence["chart_error_before_retry"] = True
                b.release()
                click_text(c, "Coba histori lagi")
                b.wait("Boolean(document.querySelector('#trend-svg'))")
    elif key.startswith("BDD-F05"):
        dashboard(c)
        if key == "BDD-F05-02":
            b.click("#filter-cat-inflasi")
            change(c, "#filter-year", "2024")
            b.wait("document.querySelectorAll('.dash-indicator').length===1 && document.querySelector('[data-indicator=\"inflasi\"] .dash-card-period')?.textContent.includes('2024')")
            wait_trend(c)
        elif key == "BDD-F05-04":
            change(c, "#filter-year", "2024")
            b.wait("document.querySelector('[data-indicator=\"pdb\"] .dash-card-value')?.textContent==='Belum tersedia'")
        elif key == "BDD-F05-07":
            b.click("#filter-cat-pdb")
            change(c, "#filter-year", "2024")
            b.wait("document.querySelector('[data-indicator=\"pdb\"] .dash-card-period')?.textContent.includes('2024')")
            b.click("#filter-reset")
            b.wait("document.querySelector('#filter-year')?.value==='' && document.querySelector('[data-indicator=\"pdb\"] .dash-card-period')?.textContent.includes('2025')")
        else:
            change(c, "#filter-year", "2024")
            b.wait("document.querySelector('.dash-metadata')?.innerText.includes('Memuat')===true")
            change(c, "#filter-year", "2025")
            b.wait("document.querySelector('[data-indicator=\"pdb\"] .dash-card-period')?.textContent.includes('2025') && document.querySelector('.dash-metadata')?.innerText.includes('Memuat')===false")
            b.release()
    elif key.startswith("BDD-F06"):
        if key == "BDD-F06-08":
            go(c, "/indikator/pdb")
            b.wait("Boolean(document.querySelector('.fd-status[role=\"status\"]'))")
            detail(c, "inflasi")
            b.release()
        else:
            detail(c, "unknown_bdd" if key == "BDD-F06-02" else "pdb")
    elif key.startswith("BDD-F07"):
        if key == "BDD-F07-08":
            trace(c, "unknown_bdd")
            c.not_found = text(c)
            b.rules = [{"match": "/source-trace/", "action": "fail"}]
            trace(c)
            c.transport_error = text(c)
        else:
            trace(c)
    elif key in {"BDD-F08-04", "BDD-F08-07"}:
        submit_feedback(c)
        b.wait("Boolean(document.querySelector('.feedback-success'))" if key.endswith("04") else "Boolean(document.querySelector('.feedback-server-error')) || Boolean(document.querySelector('#feedback-form [role=\"alert\"]'))")
    elif key in {"BDD-X-01", "BDD-X-04"}:
        dashboard(c)
        assert not session(c)["authenticated"]
        login(c)
        b.wait("Boolean(document.querySelector('#admin-session'))")
        if key == "BDD-X-04":
            dashboard(c)
            b.wait("Boolean(document.querySelector('#fb-category option[value=\"other\"]'))")
            submit_feedback(c)
            b.wait("Boolean(document.querySelector('.feedback-success'))")
        else:
            b.click("#auth-logout")
            b.wait("!document.querySelector('#admin-session')")
            detail(c)
            trace(c)
    elif key == 'BDD-X-03':
        dashboard(c)
        change(c, '#filter-year', '2024')
        b.wait("document.querySelector('[data-indicator=\"pdb\"] .dash-card-period')?.textContent.includes('2024')")
        b.click('[data-indicator="pdb"] .dash-card-bottom button')
        b.wait("Boolean(document.querySelector('.fd-metric')) && document.querySelector('#feature-content')?.getAttribute('aria-busy')==='false'")
        c.bound_views = [b.js("({url:location.href,reading:document.querySelector('.fd-reading').innerText})")]
        b.click('.fd-source-panel a')
        b.wait("document.querySelector('.ft-value-period')?.textContent==='SYNTHETIC Q1 2024'")
        c.bound_views.append(b.js("({url:location.href,reading:document.querySelector('.ft-summary').innerText})"))
        b.click('.ft-actions a[href^="/indikator/"]')
        b.wait("Boolean(document.querySelector('.fd-metric')) && document.querySelector('#feature-content')?.getAttribute('aria-busy')==='false'")
        c.bound_views.append(b.js("({url:location.href,reading:document.querySelector('.fd-reading').innerText})"))
    elif key == "BDD-X-05":
        c.keyboard_checks = []
        go(c, "/admin/login")
        b.wait("Boolean(document.querySelector('#login-submit')) && !document.querySelector('#login-submit').disabled")
        tab_to(c, '#identifier')
        tab_to(c, '#password')
        press(c, 'Tab', shift=True)
        assert b.js("document.activeElement.id") == 'identifier'
        press(c, 'Tab')
        assert b.js("document.activeElement.id") == 'password'
        tab_to(c, '#login-submit')
        tab_to(c, 'footer button')
        press(c, 'Enter')
        b.wait("document.querySelector('dialog')?.open===true")
        press(c, 'Escape')
        b.wait("document.querySelector('dialog')?.open===false")
        assert b.js("document.activeElement.matches('footer button')")
        dashboard(c)
        tab_to(c, '#filter-year')
        tab_to(c, '#trend-svg .dash-point[tabindex="0"]')
        press(c, 'Home')
        press(c, 'End')
        tab_to(c, '#fb-category')
        tab_to(c, '#fb-description')
        tab_to(c, '#fb-submit')
        press(c, 'Enter')
        assert Feedback.objects.count() == 0
        assert b.js("document.querySelector('#fb-category').matches(':invalid')")
        for code in ['pdb', 'pdb/sumber']:
            go(c, '/indikator/' + code)
            b.wait("document.querySelector('#feature-content')?.getAttribute('aria-busy')==='false'")
            tab_to(c, '.fd-source-panel a' if code == 'pdb' else '.ft-actions a[href^="/indikator/"]')
            press(c, 'Enter')
            b.wait("location.pathname==='" + ('/indikator/pdb/sumber' if code == 'pdb' else '/indikator/pdb') + "'")
    elif key == "BDD-X-06":
        c.width_checks = []
        for width in [390, 1280]:
            b.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": False})
            for path in ["/", "/admin/login", "/admin/forgot-password", "/admin/reset-password", "/indikator/pdb", "/indikator/pdb/sumber"]:
                go(c, path)
                b.wait("document.fonts.status==='loaded'")
                c.width_checks.append(b.js("({path:location.pathname,width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})"))
    elif key == "BDD-X-07":
        child = subprocess.run([sys.executable, "-I", "-B", str(QA / "run_bdd.py"), "--tags", "@BDD_F03_05", "--label", "safety-child"], cwd=QA, capture_output=True, text=True, timeout=60)
        (c.artifacts / "child.log").write_text(child.stdout + child.stderr, encoding="utf-8")
        assert child.returncode == 0
        marker = next(line.removeprefix("ARTIFACTS ") for line in child.stdout.splitlines() if line.startswith("ARTIFACTS "))
        c.child_artifacts = Path(marker)
    else:
        raise AssertionError("Missing real action for " + key)
    if b:
        c.evidence["extended_actual"] = {"path": b.js("location.pathname"), "body": text(c)[:14000]}


def check(c):
    key = sid(c)
    b = c.browser
    body = text(c) if b else ""
    if key in {"BDD-F01-03", "BDD-F01-08"}:
        assert not session(c)["authenticated"] and not b.js("Boolean(document.querySelector('#admin-session'))")
        assert b.js("Boolean(document.querySelector('#form-status').textContent)")
        if key.endswith("08"):
            assert len([r for r in b.requests if r["method"] == "POST" and r["url"].endswith("/api/auth/login/")]) == 1
    elif key == "BDD-F01-06":
        replay = Client(enforce_csrf_checks=True)
        replay.cookies[settings.SESSION_COOKIE_NAME] = c.old_cookie
        assert not replay.get("/api/auth/session/").json()["authenticated"] and not session(c)["authenticated"]
    elif key == "BDD-F02-02":
        assert b.js("Boolean(document.querySelector('#recovery-email-error').textContent)")
        assert not any(e["path"].endswith("password-reset/request/") for e in entries)
    elif key == "BDD-F02-04":
        assert not any(e["path"].endswith("password-reset/confirm/") for e in entries)
        assert not b.js("Boolean(document.querySelector('#recovery-login'))")
    elif key == "BDD-F02-05":
        c.user.refresh_from_db()
        assert c.user.check_password(NEW) and not c.user.check_password(PASSWORD)
        replay = Client(enforce_csrf_checks=True)
        replay.cookies[settings.SESSION_COOKIE_NAME] = c.old_cookie
        assert not replay.get("/api/auth/session/").json()["authenticated"] and not session(c)["authenticated"]
        login(c, PASSWORD)
        b.wait("Boolean(document.querySelector('#form-status').textContent)")
        assert not session(c)["authenticated"]
    elif key == "BDD-F02-08":
        assert not b.js("Boolean(document.querySelector('#recovery-login'))")
        assert len([r for r in b.requests if r["url"].endswith("password-reset/confirm/")]) == 1
    elif key == "BDD-F03-03":
        assert Decimal(text(c, '[data-indicator="pdb"] .dash-card-value')) == 0
        assert text(c, '[data-indicator="inflasi"] .dash-card-value') == "Belum tersedia"
    elif key == "BDD-F03-06":
        assert text(c, '[data-indicator="pdb"]') == c.before
        assert "2025-04-30" in c.before and "Q1 2025" in c.before
        assert text(c, '.dash-metadata') == c.global_before and '01 Jun 2025' in c.global_before
    elif key == "BDD-F03-07":
        assert not b.js("Boolean(document.querySelector('[data-indicator=\"pdb\"] .dash-card-value'))")
        assert "Memuat" in text(c, ".dash-metadata")
        # Independent history may already show real API data; that is not a design fallback.
        assert "1.234" not in text(c, "#economic-indicators")
        b.release()
        b.wait("Boolean(document.querySelector('[data-indicator=\"pdb\"]'))")
    elif key == "BDD-F03-08":
        assert c.evidence["error_visible_before_retry"] and "1.234,5" in body
    elif key == "BDD-F04-02":
        assert "Seri tidak sebanding" in text(c, "#economic-trend")
        assert b.js("document.querySelectorAll('.dash-history tbody tr').length") == 2
        assert not b.js("Boolean(document.querySelector('#trend-svg .dash-line'))")
    elif key == "BDD-F04-04":
        assert b.js("Array.from(document.querySelectorAll('[aria-labelledby=\"frequency-label\"] button')).find(e=>e.textContent==='Bulanan').disabled")
    elif key in {"BDD-F04-05", "BDD-F06-06"}:
        selector = "#economic-trend" if key.startswith("BDD-F04") else ".fd-history"
        assert b.js("document.querySelectorAll(" + json.dumps(selector + " tbody tr") + ").length") == 2
        assert not b.js("Array.from(document.querySelectorAll(" + json.dumps(selector + " polyline") + ")).some(e=>e.getAttribute('points').trim().split(/\\s+/).length>1)")
        assert "1.234,123456" in b.js("document.querySelector(" + json.dumps(selector + " table") + ").textContent")
    elif key == "BDD-F04-06":
        assert "Belum ada histori" in text(c, "#economic-trend") and not b.js("Boolean(document.querySelector('#trend-svg'))")
    elif key == "BDD-F04-07":
        assert "Inflasi" in text(c, "#chart-current-period")
        assert b.js("document.querySelector('[aria-labelledby=\"series-label\"] [aria-pressed=\"true\"]').textContent") == "Inflasi"
    elif key == "BDD-F04-08":
        assert c.evidence["chart_error_before_retry"] and "1.234,5" in text(c, '[data-indicator="pdb"]')
        assert b.js("Boolean(document.querySelector('#trend-svg'))")
    elif key == "BDD-F05-02":
        assert b.js("Array.from(document.querySelectorAll('.dash-indicator')).map(e=>e.dataset.indicator)") == ["inflasi"]
        periods = b.js("Array.from(document.querySelectorAll('.dash-history tbody th')).map(e=>e.textContent)")
        assert periods and all("2024" in p for p in periods)
    elif key == "BDD-F05-04":
        assert b.js("document.querySelector('#filter-year').value") == "2024"
        assert text(c, '[data-indicator="pdb"] .dash-card-value') == "Belum tersedia"
    elif key == "BDD-F05-07":
        assert b.js("document.querySelector('#filter-year').value") == ""
        assert b.js("document.querySelector('#filter-cat-all').getAttribute('aria-pressed')") == "true"
        assert "2025" in text(c, '[data-indicator="pdb"] .dash-card-period')
    elif key == "BDD-F05-08":
        assert b.js("document.querySelector('#filter-year').value") == "2025"
        assert "2025" in text(c, '[data-indicator="pdb"] .dash-card-period')
    elif key == "BDD-F06-02":
        assert "tidak ditemukan" in body.lower(), "PRODUCT GAP: unknown indicator has no distinct not-found state"
        assert "1.234,5" not in body
    elif key == "BDD-F06-03":
        comparison = text(c, ".fd-comparison")
        assert "poin persentase" in comparison and "Q1 2024" in comparison
        assert "0.5" in comparison or "0,5" in comparison
    elif key == "BDD-F06-04":
        assert "Angka bukan kesimpulan" in body and "Tidak ada interpretasi atau narasi AI pengganti" in body
    elif key == "BDD-F06-05":
        metadata = b.js("Array.from(document.querySelectorAll('.fd-metadata div')).map(e=>e.textContent)")
        assert any("Tanggal rilis" in v and "Belum tersedia" in v for v in metadata)
        acquisition = b.js("Array.from(document.querySelectorAll('.fd-metadata div')).find(e=>e.querySelector('dt')?.textContent==='Waktu akuisisi')?.querySelector('dd')?.textContent")
        assert "1.234,5" in body
        assert datetime.fromisoformat(acquisition) == c.observation.raw_file.retrieved_at
    elif key == "BDD-F06-08":
        assert "INFLASI SYNTHETIC BDD" in text(c, "h1")
        assert "1.234,5" not in text(c, ".fd-reading")
    elif key == "BDD-F07-05":
        assert not b.js("Boolean(window.__BDD_XSS)")
        assert "<img src=x" in body
        assert not b.js("Boolean(document.querySelector('a[href^=\"javascript:\"]'))")
    elif key == "BDD-F07-03":
        kind = b.js("Array.from(document.querySelectorAll('.ft-summary div')).find(e=>e.querySelector('dt')?.textContent==='Tipe kalkulasi')?.querySelector('dd')?.textContent")
        assert kind and ('official' in kind.lower() or 'resmi' in kind.lower()), 'PRODUCT GAP (mock contract): valueKind=official is not displayed as official'
        assert 'Formula belum tersedia' in body
    elif key == "BDD-F07-04":
        assert 'Bukan snapshot historis' in body and 'Riwayat revisi belum tersedia' in body
        assert 'Formula belum tersedia' in body
        assert b.js("Array.from(document.querySelectorAll('.fd-metadata div')).filter(e=>e.querySelector('dt')?.textContent==='ID observasi / revisi').every(e=>e.querySelector('dd').textContent==='Belum disediakan API')")
    elif key == "BDD-F07-07":
        assert "SYNTHETIC institution" in body and "Q1 2025" in body
        assert "2025-04-30" not in body and "Belum tersedia" in body
    elif key == "BDD-F07-08":
        assert c.not_found != c.transport_error
        assert "tidak ditemukan" in c.not_found.lower(), "PRODUCT GAP: missing trace not distinguished from transport error"
        assert "gagal" in c.transport_error.lower() or "jaringan" in c.transport_error.lower()
    elif key == "BDD-F08-04":
        row = Feedback.objects.get()
        assert row.status == "pending" and row.sender_name == row.sender_email == ""
        assert any(e["path"] == "/api/feedback/" and e["status"] == 201 for e in entries)
    elif key == "BDD-F08-07":
        assert Feedback.objects.count() == 0 and not b.js("Boolean(document.querySelector('.feedback-success'))")
        assert len([e for e in entries if e["path"] == "/api/feedback/" and e["method"] == "POST"]) == 1

    elif key == "BDD-X-01":
        assert not session(c)["authenticated"] and "Q1 2025" in body
    elif key == 'BDD-X-03':
        assert len(c.bound_views) == 3
        for view in c.bound_views:
            query = parse_qs(urlsplit(view['url']).query)
            assert query['tanggal'] == ['2024-03-31'] and query['sumber'] == ['SYNTHETIC_BDD']
            assert query['frekuensi'] == ['quarterly'] and query['tipe'] == ['level']
            assert '1.111' in view['reading'] and 'SYNTHETIC Q1 2024' in view['reading'] and 'triliun rupiah' in view['reading']
        c.evidence['bound_views'] = c.bound_views
    elif key == "BDD-X-04":
        assert Feedback.objects.get().status == "pending"
        login_at = next(i for i, e in enumerate(entries) if e["path"] == "/api/auth/login/" and e["status"] == 200)
        assert any(e["path"] == "/api/feedback/categories/" for e in entries[login_at+1:])
    elif key == "BDD-X-05":
        assert all(row["tag"] not in ["BODY", "HTML"] and row['focus_visible'] for row in c.keyboard_checks), c.keyboard_checks
        c.evidence["keyboard_checks"] = c.keyboard_checks
    elif key == "BDD-X-06":
        c.evidence["viewport_checks"] = c.width_checks
        assert all(row["scroll"] <= row["width"] for row in c.width_checks), c.width_checks
    elif key == "BDD-X-07":
        cleanup = json.loads((c.child_artifacts / "cleanup.json").read_text())
        run = json.loads((c.child_artifacts / "run.json").read_text())
        assert cleanup["disposable_run_directory_removed"] and not cleanup["product_db_used"]
        assert run["exit_code"] == 0 and not run["external_connections_blocked"]
        c.evidence["isolation_child_receipt"] = str(c.child_artifacts)
        c.evidence["boundary"] = "Task-owned DB and .env rejection checked; Python audit hook is not an OS sandbox"
    elif key == "BDD-X-08":
        assert not session(c)["authenticated"]
        assert b.js("location.hash") == ""
        assert b.js("Object.keys(localStorage).length+Object.keys(sessionStorage).length") == 0
        assert not any(PASSWORD in r["url"] or NEW in r["url"] for r in b.requests)
        assert not b.js("Boolean(document.querySelector('input[type=password]'))")
    else:
        raise AssertionError("Missing nontrivial oracle for " + key)


def dispatch(phase):
    def execute(c):
        {"given": setup, "when": act, "then": check}[phase](c)
    return execute


# Behave-Django may swap the module registry; use the registry actually captured
# by the active decorator so an existing binding is never re-registered.
active_registry = getclosurevars(given).nonlocals['self']
for feature_path in sorted((QA / "features").glob("*.feature")):
    feature = parse_file(str(feature_path))
    for scenario in feature.scenarios:
        if scenario.name.split(" - ")[0] not in IDS:
            continue
        for item in scenario.steps:
            if not any(m.matches(item.name) for m in active_registry.steps[item.step_type]):
                {"given": given, "when": when, "then": then}[item.step_type](item.name)(dispatch(item.step_type))
