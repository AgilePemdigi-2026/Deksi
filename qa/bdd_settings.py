"""Test-only configuration; product settings and security middleware stay intact."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend-checkpoint" / "backend"
if (BACKEND / ".env").exists():
    raise RuntimeError("BDD refuses application .env")

from backend import test_settings_sprint1 as baseline  # noqa: E402

globals().update({k: getattr(baseline, k) for k in dir(baseline) if k.isupper()})
RUN_DIR = Path(os.environ["DEKSI_BDD_RUN_DIR"]).resolve()
SCRATCH = Path(os.environ["HERMES_TEST_SCRATCH"]).resolve()
if not RUN_DIR.is_relative_to(SCRATCH) or not RUN_DIR.name.startswith("deksi-bdd-"):
    raise RuntimeError("Only task-owned disposable storage is allowed")
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    # A file-backed initial connection can be closed when Django switches to TEST.NAME.
    # Starting at :memory: can retain a pre-opened private connection across that switch.
    "NAME": str(RUN_DIR / "unused-default.sqlite3"),
    "TEST": {"NAME": str(RUN_DIR / "test.sqlite3")},
}}
DEKSI_RAW_DIR = RUN_DIR / "raw"
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
ADMIN_PASSWORD_RESET_ENABLED = True
MIDDLEWARE = ["journal.RequestJournal", *baseline.MIDDLEWARE]
# Same-origin Vite proxy preserves Host; no cross-origin bypass/CSRF exemption.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
assert "django.middleware.csrf.CsrfViewMiddleware" in MIDDLEWARE
assert baseline.CSRF_COOKIE_HTTPONLY
