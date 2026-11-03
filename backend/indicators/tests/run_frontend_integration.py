"""Exercise published React against an owned real Django/SQLite loopback instance.

Only synthetic records in a freshly allocated scratch database are created or
mutated. No .env, user DB, provider acquisition, API interception or installation.
"""
import argparse
import calendar
import contextlib
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def configure():
    os.environ["DJANGO_SETTINGS_MODULE"] = "backend.test_settings_indicators"
    import django
    django.setup()


def configure_owned_database():
    scratch = Path(os.environ["HERMES_TEST_SCRATCH"]).resolve()
    database = Path(os.environ["DEKSI_TEST_DATABASE"]).resolve()
    if not database.is_relative_to(scratch) or not database.parent.name.startswith("deksi-be-live-"):
        raise RuntimeError("Mutation is restricted to this runner's owned scratch database")
    configure()


def set_value(value):
    configure_owned_database()
    from indicators.models import Observation
    changed = Observation.objects.filter(indicator__code="inflasi", observation_date=date(2000, 1, 31)).update(
        value=Decimal(value))
    assert changed == 1


def lifecycle_action(action):
    configure_owned_database()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from unittest.mock import patch

    from indicators.lifecycle import review_candidate, stage_observation
    from indicators.models import Observation, ObservationCandidate

    row = Observation.objects.get(indicator__code="birate", observation_date=date(2020, 1, 31))
    actor = get_user_model().objects.get(username="reviewer-synthetic")
    if action in {"stage6", "stage7"}:
        stage_observation(indicator_id=row.indicator_id, source_id=row.source_id,
            observation_date=row.observation_date, period_label=row.period_label, frequency=row.frequency,
            data_type=row.data_type, value=Decimal(action[-1]), unit=row.unit,
            publication_date=row.publication_date, raw_file_id=row.raw_file_id)
        return
    candidate = ObservationCandidate.objects.get(indicator__code="birate", status="pending",
        payload__value="6.000000" if action == "reject6" else "7.000000")
    if action == "reject6":
        review_candidate(candidate.pk, actor, publish=False, notes="Ditolak pada UJI SINTETIS")
    elif action == "fail7":
        with patch("indicators.lifecycle.record_update_success", side_effect=RuntimeError("UJI rollback")):
            try:
                review_candidate(candidate.pk, actor)
            except RuntimeError as exc:
                assert str(exc) == "UJI rollback"
            else:
                raise AssertionError("Injected failure did not execute")
        row.refresh_from_db()
        candidate.refresh_from_db()
        assert row.value == Decimal("5") and candidate.status == "pending"
    elif action == "publish7":
        call_command("publish_observations", username=actor.get_username(), candidate_ids=[candidate.pk])


def seed(owned):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.utils import timezone

    from indicators.models import Indicator, Observation, Source
    from indicators.storage import save_raw

    reviewer = get_user_model().objects.create_user(username="reviewer-synthetic", is_staff=True)
    reviewer.user_permissions.add(Permission.objects.get(content_type__app_label="indicators",
                                                        codename="change_observationcandidate"))
    source = Source.objects.create(source_id="TEST_ONLY", source_name="Dataset UJI SINTETIS",
                                   institution="INSTANSI UJI SINTETIS", primary_url="https://example.test/source")
    for code in ["pdb", "inflasi", "fiskal", "investasi", "birate", "tpt"]:
        Indicator.objects.create(code=code, name=f"{code.upper()} UJI SINTETIS", category="Uji", unit="%")
    indicator = Indicator.objects.get(code="inflasi")
    payload = b"DEKSI UJI SINTETIS: not official economic data\n"
    raw, _ = save_raw(source, payload, "UJI SINTETIS <img onerror=window.__xss=1>.txt",
                      source_url="https://example.test/document", period_label="Dataset UJI 1998-2000")
    months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
              "September", "Oktober", "November", "Desember"]
    for index, month_index in enumerate(range(1998 * 12 + 1, 2000 * 12 + 1)):
        year, month = divmod(month_index, 12)
        month += 1
        latest = year == 2000 and month == 1
        Observation.objects.create(indicator=indicator, source=source, raw_file=raw,
            observation_date=date(year, month, calendar.monthrange(year, month)[1]),
            period_label=f"{months[month - 1]} {year}", frequency="monthly", data_type="yoy",
            value=Decimal(0) if latest else Decimal("2.123456") + Decimal(index) / 100,
            unit="%", publication_date=date(2000, 2, 1), validation_status="published",
            reviewed_by=reviewer, reviewed_at=timezone.now())
    Observation.objects.create(indicator=indicator, source=source, observation_date=date(2026, 1, 31),
        period_label="DRAFT UJI", frequency="monthly", data_type="yoy", value=Decimal(999), unit="%",
        validation_status="pending")
    alternate = Source.objects.create(source_id="ALT_TEST_ONLY", source_name="Dataset ALTERNATIF UJI",
        institution="INSTANSI ALTERNATIF UJI", primary_url="https://example.test/alternate")
    exact_value = "999999999999999999.999999"
    for code, month, value, row_source in [
        ("pdb", 1, exact_value, source),
        ("fiskal", 1, "1", source), ("fiskal", 2, "2", alternate),
        ("investasi", 1, "1", source), ("investasi", 3, "3", source),
    ]:
        Observation.objects.create(indicator=Indicator.objects.get(code=code), source=row_source,
            observation_date=date(2000, month, calendar.monthrange(2000, month)[1]),
            period_label=f"{months[month - 1]} 2000 UJI", frequency="monthly", data_type="level",
            value=Decimal(value), unit="%", validation_status="published",
            reviewed_by=reviewer, reviewed_at=timezone.now())
    lifecycle_raw, _ = save_raw(source, b"UJI SINTETIS lifecycle 2020", "UJI lifecycle.txt",
                                source_url="https://example.test/lifecycle", period_label="Januari 2020 UJI")
    Observation.objects.create(indicator=Indicator.objects.get(code="birate"), source=source, raw_file=lifecycle_raw,
        observation_date=date(2020, 1, 31), period_label="Januari 2020 UJI", frequency="monthly", data_type="level",
        value=Decimal("5"), unit="%", validation_status="published", reviewed_by=reviewer, reviewed_at=timezone.now())
    manifest = {"synthetic": True, "rawPath": raw.stored_path, "rawSha256": raw.checksum_sha256,
                "rawContent": payload.decode(), "rawUrl": f"http://localhost:8000/api/indicators/inflasi/raw-file/{raw.pk}/",
                "oldestValueDisplay": "2,123456", "oldestPeriod": "Februari 1998", "rows": 24,
                "exactValue": exact_value, "exactDisplay": "999.999.999.999.999.999,999999",
                "lifecycleRawUrl": f"http://localhost:8000/api/indicators/birate/raw-file/{lifecycle_raw.pk}/",
                "lifecycleRawSha256": lifecycle_raw.checksum_sha256}
    path = owned / "fixture.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def run(frontend):
    scratch = Path(os.environ["HERMES_TEST_SCRATCH"]).resolve()
    assert scratch.is_dir() and (frontend / "package.json").is_file()
    for port in [8000, 5196]:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    owned = Path(tempfile.mkdtemp(prefix="deksi-be-live-", dir=scratch))
    output = BACKEND / ".artifacts" / "live-integration"
    output.mkdir(parents=True, exist_ok=True)
    server = None
    os.environ.update(DEKSI_TEST_DATABASE=str(owned / "integration.sqlite3"),
                      DEKSI_TEST_RAW_ROOT=str(owned / "raw"),
                      DEKSI_TEST_FE_ORIGIN="http://127.0.0.1:5196")
    try:
        configure()
        from django.core.management import call_command
        with (output / "migrate.log").open("w", encoding="utf-8") as migration_log:
            call_command("migrate", interactive=False, stdout=migration_log, stderr=migration_log)
        fixture = seed(owned)
        with (output / "django.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, str(BACKEND / "manage.py"), "runserver",
                "127.0.0.1:8000", "--noreload", "--settings=backend.test_settings_indicators"],
                cwd=BACKEND, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT)
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError("Owned backend exited before readiness; inspect django.log")
                try:
                    url = "http://localhost:8000/api/indicators/?code=inflasi"
                    with urllib.request.urlopen(url, timeout=1) as response:
                        assert json.load(response)["indicators"][0]["value"] == "0"
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Owned backend readiness deadline exceeded")
            env = os.environ.copy()
            env.update(DEKSI_QA_FRONTEND=str(frontend), DEKSI_QA_FIXTURE=str(fixture),
                       DEKSI_QA_OUTPUT=str(output), DEKSI_QA_PYTHON=sys.executable)
            result = subprocess.run(["node", str(Path(__file__).with_name("frontend-integration.mjs"))],
                                    cwd=BACKEND, env=env, timeout=180, check=False)
            if result.returncode:
                raise RuntimeError(f"Actual frontend integration failed, exit={result.returncode}; inspect artifacts")
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        # Release the runner-owned connection before removing SQLite on Windows.
        with contextlib.suppress(ImportError):
            from django.db import connections
            connections.close_all()
        shutil.rmtree(owned)
    receipt = json.loads((output / "verification.json").read_text(encoding="utf-8"))
    receipt["scratch_database_removed"] = not owned.exists()
    receipt["owned_backend_stopped"] = server is not None and server.poll() is not None
    receipt["python"] = sys.version
    receipt["frontend_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=frontend, text=True).strip()
    receipt["backend_source_sha256"] = {
        f"indicators/{name}": hashlib.sha256((BACKEND / "indicators" / name).read_bytes()).hexdigest()
        for name in ["views.py", "storage.py", "provenance.py"]}
    (output / "verification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    assert receipt["scratch_database_removed"] and receipt["owned_backend_stopped"]
    print(json.dumps({"integration_checks": len(receipt["checks"]), "errors": receipt["errors"],
                      "scratch_database_removed": True, "owned_backend_stopped": True,
                      "receipt": str(output / "verification.json")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-root", type=Path)
    parser.add_argument("--set-value", choices=["0", "9"])
    parser.add_argument("--lifecycle-action", choices=["stage6", "stage7", "reject6", "fail7", "publish7"])
    args = parser.parse_args()
    if args.lifecycle_action:
        lifecycle_action(args.lifecycle_action)
    elif args.set_value is not None:
        set_value(args.set_value)
    elif args.frontend_root:
        run(args.frontend_root.resolve())
    else:
        parser.error("--frontend-root is required")
