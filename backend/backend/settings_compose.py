"""Docker Compose settings for the host PostgreSQL and persistent raw storage."""

from pathlib import Path

from . import settings as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
DEKSI_RAW_DIR = Path("/data/raw_storage")
