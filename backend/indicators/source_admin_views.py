"""
Views untuk Fitur 10: Tambah Sumber Data (UC-06).

Konvensi mengikuti indicators/feedback_views.py:
  - function-based views, tanpa DRF
  - json_success / json_error dari indicators.views
  - validasi manual, transaksi atomik, tanpa sinkronisasi otomatis
"""

import json
import logging
from urllib.parse import urlparse

import httpx
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from indicators.models import RawFile, Source
from indicators.updates import record_update_success
from indicators.views import json_error, json_success

logger = logging.getLogger(__name__)

# Metode yang benar-benar memiliki handler di codebase.
# Jangan tambah opsi di sini tanpa implementasi handler-nya.
SUPPORTED_METHODS = {
    "api_bps": {
        "label": "API resmi (WebAPI BPS)",
        "formats": ["json"],
        "handler": "indicators.bps.sync_bps_indicators",
        "endpointRequired": True,
        "description": "Sinkronisasi WebAPI BPS (bps.py).",
    },
    "pdf_kita": {
        "label": "PDF resmi (APBN KiTa Kemenkeu)",
        "formats": ["pdf"],
        "handler": "indicators.fiscal.ingest_kita_pdf_url",
        "endpointRequired": True,
        "description": "Unduh PDF APBN KiTa lalu parse (fiscal.py/kemenkeu.py).",
    },
    "file_xlsx": {
        "label": "File resmi (XLSX dataset)",
        "formats": ["xlsx"],
        "handler": "indicators.ingest.parse_bi_rr_xlsx",
        "endpointRequired": False,
        "description": "Dataset XLSX lokal (ingest.py: BI-7Day-RR/JISDOR/moneter).",
    },
    "file_zip_csv": {
        "label": "File resmi (ZIP berisi CSV)",
        "formats": ["zip_csv"],
        "handler": "indicators.ingest.sum_bkpm_zip_csv",
        "endpointRequired": False,
        "description": "Arsip ZIP triwulanan berisi CSV investasi (ingest.py).",
    },
}

FREQUENCIES = ["daily", "monthly", "quarterly", "semiannual", "annual", "adhoc", "mixed"]

PROBE_TIMEOUT_SECONDS = 10


def _parse_json_body(request):
    if "application/json" not in (request.content_type or ""):
        return None, "Content-Type harus application/json."
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Body permintaan bukan JSON yang valid."
    if not isinstance(data, dict):
        return None, "Payload JSON harus berupa objek."
    return data, None


def _require_staff(request):
    """401 jika belum login, 403 jika bukan staf pengelola sumber."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return json_error("Autentikasi diperlukan.", status=401)
    if not user.is_staff:
        return json_error("Hak akses pengelolaan sumber diperlukan.", status=403)
    return None


def _is_valid_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _probe_endpoint_reachable(url: str) -> tuple[bool, str]:
    """HEAD lalu fallback GET ringan. True jika status < 400."""
    try:
        with httpx.Client(timeout=PROBE_TIMEOUT_SECONDS, follow_redirects=True) as client:
            try:
                response = client.head(url)
                if response.status_code in (403, 405):
                    response = client.get(url, headers={"Range": "bytes=0-0"})
            except httpx.HTTPError:
                response = client.get(url)
        if response.status_code >= 400:
            return False, f"Endpoint mengembalikan HTTP {response.status_code}."
        return True, ""
    except httpx.HTTPError as exc:
        return False, f"Endpoint tidak dapat dijangkau: {exc.__class__.__name__}."


def _last_fetch_info(source: Source) -> dict:
    latest = RawFile.objects.filter(source=source).order_by("-retrieved_at", "-id").first()
    if latest is None:
        return {"retrievedAt": None, "documentName": None, "parseStatus": None}
    return {
        "retrievedAt": latest.retrieved_at.isoformat() if latest.retrieved_at else None,
        "documentName": latest.document_name,
        "parseStatus": latest.parse_status,
    }


def _serialize_admin_entry(source: Source) -> dict:
    return {
        "sourceId": source.source_id,
        "sourceName": source.source_name,
        "institution": source.institution,
        "primaryUrl": source.primary_url,
        "description": source.description or "",
        "acquisitionMethod": source.acquisition_method or "",
        "acquisitionMethodLabel": (
            SUPPORTED_METHODS[source.acquisition_method]["label"]
            if source.acquisition_method in SUPPORTED_METHODS
            else (source.acquisition_method or "")
        ),
        "endpointUrl": source.endpoint_url or "",
        "dataFormat": source.data_format or "",
        "frequency": source.frequency or "",
        "updateSchedule": source.update_schedule or "",
        "status": source.status,
        "lastFetch": _last_fetch_info(source),
    }


# ---------------------------------------------------------------------------
# Sesi Admin (session auth bawaan Django, khusus staf)
# ---------------------------------------------------------------------------


@csrf_exempt
@require_POST
def admin_login(request):
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return json_error(parse_error, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return json_error("Username dan password wajib diisi.", status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return json_error("Kredensial tidak valid.", status=401)
    if not user.is_staff:
        return json_error("Akun tidak memiliki hak pengelolaan sumber.", status=403)
    login(request, user)
    return json_success({"username": user.get_username(), "isStaff": True})


@csrf_exempt
@require_POST
def admin_logout(request):
    logout(request)
    return json_success({"loggedOut": True})


@require_GET
def admin_session(request):
    user = getattr(request, "user", None)
    authenticated = bool(user and user.is_authenticated and user.is_staff)
    return json_success(
        {
            "authenticated": authenticated,
            "username": user.get_username() if authenticated else None,
            "isStaff": bool(user and user.is_authenticated and user.is_staff),
        }
    )


@require_GET
def acquisition_methods(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    return json_success(
        {
            "methods": [
                {"value": value, **meta} for value, meta in SUPPORTED_METHODS.items()
            ],
            "frequencies": FREQUENCIES,
        }
    )


@require_GET
def admin_source_list(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    sources = list(Source.objects.all().order_by("source_id"))
    return json_success(
        {"sources": [_serialize_admin_entry(s) for s in sources], "count": len(sources)}
    )


@csrf_exempt
@require_POST
def admin_source_create(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return json_error(parse_error, status=400)

    source_id = (data.get("sourceId") or data.get("source_id") or "").strip().upper()
    source_name = (data.get("sourceName") or data.get("source_name") or "").strip()
    institution = (data.get("institution") or "").strip()
    primary_url = (data.get("primaryUrl") or data.get("primary_url") or "").strip()
    description = (data.get("description") or "").strip()
    method = (data.get("acquisitionMethod") or data.get("acquisition_method") or "").strip()
    endpoint_url = (data.get("endpointUrl") or data.get("endpoint_url") or "").strip()
    data_format = (data.get("dataFormat") or data.get("data_format") or "").strip()
    frequency = (data.get("frequency") or "").strip()
    update_schedule = (data.get("updateSchedule") or data.get("update_schedule") or "").strip()
    status = (data.get("status") or "active").strip()

    # ── Validasi wajib ──────────────────────────────────────────────────
    if not source_id:
        return json_error("Field 'sourceId' wajib diisi.", status=400)
    if len(source_id) > 32:
        return json_error("Field 'sourceId' maksimal 32 karakter.", status=400)
    if not all(ch.isalnum() or ch == "_" for ch in source_id):
        return json_error("Field 'sourceId' hanya boleh huruf, angka, dan garis bawah.", status=400)
    if not source_name:
        return json_error("Field 'sourceName' wajib diisi.", status=400)
    if not institution:
        return json_error("Field 'institution' wajib diisi.", status=400)
    if not primary_url:
        return json_error("Field 'primaryUrl' wajib diisi.", status=400)
    if not _is_valid_http_url(primary_url):
        return json_error("Field 'primaryUrl' harus URL http(s) yang valid.", status=400)
    if not method:
        return json_error("Field 'acquisitionMethod' wajib diisi.", status=400)
    if method not in SUPPORTED_METHODS:
        return json_error(
            f"Metode '{method}' belum didukung. Pilihan: {sorted(SUPPORTED_METHODS)}.",
            status=400,
        )
    if not data_format:
        return json_error("Field 'dataFormat' wajib diisi.", status=400)
    if data_format not in SUPPORTED_METHODS[method]["formats"]:
        return json_error(
            f"Format '{data_format}' tidak didukung metode '{method}'. "
            f"Format valid: {SUPPORTED_METHODS[method]['formats']}.",
            status=400,
        )
    if not frequency:
        return json_error("Field 'frequency' wajib diisi.", status=400)
    if frequency not in FREQUENCIES:
        return json_error(
            f"Frekuensi '{frequency}' tidak valid. Pilihan: {FREQUENCIES}.", status=400
        )
    if status not in ("active", "inactive"):
        return json_error("Field 'status' harus 'active' atau 'inactive'.", status=400)
    if len(source_name) > 200 or len(institution) > 200:
        return json_error("Nama sumber/institusi maksimal 200 karakter.", status=400)

    meta = SUPPORTED_METHODS[method]
    if meta["endpointRequired"] and not endpoint_url:
        return json_error(
            f"Metode '{method}' membutuhkan endpoint URL.", status=400
        )
    if endpoint_url and not (
        _is_valid_http_url(endpoint_url) or endpoint_url.startswith("file://")
    ):
        return json_error(
            "Field 'endpointUrl' harus URL http(s) valid atau path file://.", status=400
        )

    # ── Duplikasi ───────────────────────────────────────────────────────
    if Source.objects.filter(source_id__iexact=source_id).exists():
        return json_error(f"Sumber '{source_id}' sudah terdaftar.", status=409)
    if Source.objects.filter(
        source_name__iexact=source_name, institution__iexact=institution
    ).exists():
        return json_error(
            "Kombinasi nama sumber dan institusi sudah terdaftar.", status=409
        )

    # ── Probing aksesibilitas SEBELUM menyimpan (tanpa sinkronisasi) ────
    if endpoint_url.startswith("http"):
        reachable, reason = _probe_endpoint_reachable(endpoint_url)
        if not reachable:
            logger.warning("Tolak sumber %s: %s", source_id, reason)
            return json_error(
                f"Endpoint tidak dapat diakses ({reason}). "
                "Konfigurasi ditolak; data lama dipertahankan.",
                status=400,
            )

    # ── Simpan atomik + audit ───────────────────────────────────────────
    with transaction.atomic():
        source = Source.objects.create(
            source_id=source_id,
            source_name=source_name[:200],
            institution=institution[:200],
            primary_url=primary_url,
            description=description,
            acquisition_method=method,
            endpoint_url=endpoint_url,
            data_format=data_format,
            frequency=frequency,
            update_schedule=update_schedule[:200],
            status=status,
        )
        record_update_success(
            f"sumber:{source.source_id}",
            updated_by=request.user,
            observation_count=0,
            message=f"Tambah sumber {source.source_id} ({source.institution}) via Admin.",
        )

    logger.info("Sumber ditambahkan: %s oleh %s", source.source_id, request.user)
    from django.http import JsonResponse

    return JsonResponse({"source": _serialize_admin_entry(source)}, status=201)
