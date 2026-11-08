"""Explicit file-backed SQLite test DB, strictly inside the approved scratch root."""

import os
from pathlib import Path

from . import test_settings_reset as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
_scratch = Path(os.environ["HERMES_TEST_SCRATCH"]).resolve()
_database = Path(os.environ["DEKSI_RESET_TEST_DB"]).resolve()
if not _database.is_relative_to(_scratch) or not _database.name.startswith("reset-concurrency-"):
    raise ValueError("Concurrency DB must be an owned reset-concurrency-* file under approved scratch")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": str(_database)},
        "OPTIONS": {"timeout": 20},
    }
}
