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
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from indicators.feedback_model import Feedback
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

    # ΓöÇΓöÇ Validasi wajib ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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

    # ΓöÇΓöÇ Validasi opsional ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    sender_name = (data.get("sender_name") or "").strip()

    sender_email = (data.get("sender_email") or "").strip()
    if sender_email:
        try:
            validate_email(sender_email)
        except ValidationError:
            return json_error("Format email tidak valid.", status=400)

    related_code = (data.get("related_indicator_code") or "").strip()
    related_period = (data.get("related_period") or "").strip()

    # ΓöÇΓöÇ Simpan ke database ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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
