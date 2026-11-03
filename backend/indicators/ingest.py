import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import parsing
from .lifecycle import ensure_import_master, stage_observation
from .models import Indicator, RawFile, Source
from .storage import save_raw_from_path

BI_SOURCE, _ = None, None


def get_or_create_source(source_id, source_name, institution, primary_url, description=""):
    source = ensure_import_master(Source,
        source_id=source_id,
        defaults={
            "source_name": source_name,
            "institution": institution,
            "primary_url": primary_url,
            "description": description,
        },
    )
    return source


def get_or_create_indicator(code, name, category, unit, aggregation_kind, sort_order):
    indicator = ensure_import_master(Indicator,
        code=code,
        defaults={
            "name": name,
            "category": category,
            "unit": unit,
            "aggregation_kind": aggregation_kind,
            "sort_order": sort_order,
        },
    )
    return indicator


def upsert_bi_observations(obs_dicts: list[dict]):
    count = 0
    for obs in obs_dicts:
        stage_observation(**obs)
        count += 1
    return count


def ingest_local_datasets(scraping_dir: Path | None = None) -> dict:
    from django.conf import settings as django_settings

    if scraping_dir is None:
        default_dir = django_settings.BASE_DIR / ".." / ".." / "Folder Scrapping"
        scraping_dir = Path(getattr(django_settings, "DEKSI_SCRAPING_DIR", default_dir))
    scraping_dir = Path(scraping_dir)
    if not scraping_dir.exists():
        raise FileNotFoundError(f"scraping dir not found: {scraping_dir}")

    bi_source = get_or_create_source(
        "BI",
        "Bank Indonesia Dataset",
        "Bank Indonesia",
        "https://www.bi.go.id/",
        "Hasil pengambilan data dataset BI (BI-7Day-RR, Indikator Moneter, Kurs JISDOR).",
    )
    bkpm_source = get_or_create_source(
        "BKPM",
        "Realisasi Investasi BKPM",
        "Kementerian Investasi/BKPM",
        "https://realisasiinvestasi.id/",
        "Dataset realisasi investasi triwulanan PMA/PMDN tingkat nasional.",
    )

    created_bi = 0
    created_bkpm = 0
    errors = []

    for path in sorted(scraping_dir.glob("*.xlsx")):
        name_lower = path.name.lower()
        raw_file, is_new = save_raw_from_path(
            bi_source,
            path,
            path.name,
            source_url="file://Folder Scrapping/" + path.name,
            period_label="",
        )
        try:
            if "bi-7day-rr" in name_lower:
                obs = parse_bi_rr_xlsx(path, raw_file, bi_source)
                created_bi += upsert_bi_observations(obs)
            elif "jisdor" in name_lower:
                obs = parse_jisdor_xlsx(path, raw_file, bi_source)
                created_bi += upsert_bi_observations(obs)
            elif "indikator-moneter" in name_lower or "indikator moneter" in name_lower:
                obs = parse_moneter_xlsx(path, raw_file, bi_source)
                created_bi += upsert_bi_observations(obs)
            else:
                raise ValueError(f"unknown BI dataset type: {path.name}")
            if is_new:
                raw_file.parse_status = RawFile.ParseStatus.PARSED
                raw_file.save(update_fields=["parse_status"])
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            if is_new:
                raw_file.parse_error = str(exc)
                raw_file.parse_status = RawFile.ParseStatus.FAILED
                raw_file.save(update_fields=["parse_error", "parse_status"])

    for path in sorted(scraping_dir.glob("*.zip")):
        try:
            quarter_date = bkpm_quarter_date_from_filename(path.name)
            if quarter_date is None:
                raise ValueError(f"cannot parse period from filename: {path.name}")
            period_label = bkpm_period_label_from_filename(path.name)
            raw_file, is_new = save_raw_from_path(
                bkpm_source,
                path,
                path.name,
                source_url="file://Folder Scrapping/" + path.name,
                period_label=period_label,
            )
            total = sum_bkpm_zip_csv(path)
            indicator = get_or_create_indicator(
                "investasi",
                "Realisasi Investasi",
                "Rencana Modal",
                "Rp Triliun",
                "sum",
                4,
            )
            value_rp_triliun = (total / Decimal(1000000)).normalize()
            stage_observation(indicator_id=indicator.pk, source_id=bkpm_source.pk,
                observation_date=quarter_date, data_type="derived_sum", period_label=period_label,
                frequency="quarterly", value=value_rp_triliun, unit="Rp Triliun", raw_file_id=raw_file.pk)
            created_bkpm += 1
            if is_new:
                raw_file.parse_status = RawFile.ParseStatus.PARSED
                raw_file.save(update_fields=["parse_status"])
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            raw = RawFile.objects.filter(document_name=path.name, source=bkpm_source).first()
            if raw is not None:
                raw.parse_error = str(exc)
                raw.parse_status = RawFile.ParseStatus.FAILED
                raw.save(update_fields=["parse_error", "parse_status"])

    return {
        "bi_rows": created_bi,
        "bkpm_quarters": created_bkpm,
        "errors": errors,
        "scraping_dir": str(scraping_dir),
    }


def parse_bi_rr_xlsx(path: Path, raw_file, source) -> list[dict]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        ws = wb.worksheets[0]
        rows = list(ws.values)
    finally:
        wb.close()
    indicator = get_or_create_indicator(
        "birate",
        "BI-Rate (BI-7Day Repurchase Rate)",
        "Kebijakan Moneter",
        "%",
        "avg",
        5,
    )
    results = []
    for row in rows:
        no, date_text, value_text = (row[0], row[1], row[2]) if len(row) >= 3 else (None, None, None)
        if str(no).strip() in ("", "None") or normalize_none(date_text) is None:
            continue
        parsed = None
        if isinstance(date_text, str) and str(no).strip().isdigit():
            parsed = parsing.parse_bi7day_rate(value_text, date_text)
            if parsed is None:
                raise ValueError(f"unparseable BI-7Day-RR row: {date_text!r} / {value_text!r}")
        if parsed is None:
            continue
        parsed.update(
            {
                "indicator_id": indicator.id,
                "source_id": source.id,
                "frequency": "adhoc",
                "data_type": "event",
                "raw_file_id": raw_file.id,
            }
        )
        results.append(parsed)
    if not results:
        raise ValueError(f"no BI-7Day-RR rows parsed from {path.name}")
    return results


def parse_jisdor_xlsx(path: Path, raw_file, source) -> list[dict]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        ws = wb.worksheets[0]
        rows = list(ws.values)
    finally:
        wb.close()
    indicator = get_or_create_indicator(
        "jisdor",
        "Kurs Referensi (JISDOR)",
        "Kebijakan Moneter",
        "Rp/USD",
        "avg",
        6,
    )
    results = []
    for row in rows:
        no, date_text, value_text = (row[0], row[1], row[2]) if len(row) >= 3 else (None, None, None)
        if str(no).strip() in ("", "None") or normalize_none(date_text) is None:
            continue
        parsed = None
        if isinstance(date_text, str) and str(no).strip().isdigit():
            parsed = parsing.parse_jisdor(value_text, date_text)
            if parsed is None:
                raise ValueError(f"unparseable JISDOR row: {date_text!r} / {value_text!r}")
        if parsed is None:
            continue
        parsed.update(
            {
                "indicator_id": indicator.id,
                "source_id": source.id,
                "frequency": "daily",
                "data_type": "level",
                "raw_file_id": raw_file.id,
            }
        )
        results.append(parsed)
    if not results:
        raise ValueError(f"no JISDOR rows parsed from {path.name}")
    return results


def parse_moneter_xlsx(path: Path, raw_file, source) -> list[dict]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        ws = wb.worksheets[0]
        rows = list(ws.values)
    finally:
        wb.close()
    indicator = get_or_create_indicator(
        "cad_devisa",
        "Cadangan Devisa",
        "Kebijakan Moneter",
        "",
        "end",
        7,
    )
    results = []
    for row in rows:
        no, day, value_text = (row[0], row[1], row[2]) if len(row) >= 3 else (None, None, None)
        if str(no).strip() in ("", "None") or normalize_none(value_text) is None:
            continue
        observation_date = day.date() if hasattr(day, "date") else None
        value = parsing.parse_id_number(value_text) if isinstance(value_text, str) else None
        if str(no).strip().isdigit() and (observation_date is None or value is None):
            raise ValueError(f"unparseable Indikator Moneter row: {day!r} / {value_text!r}")
        if observation_date is None or value is None:
            continue
        results.append(
            {
                "observation_date": observation_date,
                "period_label": observation_date.isoformat(),
                "value": value,
                "unit": "",
                "indicator_id": indicator.id,
                "source_id": source.id,
                "frequency": "monthly",
                "data_type": "level",
                "raw_file_id": raw_file.id,
            }
        )
    if not results:
        raise ValueError(f"no Indikator Moneter rows parsed from {path.name}")
    return results


def bkpm_quarter_date_from_filename(filename: str) -> date | None:
    import re

    match = re.search(r"triwulan-(i{1,3}|iv)-tahun-(\d{4})", filename.lower())
    if not match:
        return None
    roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4}[match.group(1)]
    year = int(match.group(2))
    month = roman * 3
    import calendar

    return date(year, month, calendar.monthrange(year, month)[1])


def bkpm_period_label_from_filename(filename: str) -> str | None:
    import re

    match = re.search(r"triwulan-(i{1,3}|iv)-tahun-(\d{4})", filename.lower())
    if not match:
        return None
    roman_labels = {"i": "I", "ii": "II", "iii": "III", "iv": "IV"}
    return f"Triwulan {roman_labels[match.group(1)]} {match.group(2)}"


def sum_bkpm_zip_csv(zip_path: Path) -> Decimal:
    total = Decimal(0)
    row_count = 0
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("no csv inside BKPM zip")
        with archive.open(csv_names[0]) as fh:
            import csv
            import io

            text = io.TextIOWrapper(fh, encoding="utf-8-sig").read()
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;")
            reader = csv.reader(text.splitlines(), dialect)
            header = next(reader)
            if "investasi_rp_juta" not in header:
                raise ValueError(f"investasi_rp_juta column missing in {csv_names[0]}")
            col_index = header.index("investasi_rp_juta")
            for row in reader:
                if len(row) <= col_index:
                    continue
                raw = row[col_index].strip()
                if raw == "":
                    continue
                value = parsing.parse_id_number(raw)
                if value is None:
                    raise ValueError(f"unparseable BKPM value: {raw!r}")
                total += value
                row_count += 1
    if row_count == 0:
        raise ValueError("BKPM csv has no data rows")
    return total


def normalize_none(value) -> str | None:
    if value is None:
        return None
    if str(value).strip() == "":
        return None
    return str(value)
