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

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from indicators.feedback_model import Feedback
from indicators.views import json_error, json_success

logger = logging.getLogger(__name__)

# Panjang maksimum yang dapat diterima untuk kolom teks bebas
_MAX_DESCRIPTION_LEN = 2000
_MAX_NAME_LEN = 150
_MAX_PERIOD_LEN = 50


def _get_client_ip(request) -> str | None:
    """Ambil IP aktual klien dengan memperhatikan X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_json_body(request) -> tuple[dict | None, str | None]:
    """Kembalikan (data, error_message). Error bukan None jika body bukan JSON valid."""
    content_type = request.content_type or ""
    if "application/json" not in content_type:
        return None, "Content-Type harus application/json."
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Body permintaan bukan JSON yang valid."
    if not isinstance(data, dict):
        return None, "Payload JSON harus berupa objek ({}), bukan array atau skalar."
    return data, None


# ---------------------------------------------------------------------------
# POST /api/feedback/
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def submit_feedback(request):
    """
    Menerima umpan balik dari pengguna publik dan menyimpannya dengan status
    'Menunggu Ditinjau'.

    Body (JSON):
      category               str  wajib   – pilihan: data_error | methodology |
                                            visualization | source | other
      description            str  wajib   – 10–2000 karakter
      sender_name            str  opsional – maks 150 karakter
      sender_email           str  opsional – format email valid
      related_indicator_code str  opsional – mis. "pdb", "inflasi"
      related_period         str  opsional – mis. "Q1 2024"

    Respons 201:
      { "id": <int>, "status": "pending", "message": "..." }
    """
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return json_error(parse_error, status=400)

    # ── Validasi wajib ────────────────────────────────────────────────────
    category = (data.get("category") or "").strip()
    description = (data.get("description") or "").strip()

    valid_categories = {c.value for c in Feedback.Category}
    if not category:
        return json_error("Field 'category' wajib diisi.", status=400)
    if category not in valid_categories:
        return json_error(
            f"Nilai category '{category}' tidak dikenal. "
            f"Pilihan yang valid: {sorted(valid_categories)}",
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
    sender_name = (data.get("sender_name") or "").strip()[:_MAX_NAME_LEN]

    sender_email = (data.get("sender_email") or "").strip()
    if sender_email:
        # Validasi format minimal: ada "@" dan "." setelah "@"
        at_pos = sender_email.find("@")
        if at_pos < 1 or "." not in sender_email[at_pos:]:
            return json_error("Format email tidak valid.", status=400)

    related_code = (data.get("related_indicator_code") or "").strip()[:32]
    related_period = (data.get("related_period") or "").strip()[:_MAX_PERIOD_LEN]

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
        "Feedback diterima: id=%s category=%s indicator=%s",
        fb.pk, fb.category, fb.related_indicator_code or "-",
    )

    from django.http import JsonResponse
    return JsonResponse(
        {
            "id": fb.pk,
            "status": fb.status,
            "message": (
                "Umpan balik Anda berhasil dikirim dan akan segera ditinjau oleh tim DEKSI."
            ),
        },
        status=201,
    )


# ---------------------------------------------------------------------------
# GET /api/feedback/categories/
# ---------------------------------------------------------------------------

@require_GET
def feedback_categories(request):
    """
    Mengembalikan daftar pilihan kategori umpan balik.
    Digunakan front-end untuk mengisi <select> tanpa hardcode di sisi klien.
    """
    categories = [
        {"value": c.value, "label": c.label}
        for c in Feedback.Category
    ]
    return json_success({"categories": categories})
