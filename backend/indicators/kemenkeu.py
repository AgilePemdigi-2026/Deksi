import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx


DEFAULT_KITA_URLS = [
    "https://media.kemenkeu.go.id/getmedia/044b5248-bdb9-4434-adf7-62fd50e93f3d/Publikasi-Web-Konpers-APBN-KiTa-(Oktober-2026)-(1).pdf?ext=.pdf",
]

PDF_MAGIC = b"%PDF"

INDONESIAN_MONTHS = {
    "januari": 1, "jan": 1, "februari": 2, "feb": 2, "maret": 3, "mar": 3,
    "april": 4, "apr": 4, "mei": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "ags": 8, "september": 9, "sep": 9,
    "oktober": 10, "okt": 10, "november": 11, "nov": 11, "desember": 12, "des": 12,
}

MONTH_NAMES_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}


class KitaError(Exception):
    pass


@dataclass
class KitaMetric:
    identifier: str
    value: Decimal
    unit: str
    matched_label: str


@dataclass
class KitaResult:
    source_url: str
    cumulative_until: date | None
    period_label: str
    publication_date: date | None
    metrics: dict[str, KitaMetric] = field(default_factory=dict)
    text: str = ""


def fetch_kita_pdf(url: str, client: httpx.Client | None = None) -> bytes:
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=180, follow_redirects=True)
    try:
        response = client.get(url)
        response.raise_for_status()
    finally:
        if own_client:
            client.close()
    if not response.content.startswith(PDF_MAGIC):
        raise KitaError(f"file not a valid PDF from {url}")
    if len(response.content) < 1024:
        raise KitaError(f"PDF too small ({len(response.content)} bytes) from {url}")
    return response.content


def resolve_pdftotext() -> str | None:
    found = shutil.which("pdftotext")
    if found:
        return found
    winget_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        for candidate in winget_root.glob("oschwartz10612.Poppler*/poppler-*/Library/bin/pdftotext.exe"):
            return str(candidate)
    return None


def run_pdftotext(pdf_path: Path) -> str:
    executable = resolve_pdftotext()
    if executable is None:
        raise KitaError("pdftotext executable not available on this system")
    with TemporaryDirectory() as tmp:
        out_txt = Path(tmp) / "kita.txt"
        completed = subprocess.run(
            [executable, "-layout", str(pdf_path), str(out_txt)],
            capture_output=True,
            timeout=300,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace").strip()
            raise KitaError(f"pdftotext failed: {stderr[:300]}")
        return out_txt.read_text(encoding="utf-8", errors="replace")


def pdf_to_text(pdf_bytes: bytes) -> str:
    with TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "kita.pdf"
        pdf_path.write_bytes(pdf_bytes)
        return run_pdftotext(pdf_path)


def parse_rp_trillion(text: str) -> Decimal | None:
    value = re.search(r"rp\s*[0-9][0-9.]*,[0-9]+", text, re.IGNORECASE)
    if value is None:
        return None
    cleaned = value.group(0).replace("Rp", "").replace("rp", "").replace(".", "")
    integer_part, _, fractional = cleaned.partition(",")
    return Decimal(f"{integer_part}.{fractional}")


METRIC_KEYWORDS = {
    "pendapatan_negara": [
        re.compile(r"PENDAPATAN\s+NEGARA", re.IGNORECASE),
        re.compile(r"Realisasi\s+Penerimaan\s+Negara", re.IGNORECASE),
    ],
    "belanja_negara": [
        re.compile(r"BELANJA\s+NEGARA", re.IGNORECASE),
        re.compile(r"Realisasi\s+Belanja\s+Negara", re.IGNORECASE),
    ],
    "defisit_apbn": [
        re.compile(r"DEFISIT\s+APBN", re.IGNORECASE),
        re.compile(r"SURPLUS/\s*\(DEFISIT\)", re.IGNORECASE),
    ],
    "pembiayaan_anggaran": [
        re.compile(r"E\.?\s*PEMBIAYAAN\s+ANGGARAN", re.IGNORECASE),
    ],
}


PERIOD_PATTERN = re.compile(
    r"s\.?d\.?\s*(\d{1,2})\s+"
    r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)"
    r"\s+(20[0-9]{2})",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+"
    r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)"
    r"\s+(20[0-9]{2})",
    re.IGNORECASE,
)


def build_period_label(cumulative_until: date) -> str:
    month_name = MONTH_NAMES_ID[cumulative_until.month]
    return f"Kumulatif s.d. {cumulative_until.day} {month_name} {cumulative_until.year}"


def find_period_info(text: str) -> tuple[date | None, date | None]:
    period_match = PERIOD_PATTERN.search(text)
    if period_match is None:
        return None, None
    day, month_name, year = period_match.groups()
    month = INDONESIAN_MONTHS[month_name.lower()]
    try:
        cumulative_until = date(int(year), month, int(day))
    except ValueError:
        return None, None
    publication_date = cumulative_until
    for date_match in DATE_PATTERN.finditer(text):
        if date_match.group(2).lower() != month_name.lower():
            continue
        try:
            publication_date = date(int(date_match.group(3)), month, int(date_match.group(1)))
            break
        except ValueError:
            continue
    return cumulative_until, publication_date


def _rp_values_with_positions(line: str) -> list[tuple[int, Decimal]]:
    values: list[tuple[int, Decimal]] = []
    for match in re.finditer(r"Rp\s*([0-9][0-9.]*,[0-9]+)\s*T", line, re.IGNORECASE):
        raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            values.append((match.start(), Decimal(raw)))
        except InvalidOperation:
            continue
    return values


def _extract_summary_metrics(text: str) -> dict[str, KitaMetric]:
    metrics: dict[str, KitaMetric] = {}
    header_match = re.search(
        r"PENDAPATAN\s+NEGARA.*BELANJA\s+NEGARA.*DEFISIT\s+APBN", text, re.IGNORECASE
    )
    if header_match is None:
        return metrics
    header_line_start = text.rfind("\n", 0, header_match.start()) + 1
    header_line_end = text.find("\n", header_match.end())
    if header_line_end == -1:
        header_line_end = len(text)
    header = text[header_line_start:header_line_end]
    columns = {
        "pendapatan_negara": header.upper().find("PENDAPATAN NEGARA"),
        "belanja_negara": header.upper().find("BELANJA NEGARA"),
        "defisit_apbn": header.upper().find("DEFISIT APBN"),
    }
    window = text[header_line_end : header_line_end + 800]
    for line in window.splitlines()[:6]:
        for position, value in _rp_values_with_positions(line):
            target = min(columns, key=lambda key: abs(columns[key] - position))
            if target in metrics or abs(columns[target] - position) > 45:
                continue
            if Decimal(1) <= abs(value) <= Decimal(50000):
                metrics[target] = KitaMetric(
                    identifier=target,
                    value=value,
                    unit="Rp Triliun",
                    matched_label=header.strip(),
                )
    ratio = re.search(r"\(?\s*(-?[0-9][0-9.,]*)\s*%\s*PDB\s*\)?", window, re.IGNORECASE)
    if ratio is not None:
        raw = ratio.group(1).replace(".", "").replace(",", ".")
        try:
            metrics["defisit_pdb"] = KitaMetric(
                identifier="defisit_pdb",
                value=Decimal(raw),
                unit="% PDB",
                matched_label=ratio.group(0),
            )
        except InvalidOperation:
            pass
    return metrics


def extract_kita_metrics(text: str) -> dict[str, KitaMetric]:
    metrics = _extract_summary_metrics(text)
    for identifier, patterns in METRIC_KEYWORDS.items():
        if identifier in metrics:
            continue
        for pattern in patterns:
            match = pattern.search(text)
            if match is None:
                continue
            window = text[match.start() : match.start() + 260]
            candidate = parse_rp_trillion(window)
            if candidate is not None and Decimal(1) <= abs(candidate) <= Decimal(50000):
                metrics[identifier] = KitaMetric(
                    identifier=identifier,
                    value=candidate,
                    unit="Rp Triliun",
                    matched_label=match.group(0),
                )
                break
    return metrics


def parse_kita_text(text: str, source_url: str = "") -> KitaResult:
    normalized = re.sub(r"[ \t]+", " ", text)
    cumulative_until, publication_date = find_period_info(normalized)
    metrics = extract_kita_metrics(normalized)
    if cumulative_until is not None:
        period_label = build_period_label(cumulative_until)
    else:
        period_label = "Periode tidak teridentifikasi"
    return KitaResult(
        source_url=source_url,
        cumulative_until=cumulative_until,
        period_label=period_label,
        publication_date=publication_date,
        metrics=metrics,
        text=text,
    )


def fetch_and_parse(url: str) -> tuple[bytes, KitaResult]:
    pdf_bytes = fetch_kita_pdf(url)
    text = pdf_to_text(pdf_bytes)
    return pdf_bytes, parse_kita_text(text, source_url=url)


def suggested_document_name(result: KitaResult) -> str:
    if result.cumulative_until is None:
        return "kita-apbn-unknown-period.pdf"
    return f"kita-apbn-{result.cumulative_until.strftime('%Y-%m')}.pdf"
