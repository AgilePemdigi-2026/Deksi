import calendar
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

INDONESIAN_MONTHS = {
    "januari": 1,
    "jan": 1,
    "februari": 2,
    "feb": 2,
    "maret": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mei": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "agustus": 8,
    "agu": 8,
    "ags": 8,
    "september": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "november": 11,
    "nov": 11,
    "desember": 12,
    "des": 12,
}


def normalize_text(value) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def parse_id_number(text: str) -> Decimal | None:
    text = normalize_text(text)
    if not text:
        return None
    text = text.replace("%", "").replace("Rp", "").replace(" ", "")
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if "," in text:
        cleaned = text.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    elif "." in text:
        integer_part, _, frac = text.rpartition(".")
        if frac and all(ch.isdigit() for ch in frac) and len(frac) == 3 and integer_part.isdigit() and integer_part:
            cleaned = (integer_part + frac).replace(".", "")
        elif frac and len(frac) != 3:
            cleaned = text
        else:
            cleaned = text.replace(".", "")
    else:
        cleaned = text
    cleaned = cleaned.lstrip("-")
    try:
        result = Decimal(cleaned)
    except InvalidOperation:
        return None
    if negative:
        result = -result
    return result


def parse_indonesian_date(text: str) -> date | None:
    text = normalize_text(text).lower()
    match = re.match(r"^(\d{1,2})\s+([a-z]+\.?)\s+(\d{4})$", text)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = INDONESIAN_MONTHS.get(month_name.rstrip("."))
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def parse_mdy_date(text: str) -> date | None:
    text = normalize_text(text)
    if not text:
        return None
    date_part = text.split(" ")[0]
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_part)
    if not match:
        return None
    month, day, year = (int(p) for p in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def quarter_label_to_date(label: str) -> date | None:
    text = normalize_text(label).lower()
    match = re.match(r"^(\d{4})\s*-\s*triwulan\s*(\d)$", text)
    if not match:
        return None
    year, quarter = int(match.group(1)), int(match.group(2))
    if quarter < 1 or quarter > 4:
        return None
    month = quarter * 3
    return date(year, month, calendar.monthrange(year, month)[1])


def parse_bi7day_rate(value_text, date_text) -> dict | None:
    raw_number = parse_id_number(value_text)
    observation_date = parse_indonesian_date(date_text)
    if raw_number is None or observation_date is None:
        return None
    if Decimal("0") > raw_number or raw_number > Decimal("50"):
        return None
    return {
        "observation_date": observation_date,
        "value": raw_number,
        "unit": "%",
        "period_label": normalize_text(date_text),
    }


def parse_jisdor(value_text, date_text) -> dict | None:
    raw_number = parse_id_number(value_text)
    observation_date = parse_mdy_date(date_text)
    if raw_number is None or observation_date is None:
        return None
    if raw_number <= 0 or raw_number > 1_000_000:
        return None
    return {
        "observation_date": observation_date,
        "value": raw_number,
        "unit": "Rp/USD",
        "period_label": observation_date.isoformat(),
    }


def parse_dot_decimal(text) -> Decimal | None:
    """Angka desimal titik internasional (contoh 9.481 = 9,481 juta), bukan pemisah ribuan.

    Dipakai untuk CSV BKPM dan XLSX Indikator Moneter yang menulis desimal
    dengan titik. JANGAN pakai parse_id_number di sini: titik tiga digit
    akan dibaca sebagai pemisah ribuan (9.481 -> 9481).
    """
    value = normalize_text(text)
    if not value:
        return None
    cleaned = value.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_bkpm_number(text) -> Decimal | None:
    """Angka kolom investasi_rp_juta lintas format file BKPM.

    File 2025 memakai desimal titik ("2264.22241"); file 2026 memakai
    desimal koma ("11368,60677"). Aturan:
    - ada koma dan titik -> format Indonesia (titik ribuan, koma desimal);
    - hanya koma -> koma adalah desimal;
    - hanya titik satu -> desimal titik; titik lebih dari satu -> ribuan.
    """
    value = normalize_text(text)
    if not value:
        return None
    if "," in value and "." in value:
        cleaned = value.replace(".", "").replace(",", ".")
    elif "," in value:
        cleaned = value.replace(",", ".")
    elif value.count(".") > 1:
        cleaned = value.replace(".", "")
    else:
        cleaned = value
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_bkpm_rp_juta(text) -> Decimal | None:
    """BKPM CSV: delegasi ke parse_bkpm_number yang tahan format campuran."""
    return parse_bkpm_number(text)
