import calendar
import time
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from django.conf import settings
from django.utils import timezone

from .models import Indicator, Source

MONTHS_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}

BPS_SOURCE_DEFAULTS = {
    "source_name": "WebAPI BPS",
    "institution": "Badan Pusat Statistik",
    "primary_url": "https://www.bps.go.id/",
    "description": "Data indikator ekonomi resmi dari WebAPI Badan Pusat Statistik.",
}

# Variable IDs are taken from the official BPS WebAPI dynamic-table catalog.
# National row IDs are resolved from the catalog at sync time, not guessed.
BPS_SERIES = [
    {
        "code": "pdb",
        "var_id": 104,
        "name": "Pertumbuhan PDB",
        "category": "Aktivitas Riil",
        "unit": "%",
        "aggregation_kind": "avg",
        "sort_order": 1,
        "frequency": "quarterly",
        "data_type": "yoy",
        "turvar_keyword": "y-on-y",
        "national_label": "PRODUK DOMESTIK BRUTO",
        "subperiods": {31: 1, 32: 2, 33: 3, 34: 4},
    },
    {
        "code": "inflasi",
        "var_id": 2263,
        "name": "Inflasi IHK",
        "category": "Stabilisasi Harga",
        "unit": "%",
        "aggregation_kind": "avg",
        "sort_order": 2,
        "frequency": "monthly",
        "data_type": "yoy",
        "turvar_keyword": None,
        "national_label": "INDONESIA",
        "subperiods": {month: month for month in range(1, 13)},
    },
    {
        "code": "tpt",
        "var_id": 543,
        "name": "Tingkat Pengangguran Terbuka",
        "category": "Pasar Kerja",
        "unit": "%",
        "aggregation_kind": "avg",
        "sort_order": 6,
        "frequency": "semiannual",
        "data_type": "level",
        "turvar_keyword": None,
        "national_label": "INDONESIA",
        "subperiods": {189: 2, 190: 8},
    },
]


class BpsError(Exception):
    pass


class BpsNotConfigured(BpsError):  # noqa: N818 - preserve the existing public exception name
    pass


def api_key() -> str:
    return str(getattr(settings, "BPS_API_KEY", "") or "").strip()


def base_url() -> str:
    return str(getattr(settings, "BPS_API_BASE_URL", "https://webapi.bps.go.id/v1") or "").rstrip("/")


def _request(path: str, params: dict | None = None) -> dict:
    key = api_key()
    if not key:
        raise BpsNotConfigured(
            "BPS_API_KEY belum diisi. Tambahkan BPS_API_KEY pada backend/.env lalu jalankan ulang backend."
        )
    url = f"{base_url()}{path}/key/{key}"
    try:
        response = httpx.get(url, params=params, timeout=30, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise BpsError(f"Koneksi ke WebAPI BPS gagal: {exc.__class__.__name__}") from exc
    if response.status_code >= 400:
        message = "permintaan ditolak"
        try:
            body = response.json()
            message = body.get("message") or body.get("status") or message
        except ValueError:
            pass
        raise BpsError(f"WebAPI BPS menolak permintaan (HTTP {response.status_code}): {message}")
    try:
        body = response.json()
    except ValueError as exc:
        raise BpsError("Respons WebAPI BPS bukan JSON yang valid.") from exc
    if body.get("status") != "OK":
        raise BpsError(f"WebAPI BPS mengembalikan status {body.get('status') or 'tidak dikenal'}.")
    return body


def _rows(body: dict) -> list[dict]:
    data = body.get("data") or []
    if len(data) < 2 or not isinstance(data[1], list):
        return []
    return data[1]


def test_connection() -> dict:
    checked_at = timezone.now().isoformat()
    if not api_key():
        return {
            "configured": False,
            "connected": False,
            "checkedAt": checked_at,
            "message": "BPS_API_KEY belum tersedia di backend/.env.",
        }
    started = time.perf_counter()
    try:
        body = _request("/api/domain/type/prov")
    except BpsError as exc:
        return {
            "configured": True,
            "connected": False,
            "checkedAt": checked_at,
            "latencyMs": int((time.perf_counter() - started) * 1000),
            "message": str(exc),
        }
    page = (body.get("data") or [{}])[0]
    return {
        "configured": True,
        "connected": True,
        "checkedAt": checked_at,
        "latencyMs": int((time.perf_counter() - started) * 1000),
        "domains": page.get("total"),
        "message": "Koneksi WebAPI BPS berhasil.",
    }


def _get_or_create_source() -> Source:
    from .lifecycle import ensure_import_master

    source = ensure_import_master(Source, source_id="BPS", defaults=BPS_SOURCE_DEFAULTS)
    return source


def _get_or_create_indicator(series: dict) -> Indicator:
    from .lifecycle import ensure_import_master

    indicator = ensure_import_master(Indicator,
        code=series["code"],
        defaults={
            "name": series["name"],
            "category": series["category"],
            "unit": series["unit"],
            "aggregation_kind": series["aggregation_kind"],
            "sort_order": series["sort_order"],
            "footnote": "Sumber: WebAPI BPS. Angka tahun terbaru dapat berstatus sementara sesuai publikasi BPS.",
        },
    )
    return indicator


def _paged_rows(path: str, params: dict | None = None) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        query = dict(params or {})
        query["page"] = page
        body = _request(path, params=query)
        batch = _rows(body)
        rows.extend(batch)
        paging = (body.get("data") or [{}])[0]
        if not batch or page >= int(paging.get("pages") or 1):
            break
        page += 1
        time.sleep(0.2)
    return rows


def _resolve_national_vervar(series: dict) -> int:
    rows = _paged_rows("/api/list/model/vervar/domain/0000", {"var": series["var_id"]})
    wanted = series["national_label"].lower()
    for row in rows:
        label = str(row.get("vervar") or "").lower()
        if wanted in label:
            return int(row["kode_ver_id"])
    for row in rows:
        if str(row.get("vervar") or "").strip().lower() == "indonesia":
            return int(row["kode_ver_id"])
    raise BpsError(f"Baris nasional untuk variabel BPS {series['var_id']} tidak ditemukan.")


def _resolve_turvar(series: dict) -> int:
    keyword = series.get("turvar_keyword")
    if not keyword:
        return 0
    rows = _paged_rows("/api/list/model/turvar/domain/0000", {"var": series["var_id"]})
    for row in rows:
        if keyword.lower() in str(row.get("turvar") or "").lower():
            return int(row["turvar_id"])
    raise BpsError(f"Turunan variabel '{keyword}' untuk variabel BPS {series['var_id']} tidak ditemukan.")


def _year_period_ids(series: dict) -> dict[int, int]:
    rows = _paged_rows("/api/list/model/th/domain/0000", {"var": series["var_id"]})
    return {int(row["th"]): int(row["th_id"]) for row in rows if str(row.get("th", "")).isdigit()}


def _chunks(values: list[int], size: int = 3) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _period_label(series: dict, year: int, subperiod_value: int) -> str:
    if series["frequency"] == "quarterly":
        return f"Q{subperiod_value} {year}"
    return f"{MONTHS_ID[subperiod_value]} {year}"


def _decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def fetch_series(series: dict, start_year: int = 2016, end_year: int | None = None) -> list[dict]:
    end_year = end_year or timezone.localdate().year
    period_ids = _year_period_ids(series)
    years = [year for year in range(start_year, end_year + 1) if year in period_ids]
    if not years:
        return []
    vervar = _resolve_national_vervar(series)
    turvar = _resolve_turvar(series)
    turth_values = list(series["subperiods"])
    points: list[dict] = []
    for chunk in _chunks(years):
        th_param = ";".join(str(period_ids[year]) for year in chunk)
        params = {
            "vervar": vervar,
            "turth": ";".join(str(value) for value in turth_values),
        }
        if turvar:
            params["turvar"] = turvar
        body = _request(
            f"/api/list/model/data/domain/0000/var/{series['var_id']}/th/{th_param}",
            params=params,
        )
        data_content = body.get("datacontent") or {}
        if not isinstance(data_content, dict):
            continue
        for year in chunk:
            th_id = period_ids[year]
            for turth_id, subperiod_value in series["subperiods"].items():
                key = f"{vervar}{series['var_id']}{turvar}{th_id}{turth_id}"
                value = _decimal(data_content.get(key))
                if value is None:
                    continue
                month = subperiod_value if series["frequency"] != "quarterly" else subperiod_value * 3
                points.append(
                    {
                        "observation_date": _last_day(year, month),
                        "period_label": _period_label(series, year, subperiod_value),
                        "value": value,
                        "frequency": series["frequency"],
                        "data_type": series["data_type"],
                        "unit": series["unit"],
                    }
                )
        time.sleep(0.25)
    return points


def sync_bps_indicators(start_year: int = 2016, end_year: int | None = None) -> dict:
    from .sync_history_service import begin_sync_run, finalize_sync_run

    source = _get_or_create_source()
    run = begin_sync_run(source=source)
    try:
        result = _sync_bps_started(source, start_year, end_year)
    except Exception:
        finalize_sync_run(run, success=False)
        raise
    finalize_sync_run(run, success=not result["errors"], failure_stage="fetch_series" if result["errors"] else None)
    return result


def _sync_bps_started(source, start_year, end_year):
    from .lifecycle import stage_observation

    total = 0
    errors: list[str] = []
    latest: dict[str, str] = {}
    for series in BPS_SERIES:
        indicator = _get_or_create_indicator(series)
        try:
            points = fetch_series(series, start_year=start_year, end_year=end_year)
        except BpsError as exc:
            errors.append(f"{series['code']}: {exc}")
            continue
        for point in points:
            stage_observation(indicator_id=indicator.pk, source_id=source.pk,
                observation_date=point["observation_date"], data_type=point["data_type"],
                period_label=point["period_label"], frequency=point["frequency"],
                value=point["value"], unit=point["unit"])
            total += 1
        if points:
            latest[series["code"]] = max(points, key=lambda point: point["observation_date"])["period_label"]
    return {"observations": total, "errors": errors, "latest": latest}
