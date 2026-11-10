"""Dashboard filter API, adapted from the team's feature 5 checkpoint."""

import re

from django.views.decorators.http import require_GET

from indicators.models import Indicator
from indicators.updates import latest_successful_update, serialize_update_log
from indicators.views import (
    FRONTEND_INDICATOR_CODES,
    json_error,
    json_success,
    serialize_summary_card,
)

INDICATOR_CATEGORY_MAP = {
    "pdb": "PDB",
    "inflasi": "Inflasi",
    "fiskal": "Fiskal",
    "investasi": "Investasi",
    "birate": "Moneter",
    "tpt": "Tenaga Kerja",
}


@require_GET
def indicator_categories(request):
    """
    GET /api/indicators/categories/

    Mengembalikan daftar kategori beserta daftar kode indikator yang tersedia
    di tiap kategori.  Digunakan front-end untuk mengisi kontrol filter.
    """
    categories: dict[str, list[str]] = {}
    for code in FRONTEND_INDICATOR_CODES:
        cat = INDICATOR_CATEGORY_MAP.get(code, "Lainnya")
        categories.setdefault(cat, []).append(code)
    result = [{"category": cat, "codes": codes} for cat, codes in categories.items()]
    return json_success({"categories": result})


@require_GET
def indicator_dashboard_filter(request):
    """
    GET /api/indicators/dashboard/

    Query params:
      category (str)  - nama kategori, mis. "PDB" atau "Inflasi"
      year     (int)  - tahun pengamatan, mis. 2024

    Mengembalikan payload yang sama dengan indicator_summary, namun disaring
    berdasarkan parameter yang diberikan.  Jika tidak ada parameter, perilaku
    identik dengan indicator_summary tanpa filter.
    """
    if set(request.GET) - {"category", "year", "code"} or any(
        len(request.GET.getlist(key)) > 1 for key in ("category", "year")
    ):
        return json_error("Parameter filter tidak didukung atau berulang.", status=400)
    raw_category = request.GET.get("category", "").strip()
    raw_year = request.GET.get("year", "").strip()

    # Validasi tahun
    if raw_year:
        if not re.fullmatch(r"[0-9]{1,4}", raw_year) or int(raw_year) < 1:
            return json_error("Parameter 'year' harus berupa tahun 1-9999.", status=400)
        filter_year = int(raw_year)
    else:
        filter_year = None

    # Tentukan kode yang akan dikembalikan
    if raw_category:
        codes = [code for code, cat in INDICATOR_CATEGORY_MAP.items() if cat.lower() == raw_category.lower()]
        if not codes:
            return json_error(
                f"Kategori '{raw_category}' tidak dikenal. "
                f"Pilihan yang tersedia: {sorted(set(INDICATOR_CATEGORY_MAP.values()))}",
                status=400,
            )
    else:
        codes = list(request.GET.getlist("code") or FRONTEND_INDICATOR_CODES)

    indicators = []
    for code in codes:
        indicator = Indicator.objects.filter(code=code).first()
        if indicator is None:
            indicators.append(
                {
                    "id": code,
                    "available": False,
                    "name": code,
                    "category": INDICATOR_CATEGORY_MAP.get(code, ""),
                    "value": None,
                    "unit": "",
                    "period": None,
                    "note": "Indikator belum terdefinisi di database.",
                }
            )
            continue

        card = serialize_summary_card(indicator, year=filter_year)
        indicators.append(card)

    # Metadata filter aktif yang diteruskan ke front-end
    active_filters: dict = {}
    if raw_category:
        active_filters["category"] = raw_category
    if filter_year is not None:
        active_filters["year"] = filter_year

    update = serialize_update_log(latest_successful_update())
    return json_success(
        {
            "updatedAt": update["updatedAt"] if update else None,
            "updatedAtFormatted": update["formatted"] if update else None,
            "lastUpdate": update,
            "activeFilters": active_filters,
            "indicators": indicators,
        }
    )
