"""Additional browser paths use real DOM input, original React and test Django HTTP."""
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from behave import given, when, then
from django.contrib.auth import get_user_model

from indicators.feedback_model import Feedback
from journal import entries
PASSWORD = "SYNTHETIC-Bdd-Original-9472!"


def browser_fixture(context):
    context.execute_steps("Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah dan periode Q1 2025 sudah direview dan dipublikasikan")


def open_dashboard(context):
    context.execute_steps("When pengunjung anonim membuka dashboard")


@given("akun sintetis Admin aktif dengan password uji yang valid dan CSRF bootstrap tersedia")
def login_browser(context):
    browser_fixture(context)
    context.user = get_user_model().objects.create_user(username="synthetic-browser-admin", password=PASSWORD, is_staff=True)
    context.browser.call("Page.navigate", {"url": context.frontend_url + "/admin/login"})
    context.browser.wait("Boolean(document.querySelector('#login-submit')) && !document.querySelector('#login-submit').disabled")


@when("Admin mengisi identifier dan password lalu mengirim formulir Login")
def submit_login(context):
    browser = context.browser
    browser.type_text("#identifier", context.user.username)
    browser.type_text("#password", PASSWORD)
    browser.click("#login-submit")
    browser.wait("Boolean(document.querySelector('#admin-session'))")


@then("browser menunjukkan status Admin dan pemeriksaan sesi backend menyatakan authenticated true")
def assert_login(context):
    browser = context.browser
    assert browser.js("document.querySelector('#session-user').textContent") == context.user.username
    state = browser.js("fetch('/api/auth/session/',{credentials:'same-origin'}).then(r=>r.json())")
    assert state["authenticated"] is True and state["user"]["isAdmin"] is True
    assert any(e["path"] == "/api/auth/login/" and e["status"] == 200 for e in entries)
    assert not browser.errors and not browser.blocked
    context.evidence["real_browser_authentication"] = True


@given("observasi PDB uji reviewed-published tersedia dan pengunjung anonim")
def detail_fixture(context):
    browser_fixture(context)


@when("pengunjung membuka detail dari kartu lalu membuka URL detail yang sama secara langsung")
def navigate_detail(context):
    open_dashboard(context)
    context.browser.click('[data-indicator="pdb"] .dash-card-bottom button')
    context.browser.wait("location.pathname === '/indikator/pdb' && Boolean(document.querySelector('.fd-metric')) && document.body.innerText.includes('Q1 2025')")
    context.detail_url = context.browser.js("location.href")
    context.detail_first = context.browser.js("document.querySelector('.fd-reading').innerText")
    previous_document = context.browser.js("performance.timeOrigin")
    context.browser.call("Page.navigate", {"url": context.detail_url})
    context.browser.wait(f"performance.timeOrigin > {previous_document}")
    context.browser.wait("Boolean(document.querySelector('.fd-metric')) && document.body.innerText.includes('Q1 2025')")


@then("kedua jalur menampilkan indikator serta konteks observasi yang sama tanpa Login")
def assert_detail(context):
    browser = context.browser
    assert browser.js("document.querySelector('.fd-reading').innerText") == context.detail_first
    assert Decimal(browser.js("document.querySelector('.fd-metric').textContent").replace(".", "").replace(",", ".")) == Decimal("1234.50")
    assert "SYNTHETIC" in browser.js("document.querySelector('h1').textContent")
    selector = parse_qs(urlsplit(context.detail_url).query)
    assert selector["tanggal"] == ["2025-03-31"] and selector["sumber"] == ["SYNTHETIC_BDD"]
    assert browser.js("fetch('/api/auth/session/').then(r=>r.json())")["authenticated"] is False
    context.evidence["bound_detail_url"] = context.detail_url


@given("detail sedang menampilkan observasi A dengan observationDate frequency dataType dan sourceId fixture")
def source_fixture(context):
    browser_fixture(context)
    navigate_detail(context)


@when("pengunjung memilih Source Trace")
def go_trace(context):
    context.browser.click(".fd-source-panel a")
    context.browser.wait("location.pathname === '/indikator/pdb/sumber' && document.querySelector('.source-trace-feature')?.getAttribute('aria-busy') === 'false' && document.querySelector('.ft-value-period')?.textContent === 'Q1 2025'")


@then("keempat selector diteruskan dan halaman trace tetap merujuk observasi A bukan observasi terbaru lain")
def assert_trace(context):
    browser = context.browser
    url = browser.js("location.href")
    context.evidence["trace_actual"] = {"url": url, "body": browser.js("document.body.innerText")}
    query = parse_qs(urlsplit(url).query)
    expected = {"tanggal": "2025-03-31", "frekuensi": "quarterly", "tipe": "level", "sumber": "SYNTHETIC_BDD"}
    assert all(query[k] == [v] for k, v in expected.items())
    body = browser.js("document.body.innerText")
    assert "Q1 2025" in body and "SYNTHETIC institution" in body
    assert "1.234,5" in body and "triliun rupiah" in body
    hits = [e for e in entries if e["path"].endswith("/source-trace/") and "observationDate=2025-03-31" in e["query"]]
    assert hits and all(e["status"] == 200 for e in hits)
    context.evidence["bound_trace_url"] = url


@given("pengunjung tanpa sesi mempunyai kategori valid dan deskripsi sintetis yang memenuhi batas kandidat")
def feedback_browser(context):
    browser_fixture(context)
    open_dashboard(context)
    context.browser.wait("Boolean(document.querySelector('#fb-category option[value=\"other\"]'))")


@when("pengunjung mengirim form setelah bootstrap CSRF")
def submit_feedback_browser(context):
    browser = context.browser
    browser.js("(()=>{const e=document.querySelector('#fb-category');e.value='other';e.dispatchEvent(new Event('change',{bubbles:true}))})()")
    browser.type_text("#fb-description", "SYNTHETIC BDD browser feedback only")
    browser.click("#fb-submit")
    browser.wait("Boolean(document.querySelector('.feedback-success'))")


@then("server mengembalikan 201 dengan status pending dan UI menampilkan konfirmasi setelah row tersimpan")
def assert_feedback_browser(context):
    assert Feedback.objects.count() == 1
    row = Feedback.objects.get()
    assert row.status == "pending" and row.description == "SYNTHETIC BDD browser feedback only"
    assert row.sender_name == row.sender_email == ""
    assert any(e["path"] == "/api/feedback/" and e["method"] == "POST" and e["status"] == 201 for e in entries)
    assert not context.browser.errors and not context.browser.blocked
    context.evidence["stored_feedback"] = {"status": row.status, "synthetic_only": True}
