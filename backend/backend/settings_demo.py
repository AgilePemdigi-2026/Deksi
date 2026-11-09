"""Isolated local-only demo database; never use for real or official data."""

from . import settings_docker as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/data/deksi-demo.sqlite3"}}
DEKSI_SYNTHETIC_DEMO = True
