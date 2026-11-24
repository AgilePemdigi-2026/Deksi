"""Read-only adapter for the public BKPM national quarterly investment preview."""

from __future__ import annotations

import base64
import calendar
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from .parsing import parse_bkpm_rp_juta

BASE_URL = "https://data.bkpm.go.id"
CATALOGUE_URL = f"{BASE_URL}/dataset"
PAGE_SIZE = 1000
MAX_CATALOGUE_PAGES = 12
MAX_ROWS = 100_000
MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_JSON_PAGE_BYTES = 8 * 1024 * 1024
EXPECTED_COLUMNS = (
    "periode", "status_penanaman_modal", "regional", "negara", "sektor_utama",
    "nama_sektor", "deskripsi_kbli_2digit", "provinsi", "kabupaten_kota",
    "jawa_luar_jawa", "pulau", "investasi_rp_juta", "investasi_us_ribu", "tki",
)
SLUG_RE = re.compile(
    r"^data-realisasi-investasi-triwulan-(i|ii|iii|iv)-tahun-(\d{4})$"
)
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}
QUARTER_NUMBER = {"i": 1, "ii": 2, "iii": 3, "iv": 4}


class BKPMError(RuntimeError):
    """The public BKPM preview was missing, ambiguous, or invalid."""


def _safe_url(url: str, *, paths: tuple[str, ...], query_allowed: bool = False) -> str:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError):
        raise BKPMError("Invalid BKPM source URL") from None
    if (parsed.scheme != "https" or parsed.hostname != "data.bkpm.go.id"
            or parsed.username is not None or parsed.password is not None
            or port is not None or parsed.fragment or parsed.path not in paths
            or (parsed.query and not query_allowed)):
        raise BKPMError("BKPM source URL is outside the approved public endpoints")
    return url


def _bytes(get_bytes, url: str, params=None, *, limit: int) -> bytes:
    parsed = urlsplit(url)
    if parsed.query:
        query = parse_qs(parsed.query, keep_blank_values=True)
        if (parsed.path != "/dataset" or set(query) != {"page"} or len(query["page"]) != 1
                or not query["page"][0].isdigit()):
            raise BKPMError("Invalid BKPM request URL parameters")
    _safe_url(url, paths=(parsed.path,), query_allowed=(parsed.path == "/dataset" and bool(parsed.query)))
    try:
        payload = get_bytes(url, params=params) if params is not None else get_bytes(url)
    except Exception:
        raise BKPMError("Could not retrieve the public BKPM preview") from None
    if not isinstance(payload, bytes) or len(payload) > limit:
        raise BKPMError("BKPM response is invalid or exceeds the size limit")
    return payload


def _local_href(base: str, href: str, expected_path: re.Pattern | None = None) -> str:
    absolute = urljoin(base, href)
    parsed = urlsplit(absolute)
    if (parsed.scheme != "https" or parsed.hostname != "data.bkpm.go.id"
            or parsed.username is not None or parsed.password is not None
            or parsed.port is not None or parsed.fragment):
        raise BKPMError("BKPM catalogue contains an unapproved link")
    if expected_path and not expected_path.fullmatch(parsed.path):
        raise BKPMError("BKPM catalogue link has an unexpected path")
    if not expected_path and parsed.path != "/dataset":
        raise BKPMError("BKPM pagination link has an unexpected path")
    return absolute


def _latest_completed(today: date) -> tuple[int, int]:
    quarter = (today.month - 1) // 3 + 1
    if quarter == 1:
        return today.year - 1, 4
    return today.year, quarter - 1


def _label(year: int, quarter: int) -> str:
    return f"Triwulan {ROMAN[quarter]} {year}"


def _catalogue_candidates(get_bytes) -> dict[tuple[int, int], set[str]]:
    first = _bytes(get_bytes, CATALOGUE_URL, limit=MAX_HTML_BYTES)
    queue = [CATALOGUE_URL]
    seen_pages: set[str] = set()
    candidates: dict[tuple[int, int], set[str]] = {}
    while queue:
        page_url = queue.pop(0)
        if page_url in seen_pages:
            continue
        if len(seen_pages) >= MAX_CATALOGUE_PAGES:
            raise BKPMError("BKPM catalogue pagination exceeds the limit")
        page = first if page_url == CATALOGUE_URL else _bytes(get_bytes, page_url, limit=MAX_HTML_BYTES)
        seen_pages.add(page_url)
        soup = BeautifulSoup(page, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            parsed_href = urlsplit(href)
            if parsed_href.path == "/dataset" and 'page' in parse_qs(parsed_href.query):
                target = _local_href(page_url, href)
                values = parse_qs(urlsplit(target).query).get("page", [])
                if len(values) != 1 or not values[0].isdigit():
                    raise BKPMError("Invalid BKPM catalogue pagination link")
                if int(values[0]) > 0:
                    if int(values[0]) == 1:
                        target = CATALOGUE_URL
                    queue.append(target)
                continue
            if "data-realisasi-investasi-triwulan-" in parsed_href.path:
                detail = _local_href(
                    page_url, href,
                    re.compile(r"/(?:dataset|dataset-detail|dataset-view)/[^/]+"),
                )
                slug = urlsplit(detail).path.rsplit("/", 1)[-1]
                match = SLUG_RE.fullmatch(slug)
                if match:
                    key = (int(match.group(2)), QUARTER_NUMBER[match.group(1)])
                    candidates.setdefault(key, set()).add(detail)
    return candidates


def _get_column_names(columns) -> tuple[str, ...]:
    if not isinstance(columns, list):
        raise BKPMError("BKPM preview columns are invalid")
    normalized = []
    for column in columns:
        if isinstance(column, str):
            name = column
        elif isinstance(column, dict):
            name = column.get("data", column.get("name"))
        else:
            name = None
        if not isinstance(name, str):
            raise BKPMError("BKPM preview has an invalid column name")
        normalized.append(name.removeprefix("\ufeff"))
    if len(set(normalized)) != len(normalized) or tuple(normalized) != EXPECTED_COLUMNS:
        raise BKPMError("BKPM preview columns changed or conflict after normalization")
    return tuple(normalized)


def _validate_period(value, year: int, quarter: int) -> None:
    if not isinstance(value, str):
        raise BKPMError("BKPM row has no valid reporting period")
    normalized = value.removeprefix("\ufeff").strip()
    match = re.fullmatch(r"(\d{4})\s*-\s*Triwulan\s+([1-4])", normalized, re.IGNORECASE)
    if not match or (int(match.group(1)), int(match.group(2))) != (year, quarter):
        raise BKPMError("BKPM row reporting period does not match the selected quarter")


def _row_value(row: dict, key: str):
    matches = [value for name, value in row.items() if isinstance(name, str) and name.removeprefix("\ufeff") == key]
    if len(matches) != 1:
        raise BKPMError("BKPM row has missing or conflicting normalized fields")
    return matches[0]


def _amount(value) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise BKPMError("BKPM investment value is missing")
    parsed = parse_bkpm_rp_juta(value)
    if not isinstance(parsed, Decimal) or not parsed.is_finite() or parsed < 0:
        raise BKPMError("BKPM investment value is invalid")
    return parsed


def _preview_pages(get_bytes, parent_id: str, year: int, quarter: int):
    pages = []
    page_hashes: set[str] = set()
    total_rows = None
    total_filtered = None
    start = 0
    total = Decimal(0)
    evidence_size = 0
    received = 0
    while True:
        params = {"dataset_detail_parent_id": parent_id, "start": start,
                  "length": PAGE_SIZE, "draw": len(pages) + 1}
        raw = _bytes(get_bytes, f"{BASE_URL}/data", params=params, limit=MAX_JSON_PAGE_BYTES)
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BKPMError("BKPM preview JSON is malformed") from None
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise BKPMError("BKPM preview JSON has an invalid structure")
        if type(data.get("draw")) is not int or data["draw"] != len(pages) + 1:
            raise BKPMError("BKPM preview draw counter changed unexpectedly")
        digest = hashlib.sha256(json.dumps(
            data["data"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).digest()
        if digest in page_hashes:
            raise BKPMError("BKPM repeated a preview page")
        page_hashes.add(digest)
        _get_column_names(data.get("columns"))
        raw_total = data.get("recordsTotal")
        raw_filtered = data.get("recordsFiltered")
        if (type(raw_total) is not int or type(raw_filtered) is not int
                or raw_total < 0 or raw_filtered < 0
                or raw_total > MAX_ROWS or raw_filtered > MAX_ROWS):
            raise BKPMError("BKPM preview row counts are invalid or exceed the limit")
        counts = (raw_total, raw_filtered)
        if total_rows is None:
            total_rows, total_filtered = counts
        elif counts != (total_rows, total_filtered):
            raise BKPMError("BKPM preview counts changed during pagination")
        if total_rows != total_filtered:
            raise BKPMError("BKPM preview is filtered; refusing incomplete data")
        rows = data["data"]
        if len(rows) > PAGE_SIZE or len(rows) != min(PAGE_SIZE, max(0, counts[0] - start)):
            raise BKPMError("BKPM preview pagination is incomplete")
        evidence_size += 4 * ((len(raw) + 2) // 3) + 512
        if evidence_size > MAX_EVIDENCE_BYTES:
            raise BKPMError("BKPM preview evidence exceeds the size limit")
        for row in rows:
            if not isinstance(row, dict):
                raise BKPMError("BKPM preview row is invalid")
            normalized_keys = [key.removeprefix('\ufeff') for key in row]
            if len(normalized_keys) != len(set(normalized_keys)) or set(normalized_keys) != set(EXPECTED_COLUMNS):
                raise BKPMError('BKPM preview row columns are incomplete or ambiguous')
            _validate_period(_row_value(row, "periode"), year, quarter)
            total += _amount(_row_value(row, "investasi_rp_juta"))
        pages.append({"start": start, "row_count": len(rows), "sha256": hashlib.sha256(raw).hexdigest(),
                      "raw_base64": base64.b64encode(raw).decode("ascii")})
        received += len(rows)
        if received >= total_rows:
            break
        if not rows:
            raise BKPMError("BKPM preview ended before all rows were retrieved")
        start += len(rows)
    if not total_rows:
        raise BKPMError("BKPM preview contains no rows")
    return pages, (total / Decimal(1_000_000)).quantize(Decimal("0.01"))


def fetch_latest(get_bytes, *, today=None) -> dict:
    """Return the latest completed national quarter using an injected GET transport."""
    today = today or date.today()
    if not isinstance(today, date):
        raise BKPMError("today must be a date")
    try:
        year, quarter = _latest_completed(today)
        candidates = _catalogue_candidates(get_bytes)
        eligible = [key for key, slugs in candidates.items() if key <= (year, quarter) and slugs]
        if not eligible:
            raise BKPMError("No completed national BKPM quarter is available")
        selected = max(eligible)
        slugs = candidates[selected]
        if len(slugs) != 1:
            raise BKPMError("BKPM catalogue has ambiguous links for the latest quarter")
        selected_year, selected_quarter = selected
        detail_url = next(iter(slugs))
        slug = urlsplit(detail_url).path.rsplit("/", 1)[-1]
        detail = BeautifulSoup(_bytes(get_bytes, detail_url, limit=MAX_HTML_BYTES), "html.parser")
        if urlsplit(detail_url).path.startswith("/dataset-view/"):
            source_url = detail_url
        else:
            view_links = []
            for anchor in detail.find_all("a", href=True):
                if "dataset-view" in urlsplit(anchor["href"]).path:
                    target = _local_href(detail_url, anchor["href"], re.compile(r"/dataset-view/[^/]+"))
                    if urlsplit(target).path.rsplit("/", 1)[-1] == slug:
                        view_links.append(target)
            if not view_links or len(set(view_links)) != 1:
                raise BKPMError("BKPM detail page has no unique matching preview link")
            source_url = view_links[0]
        preview = (detail if source_url == detail_url else
            BeautifulSoup(_bytes(get_bytes, source_url, limit=MAX_HTML_BYTES), 'html.parser'))
        parent_inputs = preview.select('input#dataset_detail_parent_id')
        if len(parent_inputs) != 1:
            raise BKPMError("BKPM preview page has no unique identifier")
        parent_id = parent_inputs[0].get("value")
        if not isinstance(parent_id, str) or not parent_id.strip() or len(parent_id) > 256:
            raise BKPMError("BKPM preview page identifier is invalid")
        pages, value = _preview_pages(get_bytes, parent_id, selected_year, selected_quarter)
        evidence = {"kind": "bkpm_public_preview_json", "source_url": source_url,
                    "period_label": _label(selected_year, selected_quarter), "pages": pages}
        content = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(content) > MAX_EVIDENCE_BYTES:
            raise BKPMError("BKPM preview evidence exceeds the size limit")
        quarter_end_month = selected_quarter * 3
        quarter_end = date(selected_year, quarter_end_month,
                           calendar.monthrange(selected_year, quarter_end_month)[1])
        return {
            "document_name": slug + '-preview.json',
            "source_url": source_url,
            "period_label": _label(selected_year, selected_quarter),
            "content": content,
            "points": [{"code": "investasi", "observation_date": quarter_end,
                        "period_label": _label(selected_year, selected_quarter),
                        "frequency": "quarterly", "data_type": "derived_sum",
                        "value": value, "unit": "Rp Triliun"}],
        }
    except BKPMError:
        raise
    except Exception:
        raise BKPMError("BKPM public preview could not be validated") from None
