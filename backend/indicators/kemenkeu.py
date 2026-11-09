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
            ratio_value = Decimal(raw)
            nominal = metrics.get("defisit_apbn")
            if nominal is not None and (nominal.value > 0) != (ratio_value > 0) and ratio_value != 0:
                # Teks sumber kadang menulis rasio defisit dengan minus
                # ("(-1,24% PDB)") sementara nominalnya positif.
                # Samakan tanda dengan nominal agar seri konsisten
                # (defisit positif, surplus negatif).
                ratio_value = -ratio_value
            metrics["defisit_pdb"] = KitaMetric(
                identifier="defisit_pdb",
                value=ratio_value,
                unit="% PDB",
                matched_label=ratio.group(0),
            )
        except InvalidOperation:
            pass
    return metrics


# Celah kata sisipan kolom antar angka dan satuannya ("atau 0,41\n Di sisi
# Belanja Negara, sampai persen"). \S+ dipakai agar koma menempel
# ("Negara,") tak memutus pencocokan seperti yang terjadi pada \w+.
_GAP = r"(?:\s+\S+){0,10}?"


def _extract_narrative_metrics(normalized: str) -> dict[str, KitaMetric]:
    """Fallback edisi lama (2021-2024): angka total dari kalimat narasi.

    Pola berjangkar, bukan keyword lepas (keyword lepas pernah mengambil
    komponen sebagai total):
    - Pendapatan: "tercatat RpX triliun" dengan "Pendapatan Negara" di dekatnya.
    - Belanja: "RpX triliun (Y% dari pagu)" yang persennya juga disebut bersama
      "Belanja Negara ... dari pagu" (cross-match, menolak komponen).
    - Surplus/defisit: "RpX triliun (Y% ... PDB)" dengan kata surplus/defisit
      di dekatnya; surplus disimpan negatif (defisit = -surplus).
    """
    from indicators.parsing import parse_id_number

    def _num(raw: str) -> Decimal | None:
        try:
            value = parse_id_number(raw)
        except Exception:
            return None
        if value is None or not (Decimal(1) <= abs(value) <= Decimal(50000)):
            return None
        return value

    metrics: dict[str, KitaMetric] = {}
    # 1. Pendapatan total, dua redaksi template era 2024:
    #    (a) "Pendapatan Negara RpX triliun [atau Y% dari target]";
    #    (b) "tercatat RpX triliun" dengan "Pendapatan Negara" di dekatnya.
    for pattern in (
        r"Pendapatan Negara\s+Rp\s*([0-9][0-9.,]*)\s*triliun",
        r"tercatat\s+Rp\s*([0-9][0-9.,]*)\s*triliun",
    ):
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            window = normalized[max(0, match.start() - 250) : match.end() + 50]
            lowered = window.lower()
            if "pendapatan negara" not in lowered:
                continue
            if any(k in lowered for k in ("pajak tercatat", "cukai", "pnbp", "bea masuk", "bea keluar", "subsidi", "transfer")):
                continue
            value = _num(match.group(1))
            if value is None:
                continue
            metrics["pendapatan_negara"] = KitaMetric(
                identifier="pendapatan_negara",
                value=value,
                unit="Rp Triliun",
                matched_label=match.group(0).strip(),
            )
            break
        if "pendapatan_negara" in metrics:
            break
    # 2. Belanja total via cross-match persentase pagu.
    mentioned: set[str] = set()
    for match in re.finditer(
        r"belanja negara[^.]{0,150}?([0-9]+,[0-9]+)\s*persen\s*dari\s*pagu",
        normalized,
        re.IGNORECASE,
    ):
        mentioned.add(match.group(1))
    for match in re.finditer(
        r"Rp\s*([0-9][0-9.,]*)\s*triliun\s*\(\s*([0-9]+,[0-9]+)\s*persen\s*dari\s*pagu\s*\)",
        normalized,
        re.IGNORECASE,
    ):
        if match.group(2) not in mentioned:
            continue
        value = _num(match.group(1))
        if value is None:
            continue
        metrics["belanja_negara"] = KitaMetric(
            identifier="belanja_negara",
            value=value,
            unit="Rp Triliun",
            matched_label=match.group(0).strip(),
        )
        break
    if "belanja_negara" not in metrics:
        # Redaksi "terealisasi RpX triliun" pada kalimat Belanja Negara.
        for match in re.finditer(
            r"terealisasi\s+Rp\s*([0-9][0-9.,]*)\s*triliun",
            normalized,
            re.IGNORECASE,
        ):
            window = normalized[max(0, match.start() - 150) : match.end() + 50]
            lowered = window.lower()
            if "belanja negara" not in lowered:
                continue
            if any(k in lowered for k in ("subsidi", "transfer", "pemerintah pusat", "belanja k/l", "nonk/l", "non k/l")):
                continue
            value = _num(match.group(1))
            if value is None:
                continue
            metrics["belanja_negara"] = KitaMetric(
                identifier="belanja_negara",
                value=value,
                unit="Rp Triliun",
                matched_label=match.group(0).strip(),
            )
            break
    # 3. Surplus/defisit + rasio PDB. Dua redaksi:
    #    (a) "RpX triliun (Y% ... PDB)" dengan kata surplus/defisit di dekatnya;
    #    (b) "tercatat/mencapai surplus|defisit RpX triliun [atau Y% ... PDB]".
    #    Surplus disimpan negatif. Abaikan perbandingan tahun lalu
    #    ("yang sama 20xx") dan keseimbangan primer.
    for match in re.finditer(
        r"Rp\s*([0-9][0-9.,]*)\s*triliun\s*\(\s*([0-9]+[.,][0-9]+)\s*(?:persen|%)\s*(?:dari\s*)?PDB\s*\)",
        normalized,
        re.IGNORECASE,
    ):
        # Atribusi harus tepat sebelum angka (menolak angka pembiayaan/utang
        # yang kebetulan ber-PDB, mis. "Pembiayaan ... Rp616,2 triliun ...").
        before = normalized[max(0, match.start() - 100) : match.start()].lower()
        pos_surplus = before.rfind("surplus")
        pos_defisit = before.rfind("defisit")
        if pos_surplus < 0 and pos_defisit < 0:
            continue
        sign = -1 if pos_surplus >= pos_defisit else 1
        value = _num(match.group(1))
        ratio_raw = match.group(2).replace(".", "").replace(",", ".")
        try:
            ratio = Decimal(ratio_raw)
        except InvalidOperation:
            continue
        if value is None or not (Decimal(0) <= abs(ratio) <= Decimal(10)):
            continue
        metrics["defisit_apbn"] = KitaMetric(
            identifier="defisit_apbn",
            value=sign * value,
            unit="Rp Triliun",
            matched_label=match.group(0).strip(),
        )
        metrics["defisit_pdb"] = KitaMetric(
            identifier="defisit_pdb",
            value=sign * ratio,
            unit="% PDB",
            matched_label=match.group(0).strip(),
        )
        break
    if "defisit_apbn" not in metrics:
        ratio_tail = r"(?:\s*atau\s*([0-9]+[.,][0-9]+)" + _GAP + r"\s*persen\s*(?:(terhadap|dari)\s*)?PDB)?"
        for match in re.finditer(
            r"(surplus|defisit)(?:\s+\w+){0,2}\s+Rp\s*([0-9][0-9.,]*)\s*triliun" + ratio_tail,
            normalized,
            re.IGNORECASE,
        ):
            # Angka headline selalu muncul sebelum perbandingan tahun lalu,
            # jadi kemunculan valid pertama langsung dipakai.
            before = normalized[max(0, match.start() - 80) : match.start()].lower()
            near = normalized[max(0, match.start() - 80) : match.end() + 80].lower()
            if "primer" in near or "keseimbangan" in near:
                continue
            if re.search(r"\bsama\b|\blalu\b", before):
                continue
            value = _num(match.group(2))
            if value is None:
                continue
            sign = -1 if match.group(1).lower() == "surplus" else 1
            metrics["defisit_apbn"] = KitaMetric(
                identifier="defisit_apbn",
                value=sign * value,
                unit="Rp Triliun",
                matched_label=match.group(0).strip(),
            )
            ratio_raw = match.group(3)
            if not ratio_raw:
                # Rasio kadang terpisah oleh kolom ("...triliun\n\n Di sisi
                # Belanja Negara, sampai atau 0,68 persen terhadap PDB",
                # atau "atau 0,41\n Di sisi ... sampai persen terhadap PDB").
                # Ambil bila rasio muncul SEBELUM angka Rp lain di jendela.
                after = normalized[match.end() : match.end() + 150]
                lookahead = re.search(
                    r"([0-9]+[.,][0-9]+)" + _GAP + r"\s*persen\s*(?:(terhadap|dari)\s*)?PDB",
                    after,
                    re.IGNORECASE,
                )
                rp_after = re.search(r"Rp\s*[0-9]", after)
                if lookahead and (not rp_after or lookahead.start() < rp_after.start()):
                    ratio_raw = lookahead.group(1)
            if ratio_raw:
                after_all = (near + normalized[match.end() : match.end() + 150]).lower()
                if "pdb" in after_all:
                    try:
                        ratio = Decimal(ratio_raw.replace(".", "").replace(",", "."))
                    except InvalidOperation:
                        ratio = None
                    if ratio is not None and Decimal(0) <= abs(ratio) <= Decimal(10):
                        metrics["defisit_pdb"] = KitaMetric(
                            identifier="defisit_pdb",
                            value=sign * ratio,
                            unit="% PDB",
                            matched_label=match.group(0).strip(),
                        )
            break
    # 3b. Rasio tanpa nominal ("mengalami defisit 0,34 persen terhadap PDB").
    # Dipakai hanya bila nominal sudah ada dari pola (b) dan polanya sendiri
    # tak menyebut tahun lain perbandingan.
    if "defisit_apbn" in metrics and "defisit_pdb" not in metrics:
        for match in re.finditer(
            r"(surplus|defisit)\s+([0-9]+[.,][0-9]+)" + _GAP + r"\s*persen\s*(?:(terhadap|dari)\s*)?PDB",
            normalized,
            re.IGNORECASE,
        ):
            window = normalized[max(0, match.start() - 80) : match.end() + 20].lower()
            if "primer" in window or "keseimbangan" in window:
                continue
            if re.search(r"\b(sama|lalu)\b", window):
                continue
            try:
                ratio = Decimal(match.group(2).replace(".", "").replace(",", "."))
            except InvalidOperation:
                continue
            if not (Decimal(0) <= abs(ratio) <= Decimal(10)):
                continue
            sign = -1 if match.group(1).lower() == "surplus" else 1
            metrics["defisit_pdb"] = KitaMetric(
                identifier="defisit_pdb",
                value=sign * ratio,
                unit="% PDB",
                matched_label=match.group(0).strip(),
            )
            break
    # 4. Identitas akuntansi: defisit = belanja - pendapatan
    # (negatif saat surplus). Jika tidak cocok, buang D.
    if {"pendapatan_negara", "belanja_negara", "defisit_apbn"} <= set(metrics):
        gap = abs(
            metrics["defisit_apbn"].value
            - (
                metrics["belanja_negara"].value
                - metrics["pendapatan_negara"].value
            )
        )
        tolerance = max(Decimal("1"), abs(metrics["defisit_apbn"].value) * Decimal("0.05"))
        if gap > tolerance:
            metrics.pop("defisit_apbn", None)
            metrics.pop("defisit_pdb", None)
    return metrics


def extract_kita_metrics(text: str) -> dict[str, KitaMetric]:
    # Ringkasan 3 kolom (pendapatan/belanja/defisit) bergantung pada spasi
    # kolom hasil pdftotext, jadi harus diproses dari teks mentah SEBELUM
    # normalisasi spasi.
    metrics = _extract_summary_metrics(text)
    normalized = re.sub(r"[ \t]+", " ", text)
    # Fallback keyword HANYA untuk pembiayaan (total tak terambigu).
    # P/B/D dari keyword lepas terbukti mengambil komponen sebagai total
    # pada edisi lama, sehingga dinonaktifkan di sini.
    for identifier, patterns in METRIC_KEYWORDS.items():
        if identifier in metrics or identifier != "pembiayaan_anggaran":
            continue
        for pattern in patterns:
            match = pattern.search(normalized)
            if match is None:
                continue
            window = normalized[match.start() : match.start() + 260]
            candidate = parse_rp_trillion(window)
            if candidate is not None and Decimal(1) <= abs(candidate) <= Decimal(50000):
                metrics[identifier] = KitaMetric(
                    identifier=identifier,
                    value=candidate,
                    unit="Rp Triliun",
                    matched_label=match.group(0),
                )
                break
    # Fallback naratif untuk edisi lama tanpa tabel ringkasan.
    for identifier, metric in _extract_narrative_metrics(normalized).items():
        metrics.setdefault(identifier, metric)
    return metrics


def parse_kita_text(text: str, source_url: str = "") -> KitaResult:
    normalized = re.sub(r"[ \t]+", " ", text)
    cumulative_until, publication_date = find_period_info(normalized)
    metrics = extract_kita_metrics(text)
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
