"""First two vertical slices bind to unchanged Batch 1 step text."""
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import tempfile

from behave import given, when, then
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from browser import Chrome, free_port, wait_http
from indicators.models import Indicator, Observation, Source
from journal import entries


def fixture(context, private=False):
    # All objects are disposable and labelled synthetic; reviewer is not a real human review.
    reviewer = get_user_model().objects.create_user(username="SYNTHETIC-BDD-reviewer", is_staff=True)
    context.indicator = Indicator.objects.create(
        code="pdb", name="PDB SYNTHETIC BDD — bukan data resmi",
        category="PDB", unit="triliun rupiah", description="SYNTHETIC BDD fixture only",
    )
    source = Source.objects.create(
        source_id="SYNTHETIC_BDD", source_name="SYNTHETIC dataset",
        institution="SYNTHETIC institution, no official verification",
        primary_url="https://example.test/bdd-synthetic",
    )
    base = dict(indicator=context.indicator, source=source, frequency="quarterly",
                data_type="level", unit="triliun rupiah")
    context.observation = Observation.objects.create(
        **base, observation_date=date(2025, 3, 31), period_label="Q1 2025", value="1234.50",
        publication_date=date(2025, 4, 30), validation_status="published",
        reviewed_by=reviewer, reviewed_at=timezone.now(),
        validation_notes="SYNTHETIC technical fixture reviewer, NOT human economic review",
    )
    if private:
        Observation.objects.create(**base, observation_date=date(2025, 6, 30), period_label="PRIVATE BDD B",
                                   value="98765.4321", validation_status="pending")
        Observation.objects.create(**base, observation_date=date(2025, 9, 30), period_label="PRIVATE BDD C",
                                   value="87654.321", validation_status="published")
    context.evidence["fixture"] = {"label": "SYNTHETIC ONLY", "human_review": False,
                                    "expected_value": "1234.50", "period": "Q1 2025"}


@given("tersedia observasi lama A yang reviewed-published serta draft B dan published C tanpa reviewer yang lebih baru")
def publication_fixture(context):
    fixture(context, private=True)
    context.client = Client(enforce_csrf_checks=True)


@when("client meminta ringkasan indikator")
def summary_api(context):
    context.response = context.client.get("/api/indicators/", {"code": context.indicator.code})
    assert context.response.status_code == 200, context.response.status_code


@then("nilai A dikembalikan dan nilai B serta C tidak dikirim sebagai angka publik")
def assert_publication(context):
    body = context.response.json()
    assert len(body["indicators"]) == 1
    row = body["indicators"][0]
    assert row["id"] == "pdb" and row["available"] is True
    assert Decimal(row["value"]) == Decimal("1234.50"), row
    assert row["period"] == "Q1 2025" and row["unit"] == "triliun rupiah"
    assert row["sourceId"] == "SYNTHETIC_BDD"
    serialized = json.dumps(body)
    for marker in ("98765.4321", "87654.321", "PRIVATE BDD B", "PRIVATE BDD C"):
        assert marker not in serialized, "Non-public fixture leaked"
    context.evidence["api"] = {"path": "/api/indicators/?code=pdb", "status": 200,
                               "value": row["value"], "private_markers_absent": True,
                               "transport": "Django test client, real views/database, CSRF enforced"}


@given("fixture PDB hanya memiliki observasi publik tahun 2025 dan browser terisolasi tersedia")
@given("observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah dan periode Q1 2025 sudah direview dan dipublikasikan")
def browser_fixture(context):
    fixture(context)
    root = Path(__file__).resolve().parents[3]
    fe = root / "frontend-checkpoint" / "frontend"
    assert (fe / "node_modules/vite/bin/vite.js").exists(), "No existing Vite dependency; no installs allowed"
    port = free_port()
    context.frontend_url = f"http://127.0.0.1:{port}"
    env = {k: v for k, v in os.environ.items() if not k.startswith("VITE_")}
    env.update({"DEKSI_PUBLIC_API_TARGET": context.base_url,
                "DEKSI_AUTH_API_TARGET": context.base_url})
    context.vite_log = (context.artifacts / "vite.log").open("w", encoding="utf-8")
    context.vite = subprocess.Popen([
        "node", str(fe / "node_modules/vite/bin/vite.js"), "--configLoader", "runner",
        "--host", "127.0.0.1", "--port", str(port), "--strictPort", "--clearScreen", "false",
    ], cwd=fe, env=env, stdout=context.vite_log, stderr=context.vite_log)
    wait_http(context.frontend_url, context.vite)
    # Unique per scenario: a reused DevToolsActivePort file can point at a stopped browser.
    profile = Path(tempfile.mkdtemp(prefix="chrome-", dir=os.environ["DEKSI_BDD_RUN_DIR"]))
    context.browser = Chrome(profile, context.artifacts, context.frontend_url)
    context.browser.connect()
    context.evidence["frontend_url"] = context.frontend_url
    context.evidence["ports"] = {"frontend": port, "chrome_debug": context.browser.debug_port}


@when("pengunjung anonim membuka dashboard")
def open_dashboard(context):
    browser = context.browser
    browser.call("Page.navigate", {"url": context.frontend_url + "/"})
    browser.wait("Boolean(document.querySelector('[data-indicator=\"pdb\"] .dash-card-value')) && document.querySelector('[data-indicator=\"pdb\"] .dash-card-value').textContent !== 'Belum tersedia'")


@then("kartu PDB menampilkan angka ekuivalen 1234.50 beserta unit dan periode yang sama tanpa meminta Login")
def assert_browser_summary(context):
    browser = context.browser
    row = browser.js("""(()=>{const c=document.querySelector('[data-indicator="pdb"]');return {
        name:c.querySelector('h3').textContent,
        value:c.querySelector('.dash-card-value').textContent,
        period:c.querySelector('.dash-card-period').textContent,
        path:location.pathname, cookies:document.cookie,
        storageKeys:[...Object.keys(localStorage),...Object.keys(sessionStorage)]}})()""")
    # Locale-independent comparison removes grouping separators but preserves decimal intent.
    assert Decimal(row["value"].replace(".", "").replace(",", ".")) == Decimal("1234.50"), row
    assert "triliun rupiah" in row["period"] and "Q1 2025" in row["period"], row
    assert "SYNTHETIC" in row["name"] and row["path"] == "/", row
    assert not any("session" in key.lower() for key in row["storageKeys"])
    public_hits = [e for e in entries if e["path"] == "/api/indicators/dashboard/" and e["status"] == 200]
    assert public_hits, "No real React→proxy→Django request recorded"
    assert not browser.errors, browser.errors
    assert not browser.blocked, browser.blocked
    assert not any(e["method"] != "GET" for e in entries), "Anonymous summary unexpectedly mutated backend"
    context.evidence["rendered_summary"] = row
    context.evidence["real_http_dashboard_requests"] = len(public_hits)
    browser.js("document.querySelector('[data-indicator=\"pdb\"]').scrollIntoView({block:'center',behavior:'instant'})")


@when("pengunjung memilih tahun 2024 tanpa data lalu menekan Detail PDB")
def empty_year_detail(context):
    open_dashboard(context)
    browser = context.browser
    browser.wait("Boolean(document.querySelector('#filter-year option[value=\"2024\"]'))")
    browser.js("(()=>{const e=document.querySelector('#filter-year');e.value='2024';e.dispatchEvent(new Event('change',{bubbles:true}))})()")
    browser.wait("document.querySelector('[data-indicator=\"pdb\"] .dash-card-value')?.textContent === 'Belum tersedia'")
    context.evidence["empty_year_before_navigation"] = browser.js("({year:document.querySelector('#filter-year').value,card:document.querySelector('[data-indicator=\"pdb\"]').innerText})")
    browser.js("document.querySelector('[data-indicator=\"pdb\"] .dash-card-bottom button').scrollIntoView({block:'center',behavior:'instant'})")
    browser.screenshot("empty-year-before.png")
    point = browser.js("(()=>{const r=document.querySelector('[data-indicator=\"pdb\"] .dash-card-bottom button').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
    browser.call("Input.dispatchMouseEvent", {"type": "mousePressed", **point, "button": "left", "clickCount": 1})
    browser.call("Input.dispatchMouseEvent", {"type": "mouseReleased", **point, "button": "left", "clickCount": 1})
    # A non-navigation explicit rejection is allowed; an unqualified latest-value redirect is not.
    import time
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if browser.js("location.pathname !== '/' && document.body.innerText.includes('Q1 2025')"):
            break
        time.sleep(0.1)
    context.evidence["empty_year_after_navigation"] = browser.js("({url:location.href,body:document.body.innerText,status:document.querySelector('.p2-navigation-status')?.textContent,year:document.querySelector('#filter-year')?.value})")


@then("navigasi mempertahankan konteks kosong atau memberi penolakan eksplisit tanpa menampilkan nilai terbaru tahun 2025")
def assert_empty_year_context(context):
    actual = context.evidence["empty_year_after_navigation"]
    assert not ("/indikator/pdb" in actual["url"] and "Q1 2025" in actual["body"]), (
        "PRODUCT GAP: empty 2024 filter silently navigated to latest Q1 2025; " + actual["url"]
    )
    if actual["url"].rstrip('/') == context.frontend_url:
        assert actual['year'] == '2024' and '2024' in actual['status']
        assert 'belum tersedia' in actual['status'] and 'Detail tidak dibuka' in actual['status']
