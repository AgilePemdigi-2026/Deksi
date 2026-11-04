"""Run selected original BDD scenarios against pinned, read-only product copies."""
import argparse
import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path

import sys
import tempfile

sys.dont_write_bytecode = True
QA = Path(__file__).resolve().parent
ROOT = QA.parent
BE = ROOT / "backend-checkpoint" / "backend"
SCRATCH = Path("C:/Users/Pongo/AppData/Local/hermes/cache/scratch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", default="@BDD_F03_05 or @BDD_F03_01")
    parser.add_argument("--label", default="pilot")
    args = parser.parse_args()
    if not args.label.replace("-", "").replace("_", "").isalnum():
        parser.error("label must be alphanumeric")
    if (BE / ".env").exists():
        raise RuntimeError("Refusing an application .env")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    artifacts = QA / "artifacts" / f"{stamp}-{args.label}"
    artifacts.mkdir(parents=True, exist_ok=False)
    sys.path[:0] = [str(QA), str(BE)]
    blocked = []

    def audit(event, values):
        if event == "socket.connect":
            address = values[1]
            if not isinstance(address, tuple):
                raise RuntimeError("Non-IP socket outside BDD scope")
            host = str(address[0])
            if host == "localhost":
                return
            try:
                safe = ipaddress.ip_address(host).is_loopback
            except ValueError:
                safe = False
            if not safe:
                blocked.append({"event": event, "host": host})
                raise RuntimeError("BDD prohibits non-loopback connections")
        elif event == "socket.getaddrinfo":
            host = values[0]
            if host not in (None, "localhost", "127.0.0.1", "::1"):
                blocked.append({"event": event, "host": str(host)})
                raise RuntimeError("BDD prohibits external DNS")

    sys.addaudithook(audit)
    result = 1
    with tempfile.TemporaryDirectory(prefix="deksi-bdd-", dir=SCRATCH) as temporary:
        run_dir = Path(temporary)
        raw = run_dir / "sprint1-unified-bdd-raw"
        raw.mkdir()
        os.environ.update({
            "DJANGO_SETTINGS_MODULE": "bdd_settings",
            "SECRET_KEY": "synthetic-bdd-fixture-key-not-for-production",
            "DEBUG": "False",
            "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
            "BPS_API_KEY": "",
            "BPS_API_BASE_URL": "http://127.0.0.1:9/provider-disabled",
            "HERMES_TEST_SCRATCH": str(SCRATCH),
            "DEKSI_TEST_RAW_ROOT": str(raw),
            "DEKSI_BDD_RUN_DIR": str(run_dir),
            "DEKSI_BDD_ARTIFACTS": str(artifacts),
            "TMPDIR": str(run_dir), "TEMP": str(run_dir), "TMP": str(run_dir),
            "SE_OFFLINE": "true", "PYTHONDONTWRITEBYTECODE": "1",
        })
        os.environ.pop("PYTHONPATH", None)
        os.environ.pop("PYTHONHOME", None)
        command = ["manage.py", "behave", str(QA / "features"), "--noinput",
                   "--tags", args.tags, "--format", "json", "--outfile",
                   str(artifacts / "behave.json"), "--format", "pretty", "--outfile", "-", "--no-capture", "--no-skipped"]
        print("ARTIFACTS", artifacts, flush=True)
        print("BDD selected", args.tags, flush=True)
        try:
            sys.argv = command
            from django.core.management import execute_from_command_line
            execute_from_command_line(command)
            result = 0
        except SystemExit as exc:
            result = int(exc.code or 0)
        finally:
            from django.db import connections
            connections.close_all()
            # Closing only task-owned SQLite connections before disposable directory teardown.
            db_left = (run_dir / "test.sqlite3").exists()
            payload = {
                "exit_code": result, "tags": args.tags, "command": command,
                "interpreter": sys.executable,
                "database": "disposable file-backed SQLite created/destroyed by Behave-Django",
                "test_database_file_remaining_before_cleanup": db_left,
                "mailer": "locmem only; no real email",
                "external_connections_blocked": blocked,
                "browser_engine": "installed Chrome via CDP (NON-Selenium); no API mocks",
                "product_changes": "NONE", "visual_review": "PENDING",
                "qa_hashes": {str(p.relative_to(QA)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in QA.rglob("*.py") if "artifacts" not in p.parts},
            }
            (artifacts / "run.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print("RUN_EXIT", result, flush=True)
    assert not run_dir.exists(), "Disposable run directory was not removed"
    (artifacts / "cleanup.json").write_text(json.dumps({
        "disposable_run_directory_removed": True,
        "product_db_used": False,
    }), encoding="utf-8")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
