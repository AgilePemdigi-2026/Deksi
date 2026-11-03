"""Combined application stack; only disposable SQLite and locmem are allowed."""

import os
from pathlib import Path

if (Path(__file__).resolve().parent.parent / ".env").exists():
    raise RuntimeError("Combined tests must not load an application's .env")

from . import test_settings_reset as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
_scratch = Path(os.environ["HERMES_TEST_SCRATCH"]).resolve()
_raw = Path(os.environ["DEKSI_TEST_RAW_ROOT"]).resolve()
if not _raw.is_relative_to(_scratch) or not _raw.name.startswith("sprint1-unified-"):
    raise ValueError("Raw fixture root must be task-owned under the approved scratch directory")
DEKSI_RAW_DIR = _raw
DEKSI_MAX_RAW_BYTES = 32 * 1024 * 1024
