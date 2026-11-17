"""F09 real browser over isolated frontend, proxy, Django and synthetic SQLite."""
from behave import given, then, when
from journal import entries


@given("browser katalog sumber menggunakan data sintetis yang direview")
def source_browser_fixture(context):
    context.execute_steps("Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah dan periode Q1 2025 sudah direview dan dipublikasikan")


@when("pengunjung membuka katalog dan detail sumber sintetis")
def open_source(context):
    browser = context.browser
    browser.call("Page.navigate", {"url": context.frontend_url + "/sumber-data"})
    browser.wait("Boolean([...document.querySelectorAll('tbody tr')].find(r=>r.innerText.includes('SYNTHETIC_BDD'))) ")
    browser.js("[...document.querySelectorAll('tbody tr')].find(r=>r.innerText.includes('SYNTHETIC_BDD')).querySelector('button.catalog-detail').click()")
    browser.wait("document.body.innerText.includes('PDB SYNTHETIC BDD — bukan data resmi')")


@then("browser menampilkan identitas dan indikator sumber yang sesuai respons Django")
def assert_source(context):
    browser = context.browser
    body = browser.js("document.body.innerText")
    assert all(value in body for value in ("SYNTHETIC_BDD", "SYNTHETIC dataset", "PDB SYNTHETIC BDD — bukan data resmi", "Q1 2025", "1234.5"))
    assert any(e["path"] == "/api/sources/" and e["status"] == 200 for e in entries)
    assert any(e["path"] == "/api/sources/SYNTHETIC_BDD/" and e["status"] == 200 for e in entries)
    assert not browser.errors and not browser.blocked
    context.evidence["verification_layer"] = "real browser, React, proxy, Django, disposable synthetic DB"
