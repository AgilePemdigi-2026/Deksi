"""
Views untuk Fitur 8: Kirim Umpan Balik (UC-05).

Konvensi mengikuti indicators/views.py:
  - function-based views
  - @require_POST untuk endpoint mutasi
  - json_success / json_error sebagai helper respons
  - validasi manual (tanpa DRF serializer) agar dependensi tetap minimal
"""

import json
import logging
from ipaddress import ip_address

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from indicators.feedback_model import Feedback, FeedbackAuditLog
from indicators.models import Indicator
from indicators.views import json_error, json_success

logger = logging.getLogger(__name__)

# Panjang maksimum yang dapat diterima untuk kolom teks bebas
_MAX_DESCRIPTION_LEN = 2000
_MAX_NAME_LEN = 150
_MAX_PERIOD_LEN = 50
_MAX_BODY_BYTES = 32 * 1024


def _get_client_ip(request) -> str | None:
    """Use the direct peer; trusting proxy headers needs an explicit proxy policy."""
    try:
        return str(ip_address(request.META.get("REMOTE_ADDR", "")))
    except ValueError:
        return None


def _unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate JSON field")
    return result


def _reject_constant(_value):
    raise ValueError("Non-finite JSON constant")


def _parse_json_body(request):
    """Return parsed UTF-8 JSON or a bounded, public error response."""
    content_type = request.content_type or ""
    if content_type != "application/json":
        return None, json_error("Content-Type harus application/json.", status=400)
    body = request.read(_MAX_BODY_BYTES + 1)
    if len(body) > _MAX_BODY_BYTES:
        return None, json_error("Body permintaan terlalu besar.", status=413)
    try:
        data = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return None, json_error("Body permintaan bukan JSON yang valid.", status=400)
    if not isinstance(data, dict):
        return None, json_error("Payload JSON harus berupa objek, bukan array atau skalar.", status=400)
    return data, None


# ---------------------------------------------------------------------------
# POST /api/feedback/
# ---------------------------------------------------------------------------


@require_POST
def submit_feedback(request):
    """
    Menerima umpan balik dari pengguna publik dan menyimpannya dengan status
    'Menunggu Ditinjau'.

    Body (JSON):
      category               str  wajib   - pilihan: data_error | methodology |
                                            visualization | source | other
      description            str  wajib   - 10-2000 karakter
      sender_name            str  opsional - maks 150 karakter
      sender_email           str  opsional - format email valid
      related_indicator_code str  opsional - mis. "pdb", "inflasi"
      related_period         str  opsional - mis. "Q1 2024"

    Respons 201:
      { "id": <int>, "status": "pending", "message": "..." }
    """
    data, parse_error = _parse_json_body(request)
    if parse_error is not None:
        return parse_error
    data = data or {}
    limits = {
        "sender_name": _MAX_NAME_LEN,
        "sender_email": 254,
        "related_indicator_code": 32,
        "related_period": _MAX_PERIOD_LEN,
    }
    for field in ("category", "description", *limits):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            return json_error(f"Field '{field}' harus berupa teks.", status=400)
        if value is not None:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                return json_error(f"Field '{field}' mengandung Unicode tidak valid.", status=400)
        if field in limits and len((value or "").strip()) > limits[field]:
            return json_error(f"Field '{field}' terlalu panjang.", status=400)

    # ── Validasi wajib ────────────────────────────────────────────────────
    category = (data.get("category") or "").strip()
    description = (data.get("description") or "").strip()

    valid_categories = {c.value for c in Feedback.Category}
    if not category:
        return json_error("Field 'category' wajib diisi.", status=400)
    if category not in valid_categories:
        return json_error(
            f"Nilai category '{category}' tidak dikenal. Pilihan yang valid: {sorted(valid_categories)}",
            status=400,
        )

    if not description:
        return json_error("Field 'description' wajib diisi.", status=400)
    if len(description) < 10:
        return json_error("Deskripsi terlalu singkat; minimal 10 karakter.", status=400)
    if len(description) > _MAX_DESCRIPTION_LEN:
        return json_error(
            f"Deskripsi terlalu panjang; maksimal {_MAX_DESCRIPTION_LEN} karakter.",
            status=400,
        )

    # ── Validasi opsional ─────────────────────────────────────────────────
    sender_name = (data.get("sender_name") or "").strip()

    sender_email = (data.get("sender_email") or "").strip()
    if sender_email:
        try:
            validate_email(sender_email)
        except ValidationError:
            return json_error("Format email tidak valid.", status=400)

    related_code = (data.get("related_indicator_code") or "").strip()
    related_period = (data.get("related_period") or "").strip()

    # ── Simpan ke database ────────────────────────────────────────────────
    fb = Feedback.objects.create(
        category=category,
        description=description,
        sender_name=sender_name,
        sender_email=sender_email,
        related_indicator_code=related_code,
        related_period=related_period,
        ip_address=_get_client_ip(request),
    )

    logger.info(
        "Feedback diterima: id=%s category=%s",
        fb.pk,
        fb.category,
    )

    from django.http import JsonResponse

    response = JsonResponse(
        {
            "id": fb.pk,
            "status": fb.status,
            "message": ("Umpan balik Anda berhasil dikirim dan akan segera ditinjau oleh tim DEKSI."),
        },
        status=201,
    )
    response["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# GET /api/feedback/categories/
# ---------------------------------------------------------------------------


@ensure_csrf_cookie
@require_GET
def feedback_categories(request):
    """
    Mengembalikan daftar pilihan kategori umpan balik.
    Digunakan front-end untuk mengisi <select> tanpa hardcode di sisi klien.
    """
    categories = [{"value": c.value, "label": c.label} for c in Feedback.Category]
    return json_success({"categories": categories, "csrfToken": get_token(request)})


# ---------------------------------------------------------------------------
# Helper Serialization
# ---------------------------------------------------------------------------


def _serialize_feedback_item(fb: Feedback) -> dict:
    return {
        "id": fb.pk,
        "category": fb.category,
        "category_label": fb.get_category_display(),
        "description": fb.description,
        "sender_name": fb.sender_name,
        "sender_email": fb.sender_email,
        "related_indicator_code": fb.related_indicator_code,
        "related_period": fb.related_period,
        "status": fb.status,
        "status_label": fb.get_status_display(),
        "admin_notes": fb.admin_notes,
        "ip_address": fb.ip_address,
        "created_at": fb.created_at.isoformat() if fb.created_at else None,
        "updated_at": fb.updated_at.isoformat() if fb.updated_at else None,
    }


def _require_feedback_staff(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return json_error("Autentikasi diperlukan.", status=401)
    if not user.is_staff:
        return json_error("Hak akses admin diperlukan.", status=403)
    return None


# ---------------------------------------------------------------------------
# Fitur 15: Daftar Umpan Balik (Admin)
# ---------------------------------------------------------------------------


@require_GET
def admin_feedback_list(request):
    """
    Memuat daftar laporan pengguna dengan pencarian kata kunci dan filter status/kategori.
    Query params:
      q / search: mencari deskripsi, pengirim, email, indikator, atau periode
      status: filter status penanganan
      category: filter kategori
    """
    denied = _require_feedback_staff(request)
    if denied is not None:
        return denied

    qs = Feedback.objects.all().order_by("-created_at")

    search_query = (request.GET.get("q") or request.GET.get("search") or "").strip()
    if search_query:
        qs = qs.filter(
            Q(description__icontains=search_query)
            | Q(sender_name__icontains=search_query)
            | Q(sender_email__icontains=search_query)
            | Q(related_indicator_code__icontains=search_query)
            | Q(related_period__icontains=search_query)
        )

    # Filter status penanganan
    status_param = (request.GET.get("status") or "").strip()
    if status_param and status_param != "all":
        qs = qs.filter(status=status_param)

    # Filter kategori laporan
    category_param = (request.GET.get("category") or "").strip()
    if category_param and category_param != "all":
        qs = qs.filter(category=category_param)

    items = [_serialize_feedback_item(fb) for fb in qs]
    return json_success({
        "count": len(items),
        "search_query": search_query,
        "feedbacks": items,
        "available_statuses": [
            {"value": s.value, "label": s.label} for s in Feedback.Status
        ],
    })


# ---------------------------------------------------------------------------
# Fitur 16: Detail Umpan Balik dan Indikator Terkait (Admin)
# ---------------------------------------------------------------------------


def _serialize_feedback_detail(fb: Feedback) -> dict:
    data = _serialize_feedback_item(fb)
    related_indicator = None
    if fb.related_indicator_code:
        indicator = Indicator.objects.filter(code__iexact=fb.related_indicator_code).first()
        if indicator:
            related_indicator = {
                "code": indicator.code,
                "name": indicator.name,
                "category": indicator.category,
                "unit": indicator.unit,
            }
        else:
            related_indicator = {
                "code": fb.related_indicator_code,
                "name": fb.related_indicator_code.upper(),
                "category": "-",
                "unit": "-",
            }
    data["related_indicator"] = related_indicator
    data["audit_logs"] = [
        {
            "id": log.pk,
            "old_status": log.old_status,
            "old_status_label": log.get_old_status_display(),
            "new_status": log.new_status,
            "new_status_label": log.get_new_status_display(),
            "notes": log.notes,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at.isoformat() if log.changed_at else None,
        }
        for log in fb.audit_logs.all().order_by("-changed_at")
    ]
    return data


@ensure_csrf_cookie
@require_GET
def admin_feedback_detail(request, feedback_id: int):
    denied = _require_feedback_staff(request)
    if denied is not None:
        return denied

    fb = Feedback.objects.filter(pk=feedback_id).first()
    if fb is None:
        return json_error("Umpan balik tidak ditemukan.", status=404)

    return json_success({"feedback": _serialize_feedback_detail(fb), "csrfToken": get_token(request)})


# ---------------------------------------------------------------------------
# Fitur 18: Ubah Status Umpan Balik dan Catat Audit Log (Admin)
# ---------------------------------------------------------------------------


@require_http_methods(["POST", "PATCH"])
def admin_feedback_update_status(request, feedback_id: int):
    denied = _require_feedback_staff(request)
    if denied is not None:
        return denied

    data, parse_error = _parse_json_body(request)
    if parse_error is not None:
        return parse_error
    data = data or {}

    status_value = data.get("status")
    if not isinstance(status_value, str) or not status_value.strip():
        return json_error("Field 'status' wajib diisi.", status=400)
    new_status = status_value.strip()
    valid_statuses = {status.value for status in Feedback.Status}
    if new_status not in valid_statuses:
        return json_error(
            f"Status '{new_status}' tidak valid. Pilihan valid: {sorted(valid_statuses)}",
            status=400,
        )

    notes = data.get("notes", "")
    if not isinstance(notes, str):
        return json_error("Field 'notes' harus berupa teks.", status=400)
    notes = notes.strip()
    if len(notes) > _MAX_DESCRIPTION_LEN:
        return json_error(
            f"Catatan penanganan maksimal {_MAX_DESCRIPTION_LEN} karakter.", status=400
        )

    user = request.user
    changed_by = (user.get_full_name() or user.get_username() or "Admin")[:150]
    with transaction.atomic():
        fb = Feedback.objects.select_for_update().filter(pk=feedback_id).first()
        if fb is None:
            return json_error("Umpan balik tidak ditemukan.", status=404)

        old_status = fb.status
        FeedbackAuditLog.objects.create(
            feedback=fb,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            changed_by=changed_by,
        )
        fb.status = new_status
        fb.admin_notes = notes
        fb.save(update_fields=["status", "admin_notes", "updated_at"])

    logger.info(
        "Status feedback #%s diubah dari '%s' ke '%s' oleh %s",
        fb.pk,
        old_status,
        new_status,
        changed_by,
    )
    return json_success({
        "feedback": _serialize_feedback_detail(fb),
        "csrfToken": get_token(request),
    })
