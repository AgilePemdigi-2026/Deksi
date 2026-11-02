import hashlib
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings

from .models import RawFile, Source


def raw_storage_root() -> Path:
    root = Path(getattr(settings, "DEKSI_RAW_DIR", settings.BASE_DIR / "raw_storage"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_raw(
    source: Source, content: bytes, original_name: str, source_url: str = "", period_label: str = ""
) -> tuple[RawFile, bool]:
    checksum = compute_checksum(content)
    existing = RawFile.objects.filter(source=source, checksum_sha256=checksum).first()
    if existing is not None:
        return existing, False
    retrieved_at = datetime.now(UTC)
    stored_dir = raw_storage_root() / source.source_id.lower() / retrieved_at.strftime("%Y%m%d")
    stored_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in (".", "-", "_") else "_" for ch in original_name)
    stored_path = stored_dir / safe_name
    stored_path.write_bytes(content)
    raw_file = RawFile.objects.create(
        source=source,
        document_name=original_name,
        source_url=source_url,
        period_label=period_label,
        retrieved_at=retrieved_at,
        checksum_sha256=checksum,
        stored_path=str(stored_path),
        file_size_bytes=len(content),
    )
    return raw_file, True


def save_raw_from_path(
    source: Source,
    local_path: Path,
    document_name: str,
    source_url: str = "",
    period_label: str = "",
) -> tuple[RawFile, bool]:
    content = local_path.read_bytes()
    return save_raw(source, content, document_name, source_url=source_url, period_label=period_label)
