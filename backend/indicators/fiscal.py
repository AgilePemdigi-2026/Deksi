from django.conf import settings
from django.utils import timezone

from . import kemenkeu
from .lifecycle import ensure_import_master, stage_observation
from .models import Indicator, RawFile, Source
from .storage import save_raw

KEMENKEU_META = {
    "source_name": "APBN Kinerja dan Tindak Lanjut (APBN KiTa)",
    "institution": "Kementerian Keuangan RI",
    "primary_url": "https://djppr.kemenkeu.go.id/apbnkita",
}

METRIC_INDICATORS = [
    ("pendapatan_negara", "Pendapatan Negara (Realisasi Kumulatif)",
     "Fiskal & Keuangan Negara", "Rp Triliun", "end", 3),
    ("belanja_negara", "Belanja Negara (Realisasi Kumulatif)", "Fiskal & Keuangan Negara", "Rp Triliun", "end", 4),
    ("defisit_apbn", "Defisit APBN (Nominal)", "Fiskal & Keuangan Negara", "Rp Triliun", "end", 5),
    ("defisit_pdb", "Defisit APBN", "Fiskal & Keuangan Negara", "% PDB", "end", 5),
]

INDICATOR_CODE_OVERRIDES = {"defisit_pdb": "fiskal"}


def get_kemenkeu_source() -> Source:
    source = ensure_import_master(Source,
        source_id="KEMENKEU",
        defaults={
            "source_name": KEMENKEU_META["source_name"],
            "institution": KEMENKEU_META["institution"],
            "primary_url": KEMENKEU_META["primary_url"],
            "description": ("Publikasi APBN KiTa (PDF resmi Kemenkeu), "
                            "realisasi kumulatif pendapatan, belanja, defisit."),
        },
    )
    return source


def get_fiscal_indicators() -> dict[str, Indicator]:
    result = {}
    for code, name, category, unit, aggregation, order in METRIC_INDICATORS:
        result[code] = ensure_import_master(Indicator,
            code=INDICATOR_CODE_OVERRIDES.get(code, code),
            defaults={
                "name": name,
                "category": category,
                "unit": unit,
                "aggregation_kind": aggregation,
                "sort_order": order,
            },
        )
    return result


def ingest_kita_pdf_url(url: str, scrap_dir=None, no_scrap_copy: bool = False) -> dict:
    pdf_bytes, parsed = kemenkeu.fetch_and_parse(url)
    if parsed.cumulative_until is None:
        raise kemenkeu.KitaError("periode kumulatif tidak teridentifikasi pada dokumen; data tidak disimpan")
    result = _store_parsed_result(url, pdf_bytes, parsed)
    if not no_scrap_copy:
        result["scrap_copy"] = archive_to_scraping_dir(
            pdf_bytes, result["document_name"], url,
            result["period_label"], result["checksum"], scrap_dir=scrap_dir,
        )
    return result


def _store_parsed_result(url: str, pdf_bytes: bytes, parsed) -> dict:
    source = get_kemenkeu_source()
    document_name = kemenkeu.suggested_document_name(parsed)
    raw_file, is_new = save_raw(
        source, pdf_bytes, document_name,
        source_url=url,
        period_label=parsed.period_label,
    )
    if is_new:
        raw_file.parse_status = RawFile.ParseStatus.PARSED
        raw_file.save(update_fields=["parse_status"])
    indicators = get_fiscal_indicators()
    stored = []
    for identifier, metric in parsed.metrics.items():
        indicator = indicators.get(identifier)
        if indicator is None:
            continue
        stage_observation(indicator_id=indicator.pk, source_id=source.pk,
            observation_date=parsed.cumulative_until, data_type="cumulative_ytd", period_label=parsed.period_label,
            frequency="monthly", value=metric.value, unit=metric.unit,
            publication_date=parsed.publication_date, raw_file_id=raw_file.pk)
        stored.append(f"{identifier}={metric.value} {metric.unit}")
    return {
        "document_name": document_name,
        "period_label": parsed.period_label,
        "publication_date": parsed.publication_date.isoformat() if parsed.publication_date else None,
        "metrics": stored,
        "raw_file_id": raw_file.id,
        "checksum": raw_file.checksum_sha256,
    }


def resolve_scraping_dir(scrap_dir=None):
    from pathlib import Path

    if scrap_dir:
        target = Path(scrap_dir)
    else:
        target = Path(getattr(settings, "DEKSI_SCRAPING_DIR", Path(".")))
    target.mkdir(parents=True, exist_ok=True)
    return target


def archive_to_scraping_dir(pdf_bytes: bytes, document_name: str, url: str,
                            period_label: str, checksum: str, scrap_dir=None) -> dict:
    """Salin PDF edisi KiTa ke Folder Scrapping + file sidecar provenance."""
    from .storage import compute_checksum

    target = resolve_scraping_dir(scrap_dir)
    if compute_checksum(pdf_bytes) != checksum:
        raise kemenkeu.KitaError("checksum PDF berubah antara unduh dan arsip; dibatalkan")
    pdf_path = target / document_name
    if not pdf_path.exists():
        pdf_path.write_bytes(pdf_bytes)
    sidecar = target / f"{document_name}.sumber.txt"
    sidecar.write_text(
        "Sumber resmi: Kementerian Keuangan RI, publikasi APBN KiTa.\n"
        f"URL: {url}\n"
        f"Periode data: {period_label}\n"
        f"SHA-256: {checksum}\n"
        f"Ukuran: {len(pdf_bytes)} bytes.\n"
        f"Diarsipkan: {timezone.now().isoformat()}.\n",
        encoding="utf-8",
    )
    return {"pdf": str(pdf_path), "sidecar": str(sidecar)}
