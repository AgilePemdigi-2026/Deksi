"""Local Docker settings: persist SQLite independently of the application image."""

from pathlib import Path

from . import settings as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/data/db.sqlite3"}}
DEKSI_RAW_DIR = Path("/data/raw_storage")
