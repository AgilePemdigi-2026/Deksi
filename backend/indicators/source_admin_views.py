"""
Views untuk Fitur 10–11: Tambah/Edit Sumber Data (UC-06).

Konvensi mengikuti indicators/feedback_views.py:
  - function-based views, tanpa DRF
  - json_success / json_error dari indicators.views
  - validasi manual, transaksi atomik, tanpa sinkronisasi otomatis
"""

import ipaddress
import json
import logging
import socket
from urllib.parse import urljoin, urlparse

import httpx
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.http import require_http_methods

from indicators.models import RawFile, Source, SourceRevision, source_config_snapshot
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
PROBE_MAX_REDIRECTS = 3


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


def _host_public_ips(host: str) -> tuple[set[str] | None, str]:
    """Resolve host; (None, alasan) jika tak ter-resolve atau tak publik (anti-SSRF)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return None, "host tidak dapat di-resolve."
    ips = {info[4][0] for info in infos}
    for raw in ips:
        try:
            ip = ipaddress.ip_address(raw.split("%")[0])
        except ValueError:
            return None, f"alamat '{raw}' tidak valid."
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return None, f"host mengarah ke alamat non-publik ({raw})."
    return ips, ""


def _check_url_public(url: str) -> tuple[str, str]:
    """Validasi skema + host publik. Kembalikan (url, '') atau ('', alasan)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return "", "URL tidak valid."
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return "", "URL harus http(s) dengan host valid."
    _, reason = _host_public_ips(parsed.hostname)
    if reason:
        return "", f"URL ditolak ({reason})"
    return url, ""


def _fetch_no_redirect(client: httpx.Client, url: str) -> httpx.Response:
    try:
        response = client.head(url)
        if response.status_code in (403, 405):
            response = client.get(url, headers={"Range": "bytes=0-0"})
        return response
    except httpx.HTTPError:
        return client.get(url)


def _probe_endpoint_reachable(url: str) -> tuple[bool, str]:
    """HEAD lalu fallback GET ringan, redirect manual max 3 hop tervalidasi. True jika status < 400."""
    current = url
    try:
        with httpx.Client(timeout=PROBE_TIMEOUT_SECONDS, follow_redirects=False) as client:
            for _ in range(PROBE_MAX_REDIRECTS + 1):
                ok_url, reason = _check_url_public(current)
                if reason:
                    return False, reason
                try:
                    response = _fetch_no_redirect(client, ok_url)
                except httpx.HTTPError as exc:
                    return False, f"Endpoint tidak dapat dijangkau: {exc.__class__.__name__}."
                location = response.headers.get("location")
                if response.status_code in (301, 302, 303, 307, 308) and location:
                    current = urljoin(ok_url, location)
                    continue
                if response.status_code >= 400:
                    return False, f"Endpoint mengembalikan HTTP {response.status_code}."
                return True, ""
            return False, "Terlalu banyak redirect."
    except httpx.HTTPError as exc:
        return False, f"Endpoint tidak dapat dijangkau: {exc.__class__.__name__}."


def _resolve_field(data: dict, existing: str, *names: str) -> str:
    """Ambil dari payload (camel/snake); jika tak ada, pertahankan nilai lama."""
    for name in names:
        if name in data and data[name] is not None:
            return str(data[name]).strip()
    return existing


def _validate_values(values: dict, source_pk=None) -> str | None:
    """Validasi aturan konfigurasi. Kembalikan pesan error atau None."""
    if not values["source_name"]:
        return "Field 'sourceName' wajib diisi."
    if not values["institution"]:
        return "Field 'institution' wajib diisi."
    if not values["primary_url"]:
        return "Field 'primaryUrl' wajib diisi."
    if not _is_valid_http_url(values["primary_url"]):
        return "Field 'primaryUrl' harus URL http(s) yang valid."
    method = values["method"]
    if not method:
        return "Field 'acquisitionMethod' wajib diisi."
    if method not in SUPPORTED_METHODS:
        return (
            f"Metode '{method}' belum didukung. Pilihan: {sorted(SUPPORTED_METHODS)}."
        )
    if not values["data_format"]:
        return "Field 'dataFormat' wajib diisi."
    if values["data_format"] not in SUPPORTED_METHODS[method]["formats"]:
        return (
            f"Format '{values['data_format']}' tidak didukung metode '{method}'. "
            f"Format valid: {SUPPORTED_METHODS[method]['formats']}."
        )
    if not values["frequency"]:
        return "Field 'frequency' wajib diisi."
    if values["frequency"] not in FREQUENCIES:
        return f"Frekuensi '{values['frequency']}' tidak valid. Pilihan: {FREQUENCIES}."
    if values["status"] not in ("active", "inactive"):
        return "Field 'status' harus 'active' atau 'inactive'."
    if len(values["source_name"]) > 200 or len(values["institution"]) > 200:
        return "Nama sumber/institusi maksimal 200 karakter."
    if len(values["update_schedule"]) > 200:
        return "Jadwal pembaruan maksimal 200 karakter."
    if SUPPORTED_METHODS[method]["endpointRequired"] and not values["endpoint_url"]:
        return f"Metode '{method}' membutuhkan endpoint URL."
    if values["endpoint_url"] and not (
        _is_valid_http_url(values["endpoint_url"]) or values["endpoint_url"].startswith("file://")
    ):
        return "Field 'endpointUrl' harus URL http(s) valid atau path file://."
    dup = Source.objects.filter(
        source_name__iexact=values["source_name"],
        institution__iexact=values["institution"],
    )
    if source_pk is not None:
        dup = dup.exclude(pk=source_pk)
    if dup.exists():
        return "Kombinasi nama sumber dan institusi sudah terdaftar."
    return None


def _record_revision(source: Source, action: str, before: dict, user) -> dict:
    """Simpan revisi + audit. Panggil di dalam transaction yang sama dengan save."""
    after = source_config_snapshot(source)
    changed = [k for k in after if before.get(k) != after[k]] if before else list(after)
    last = (
        SourceRevision.objects.filter(source=source).order_by("-version").first()
    )
    version = (last.version + 1) if last else 1
    revision = SourceRevision.objects.create(
        source=source,
        version=version,
        action=action,
        before=before,
        after=after,
        changed_fields=changed,
        updated_by=user,
    )
    verb = "Tambah" if action == SourceRevision.Action.CREATE else "Edit"
    record_update_success(
        f"sumber:{source.source_id}",
        updated_by=user,
        observation_count=0,
        message=f"{verb} sumber {source.source_id} ({source.institution}) via Admin. "
        f"Ubah: {', '.join(changed) or '-'}.",
    )
    return _serialize_revision(revision)


def _serialize_revision(revision: SourceRevision) -> dict:
    return {
        "version": revision.version,
        "action": revision.action,
        "before": revision.before,
        "after": revision.after,
        "changedFields": revision.changed_fields,
        "updatedBy": revision.updated_by.get_username() if revision.updated_by else None,
        "createdAt": revision.created_at.isoformat() if revision.created_at else None,
    }


def _get_staff_source(source_id: str):
    source = Source.objects.filter(source_id__iexact=source_id).first()
    if source is None:
        return None, json_error(f"Sumber '{source_id}' tidak tersedia.", status=404)
    return source, None


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
    values = {
        "source_name": (data.get("sourceName") or data.get("source_name") or "").strip(),
        "institution": (data.get("institution") or "").strip(),
        "primary_url": (data.get("primaryUrl") or data.get("primary_url") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "method": (data.get("acquisitionMethod") or data.get("acquisition_method") or "").strip(),
        "endpoint_url": (data.get("endpointUrl") or data.get("endpoint_url") or "").strip(),
        "data_format": (data.get("dataFormat") or data.get("data_format") or "").strip(),
        "frequency": (data.get("frequency") or "").strip(),
        "update_schedule": (data.get("updateSchedule") or data.get("update_schedule") or "").strip(),
        "status": (data.get("status") or "active").strip(),
    }

    # ── Validasi wajib ──────────────────────────────────────────────────
    if not source_id:
        return json_error("Field 'sourceId' wajib diisi.", status=400)
    if len(source_id) > 32:
        return json_error("Field 'sourceId' maksimal 32 karakter.", status=400)
    if not all(ch.isalnum() or ch == "_" for ch in source_id):
        return json_error("Field 'sourceId' hanya boleh huruf, angka, dan garis bawah.", status=400)
    problem = _validate_values(values)
    if problem:
        return json_error(problem, status=400)

    # ── Duplikasi ───────────────────────────────────────────────────────
    if Source.objects.filter(source_id__iexact=source_id).exists():
        return json_error(f"Sumber '{source_id}' sudah terdaftar.", status=409)

    # ── Probing aksesibilitas SEBELUM menyimpan (tanpa sinkronisasi) ────
    if values["endpoint_url"].startswith("http"):
        reachable, reason = _probe_endpoint_reachable(values["endpoint_url"])
        if not reachable:
            logger.warning("Tolak sumber %s: %s", source_id, reason)
            return json_error(
                f"Endpoint tidak dapat diakses ({reason}). "
                "Konfigurasi ditolak; data lama dipertahankan.",
                status=400,
            )

    # ── Simpan atomik + revisi v1 + audit ───────────────────────────────
    with transaction.atomic():
        source = Source.objects.create(
            source_id=source_id,
            source_name=values["source_name"][:200],
            institution=values["institution"][:200],
            primary_url=values["primary_url"],
            description=values["description"],
            acquisition_method=values["method"],
            endpoint_url=values["endpoint_url"],
            data_format=values["data_format"],
            frequency=values["frequency"],
            update_schedule=values["update_schedule"][:200],
            status=values["status"],
        )
        revision = _record_revision(source, SourceRevision.Action.CREATE, {}, request.user)

    logger.info("Sumber ditambahkan: %s oleh %s", source.source_id, request.user)
    from django.http import JsonResponse

    return JsonResponse(
        {"source": _serialize_admin_entry(source), "revision": revision}, status=201
    )


@require_GET
def admin_source_detail(request, source_id: str):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    source, error = _get_staff_source(source_id)
    if error is not None:
        return error
    entry = _serialize_admin_entry(source)
    entry["revisionCount"] = source.revisions.count()
    return json_success(entry)


@require_GET
def admin_source_revisions(request, source_id: str):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    source, error = _get_staff_source(source_id)
    if error is not None:
        return error
    revisions = [_serialize_revision(r) for r in source.revisions.all()[:50]]
    return json_success(
        {"sourceId": source.source_id, "revisions": revisions, "count": len(revisions)}
    )


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def admin_source_update(request, source_id: str):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    source, error = _get_staff_source(source_id)
    if error is not None:
        return error
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return json_error(parse_error, status=400)

    # Identitas tidak dapat diubah.
    incoming_id = (data.get("sourceId") or data.get("source_id") or "").strip()
    if incoming_id and incoming_id.upper() != source.source_id.upper():
        return json_error("Field 'sourceId' tidak dapat diubah.", status=400)

    before = source_config_snapshot(source)
    values = {
        "source_name": _resolve_field(data, source.source_name, "sourceName", "source_name"),
        "institution": _resolve_field(data, source.institution, "institution"),
        "primary_url": _resolve_field(data, source.primary_url, "primaryUrl", "primary_url"),
        "description": _resolve_field(data, source.description, "description"),
        "method": _resolve_field(
            data, source.acquisition_method, "acquisitionMethod", "acquisition_method"
        ),
        "endpoint_url": _resolve_field(
            data, source.endpoint_url, "endpointUrl", "endpoint_url"
        ),
        "data_format": _resolve_field(data, source.data_format, "dataFormat", "data_format"),
        "frequency": _resolve_field(data, source.frequency, "frequency"),
        "update_schedule": _resolve_field(
            data, source.update_schedule, "updateSchedule", "update_schedule"
        ),
        "status": _resolve_field(data, source.status, "status") or "active",
    }
    problem = _validate_values(values, source_pk=source.pk)
    if problem:
        return json_error(problem, status=400)

    endpoint_changed = values["endpoint_url"] != (source.endpoint_url or "")
    method_changed = values["method"] != (source.acquisition_method or "")
    if (endpoint_changed or method_changed) and values["endpoint_url"].startswith("http"):
        reachable, reason = _probe_endpoint_reachable(values["endpoint_url"])
        if not reachable:
            logger.warning("Tolak edit %s: %s", source.source_id, reason)
            return json_error(
                f"Endpoint tidak dapat diakses ({reason}). "
                "Perubahan ditolak; konfigurasi terakhir yang valid dipertahankan.",
                status=400,
            )

    with transaction.atomic():
        source = Source.objects.select_for_update().get(pk=source.pk)
        source.source_name = values["source_name"][:200]
        source.institution = values["institution"][:200]
        source.primary_url = values["primary_url"]
        source.description = values["description"]
        source.acquisition_method = values["method"]
        source.endpoint_url = values["endpoint_url"]
        source.data_format = values["data_format"]
        source.frequency = values["frequency"]
        source.update_schedule = values["update_schedule"][:200]
        source.status = values["status"]
        source.save()
        after = source_config_snapshot(source)
        if after == before:
            return json_success(
                {"source": _serialize_admin_entry(source), "changedFields": []}
            )
        revision = _record_revision(source, SourceRevision.Action.UPDATE, before, request.user)

    logger.info("Sumber diubah: %s oleh %s", source.source_id, request.user)
    from django.http import JsonResponse

    return JsonResponse(
        {
            "source": _serialize_admin_entry(source),
            "revision": revision,
            "changedFields": revision["changedFields"],
        }
    )
