"""Discovery arsip APBN KiTa Kemenkeu via BeautifulSoup.

Menghubungkan seluruh alur Kemenkeu ke satu pintu discovery:
halaman arsip resmi (DJPPR/Kemenkeu) -> daftar tautan PDF KiTa
-> filter 5/10 tahun kebelakang -> ingest via fiscal/kemenkeu.

Hanya domain resmi yang diizinkan (anti-SSRF):
- kemenkeu.go.id dan subdomainnya (www, media, djppr, ...)
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

ALLOWED_SUFFIX = "kemenkeu.go.id"
ALLOWED_HOSTS = ("kemenkeu.go.id", "anggaran.kemenkeu.go.id")

DEFAULT_ARCHIVE_URLS = [
    "https://djppr.kemenkeu.go.id/apbnkita",
    "https://www.kemenkeu.go.id/publikasi/apbn-kita",
]

ANGGARAN_SEARCH_URL = "https://anggaran.kemenkeu.go.id/api/posts"
ANGGARAN_ORIGIN = "https://anggaran.kemenkeu.go.id"
MEDIAS_RE = re.compile(r"/api/Medias/([0-9A-Za-z-]+)", re.IGNORECASE)

KITA_HREF_RE = re.compile(r"kita", re.IGNORECASE)
PDF_RE = re.compile(r"\.pdf(\?|$)", re.IGNORECASE)
YEAR_RE = re.compile(r"(20[1-3][0-9])")
MONTH_MAP = {
    "januari": 1, "jan": 1, "februari": 2, "feb": 2, "maret": 3, "mar": 3,
    "april": 4, "apr": 4, "mei": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "ags": 8, "september": 9, "sep": 9,
    "oktober": 10, "okt": 10, "november": 11, "nov": 11, "desember": 12, "des": 12,
}
MONTH_RE = re.compile(
    r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember|"
    r"jan|feb|mar|apr|jun|jul|agu|ags|sep|okt|nov|des)",
    re.IGNORECASE,
)


class DiscoveryError(Exception):
    pass


def is_allowed_url(url: str) -> bool:
    """Hanya http(s) ke *.kemenkeu.go.id yang boleh di-fetch."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return host == "kemenkeu.go.id" or host.endswith("." + ALLOWED_SUFFIX)


def fetch_page(url: str, client: httpx.Client | None = None, timeout: int = 60) -> str:
    if not is_allowed_url(url):
        raise DiscoveryError(f"domain tidak diizinkan: {url}")
    own = client is None
    if own:
        client = httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 DEKSI-discovery"})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise DiscoveryError(f"gagal memuat {url}: {exc.__class__.__name__}") from exc
    finally:
        if own:
            client.close()
    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and "<html" not in resp.text[:2000].lower():
        raise DiscoveryError(f"bukan halaman HTML: {url} ({ctype or 'tanpa content-type'})")
    return resp.text


def _infer_year_month(text: str, today: date | None = None) -> tuple[int | None, int | None]:
    today = today or date.today()
    year: int | None = None
    for year_m in YEAR_RE.finditer(text):
        candidate = int(year_m.group(1))
        # Tolak tahun mustahil (mis. digit GUID seperti 2033): izinkan
        # 2015 (awal publikasi KiTa) sampai setahun ke depan.
        if 2015 <= candidate <= today.year + 1:
            year = candidate
            break
    month_m = MONTH_RE.search(text)
    month = MONTH_MAP[month_m.group(1).lower()] if month_m else None
    return year, month


def extract_kita_links(html: str, base_url: str) -> list[dict]:
    """Ambil semua <a href=*.pdf> yang berbau KiTa/APBN beserta tahun/bulan."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()
    for tag in soup.find_all("a", href=True):
        raw = str(tag["href"]).strip()
        if not raw or raw.startswith(("javascript:", "mailto:", "#")):
            continue
        full = urljoin(base_url, raw)
        if not is_allowed_url(full):
            continue
        if not PDF_RE.search(full):
            continue
        label = " ".join(tag.get_text(" ", strip=True).split())
        haystack = f"{full} {label}"
        if not KITA_HREF_RE.search(haystack) and "apbn" not in haystack.lower():
            continue
        if full in seen:
            continue
        seen.add(full)
        year, month = _infer_year_month(haystack)
        out.append({"url": full, "title": label or full, "year": year, "month": month})
    # Tahun terbaru dulu; tanpa tahun ditaruh paling belakang.
    out.sort(key=lambda d: ((d["year"] or 0), (d["month"] or 0)), reverse=True)
    return out


def filter_by_year(links: list[dict], years_back: int, today: date | None = None) -> list[dict]:
    today = today or date.today()
    min_year = today.year - years_back + 1
    kept = [d for d in links if (d.get("year") or 0) >= min_year]
    # Tautan tanpa tahun tetap disertakan agar tidak ada arsip hilang;
    # ingest nanti memvalidasi periode dari isi PDF.
    kept += [d for d in links if not d.get("year")]
    return kept


def _extract_medias_links(content_html: str) -> list[dict]:
    """Ambil tautan /api/Medias/<guid> dari konten post (a/iframe/embed/object).

    BeautifulSoup dipakai di sini: konten post adalah HTML mentah berisi
    <a href="/api/Medias/...">Paparan Konpers APBN KiTa Bulan X YYYY</a>.
    """
    soup = BeautifulSoup(content_html or "", "html.parser")
    out: list[dict] = []
    seen: set[str] = set()
    for tag in soup.find_all(["a", "iframe", "embed", "object", "source"]):
        raw = str(tag.get("href") or tag.get("src") or tag.get("data") or "").strip()
        if not raw:
            continue
        full = urljoin(ANGGARAN_ORIGIN, raw)
        match = MEDIAS_RE.search(full)
        if not match:
            continue
        guid = match.group(1)
        canonical = f"{ANGGARAN_ORIGIN}/api/Medias/{guid}"
        if canonical in seen:
            continue
        seen.add(canonical)
        label = " ".join(tag.get_text(" ", strip=True).split())
        year, month = _infer_year_month(f"{label} {full}")
        out.append({"url": canonical, "title": label or guid, "year": year, "month": month})
    return out


def discover_via_anggaran_search(
    keyword: str = "kita",
    years_back: int = 10,
    max_items: int = 120,
    client: httpx.Client | None = None,
    timeout: int = 30,
) -> list[dict]:
    """Cari arsip KiTa via API pencarian anggaran.kemenkeu.go.id + BeautifulSoup.

    Pagination memakai offset+limit (limit=100 per halaman). Setiap konten
    post diurai dengan BeautifulSoup untuk memungut tautan PDF /api/Medias/.
    """
    if years_back not in (5, 10):
        raise DiscoveryError("years_back harus 5 atau 10")
    own = client is None
    if own:
        client = httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        merged: dict[str, dict] = {}
        offset = 0
        step = 100
        total = None
        guard = 0
        while True:
            guard += 1
            if guard > 30:
                break
            last_error: Exception | None = None
            resp = None
            for attempt in range(4):
                try:
                    resp = client.get(
                        ANGGARAN_SEARCH_URL,
                        params={"search": keyword, "offset": offset, "limit": step},
                        headers={
                            "User-Agent": "Mozilla/5.0 DEKSI-discovery",
                            "Accept": "application/json",
                        },
                    )
                    resp.raise_for_status()
                    last_error = None
                    break
                except httpx.HTTPError as exc:
                    last_error = exc
                    if attempt < 3:
                        import time as _time

                        _time.sleep(2 * (attempt + 1))
            if resp is None or last_error is not None:
                raise DiscoveryError(
                    "pencarian arsip gagal setelah 4x coba: "
                    f"{type(last_error).__name__ if last_error else 'tanpa respons'}"
                )
            try:
                body = resp.json()
            except ValueError as exc:
                raise DiscoveryError("respons pencarian arsip bukan JSON") from exc
            if total is None:
                try:
                    total = int(body.get("TotalData") or 0)
                except (TypeError, ValueError):
                    total = 0
            items = body.get("Data") or []
            if not items:
                break
            for post in items:
                content = post.get("Content") or ""
                post_title = post.get("Title") or ""
                for link in _extract_medias_links(content):
                    if not link["title"] or len(link["title"]) < 4:
                        link["title"] = post_title
                        y, m = _infer_year_month(f"{post_title} {link['url']}")
                        link["year"] = link["year"] or y
                        link["month"] = link["month"] or m
                    # Hanya arsip KiTa: "kita" harus ada di judul tautan
                    # atau judul post (menyingkirkan PMK/dokumen lain).
                    context = f"{link['title']} {post_title}".lower()
                    if "kita" not in context:
                        continue
                    merged.setdefault(link["url"], link)
                    if 0 < max_items <= len(merged):
                        break
                if 0 < max_items <= len(merged):
                    break
            offset += len(items)
            if total and offset >= total:
                break
            if 0 < max_items <= len(merged):
                break
        links = sorted(
            merged.values(),
            key=lambda d: ((d["year"] or 0), (d["month"] or 0)),
            reverse=True,
        )
        return filter_by_year(links, years_back)[:max_items] if max_items > 0 else filter_by_year(links, years_back)
    except httpx.HTTPError as exc:
        raise DiscoveryError(f"pencarian arsip gagal: {exc.__class__.__name__}") from exc
    finally:
        if own:
            client.close()


def discover_kita_urls(
    base_urls: list[str] | None = None,
    years_back: int = 10,
    max_items: int = 120,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Jelajahi arsip KiTa 5/10 tahun terakhir.

    Jalur utama: API pencarian anggaran.kemenkeu.go.id + BeautifulSoup
    atas konten post (menangani SPA yang tidak punya tautan statis).
    Fallback: halaman arsip statis DJPPR/Kemenkeu.
    """
    if years_back not in (5, 10):
        raise DiscoveryError("years_back harus 5 atau 10")
    try:
        primary = discover_via_anggaran_search(
            keyword="kita", years_back=years_back, max_items=max_items, client=client
        )
    except DiscoveryError:
        primary = []
    if primary:
        return primary
    bases = base_urls or DEFAULT_ARCHIVE_URLS
    merged: dict[str, dict] = {}
    errors: list[str] = []
    for base in bases:
        try:
            html = fetch_page(base, client=client)
        except DiscoveryError as exc:
            errors.append(str(exc))
            continue
        for item in extract_kita_links(html, base):
            merged.setdefault(item["url"], item)
    links = sorted(
        merged.values(),
        key=lambda d: ((d["year"] or 0), (d["month"] or 0)),
        reverse=True,
    )
    links = filter_by_year(links, years_back)
    if max_items > 0:
        links = links[:max_items]
    if not links and errors:
        raise DiscoveryError("; ".join(errors))
    return links
