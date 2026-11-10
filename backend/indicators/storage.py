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


def verified_raw_bytes(raw_file: RawFile) -> bytes:
    root = Path(settings.DEKSI_RAW_DIR).resolve(strict=True)
    stored = Path(raw_file.stored_path).absolute()
    candidate = stored.resolve(strict=True)
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise FileNotFoundError("RAW tidak berada dalam penyimpanan yang diizinkan")
    for part in (stored, *stored.parents):
        if part == root:
            break
        if part.is_symlink() or part.is_junction():
            raise FileNotFoundError("Tautan filesystem bukan RAW publik")
    maximum = getattr(settings, "DEKSI_MAX_RAW_BYTES", 32 * 1024 * 1024)
    with candidate.open("rb") as handle:
        content = handle.read(maximum + 1)
    if (len(content) > maximum or len(content) != raw_file.file_size_bytes
            or compute_checksum(content) != raw_file.checksum_sha256):
        raise ValueError("Ukuran atau checksum RAW tidak sesuai")
    return content


def save_raw(
    source: Source, content: bytes, original_name: str, source_url: str = "", period_label: str = ""
) -> tuple[RawFile, bool]:
    maximum = getattr(settings, "DEKSI_MAX_RAW_BYTES", 32 * 1024 * 1024)
    if len(content) > maximum:
        raise ValueError("Berkas RAW melebihi batas penyimpanan")
    checksum = compute_checksum(content)
    existing = RawFile.objects.filter(source=source, checksum_sha256=checksum).first()
    if existing is not None:
        try:
            verified_raw_bytes(existing)
        except FileNotFoundError:
            # Baris lama menunjuk path yang sudah tidak ada (mis. skema
            # penyimpanan lama). Tulis ulang isi ke path skema baru dan
            # perbaiki penunjuknya; riwayat baris tetap.
            # Checksum MISMATCH (ValueError) TIDAK ditangani di sini:
            # itu tanda pemalsuan dan harus tetap melempar error.
            root = raw_storage_root().resolve()
            stored_dir = root / f"source-{source.pk}"
            stored_dir.mkdir(parents=True, exist_ok=True)
            stored_path = stored_dir / f"{checksum}.raw"
            try:
                with stored_path.open("xb") as handle:
                    handle.write(content)
            except FileExistsError:
                pass
            existing.stored_path = str(stored_path)
            existing.file_size_bytes = len(content)
            existing.save(update_fields=["stored_path", "file_size_bytes"])
        return existing, False
    retrieved_at = datetime.now(UTC)
    root = raw_storage_root().resolve()
    stored_dir = root / f"source-{source.pk}"
    stored_dir.mkdir(parents=True, exist_ok=True)
    if stored_dir.is_symlink() or stored_dir.is_junction() or not stored_dir.resolve().is_relative_to(root):
        raise ValueError("Penyimpanan RAW tidak aman")
    stored_path = stored_dir / f"{checksum}.raw"
    created_file = False
    try:
        with stored_path.open("xb") as handle:
            created_file = True
            handle.write(content)
    except FileExistsError:
        candidate = RawFile(stored_path=str(stored_path), checksum_sha256=checksum, file_size_bytes=len(content))
        verified_raw_bytes(candidate)
    except OSError:
        # Remove only the partially written file created by this call, never a preexisting RAW.
        if created_file:
            stored_path.unlink(missing_ok=True)
        raise
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
    maximum = getattr(settings, "DEKSI_MAX_RAW_BYTES", 32 * 1024 * 1024)
    with local_path.open("rb") as handle:
        content = handle.read(maximum + 1)
    return save_raw(source, content, document_name, source_url=source_url, period_label=period_label)
