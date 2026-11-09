from django.db import transaction

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


def ingest_kita_pdf_url(url: str) -> dict:
    pdf_bytes, parsed = kemenkeu.fetch_and_parse(url)
    if parsed.cumulative_until is None:
        raise kemenkeu.KitaError("periode kumulatif tidak teridentifikasi pada dokumen; data tidak disimpan")
    with transaction.atomic():
        return _store_parsed_result(url, pdf_bytes, parsed)


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
