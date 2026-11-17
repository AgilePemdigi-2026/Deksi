"""Hooks apply only to this owned BDD tree, never the product hook file."""
import json
import os
from pathlib import Path

import subprocess

from django.conf import settings
from django.db import connection

from journal import entries


def before_scenario(context, scenario):
    context.browser = None
    context.vite = None
    context.vite_log = None
    context.artifacts = Path(os.environ["DEKSI_BDD_ARTIFACTS"]) / scenario.name.split(" - ")[0]
    context.artifacts.mkdir(parents=True, exist_ok=False)
    context.evidence = {"scenario": scenario.name, "api_mocked": False}
    context.cleanup_results = {}
    entries.clear()
    context.overrides = []
    scenario_id = scenario.name.split(" - ")[0]
    candidate_contracts = {
        "BDD-F07-04": "Q03: candidate contract executed; human acceptance remains pending",
        "BDD-F08-08": "Q04: advisory context candidate executed; human acceptance remains pending",
        "BDD-X-03": "Q02: populated historical flow executed; empty-year coordination remains pending",
    }
    if scenario_id in candidate_contracts:
        context.evidence["human_review_pending"] = candidate_contracts[scenario_id]


def django_ready(context):
    database = Path(connection.settings_dict["NAME"]).resolve()
    run_dir = Path(os.environ["DEKSI_BDD_RUN_DIR"]).resolve()
    assert database.is_relative_to(run_dir), "Wrong database; refusing fixture writes"
    assert settings.MAILERS["default"]["BACKEND"] == "django.core.mail.backends.locmem.EmailBackend"
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE
    assert settings.CSRF_COOKIE_HTTPONLY
    context.evidence["database"] = str(database)
    context.evidence["backend_live_url"] = context.base_url
    with connection.cursor() as cursor:
        context.evidence["main_database_list"] = cursor.execute("PRAGMA database_list").fetchall()


def after_scenario(context, scenario):
    if context.browser:
        try:
            context.browser.screenshot("browser-final.png")
            context.evidence["final_dom"] = context.browser.js("({path:location.pathname,body:document.body.innerText})")
            context.evidence.update({"browser_requests": context.browser.requests,
                                     "browser_blocked": context.browser.blocked,
                                     "browser_runtime_errors": context.browser.errors,
                                     "fault_injections": context.browser.faults,
                                     "browser_driver": "Chrome/CDP real, NON-Selenium"})
        except Exception as exc:
            context.evidence["capture_error"] = type(exc).__name__
        finally:
            context.browser.close()
            context.cleanup_results["chrome_process_stopped"] = context.browser.process.poll() is not None
    if context.vite:
        context.vite.terminate()
        try:
            context.vite.wait(timeout=8)
        except subprocess.TimeoutExpired:
            context.vite.kill()
            context.vite.wait(timeout=5)
        context.cleanup_results["vite_process_stopped"] = context.vite.poll() is not None
    if context.vite_log:
        context.vite_log.close()
    for override in reversed(context.overrides):
        override.disable() if hasattr(override, "disable") else override.stop()
    context.evidence["server_requests"] = list(entries)
    context.evidence["status"] = str(scenario.status)
    context.evidence["cleanup"] = context.cleanup_results
    (context.artifacts / "evidence.json").write_text(json.dumps(context.evidence, indent=2), encoding="utf-8")
