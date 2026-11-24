"""Feature 24: Diagnostic Engine minimal yang membaca konfigurasi aktif.

Kontrak:
- Tidak mengubah rumus inti Economic Engine (indicators/views.py).
- Tidak menulis ulang Observation, nilai resmi, normalisasi CLEAN, atau data RAW.
- Hanya membandingkan nilai observasi terbaru yang sudah dipublikasi
  terhadap threshold aktif untuk menghasilkan status diagnostik.
"""
from decimal import Decimal

from indicators.threshold_model import DiagnosticThreshold
from indicators.threshold_registry import get_supported


def active_threshold_value(indicator_code: str, param_key: str) -> Decimal:
    row = DiagnosticThreshold.objects.filter(
        indicator_code=indicator_code, param_key=param_key, status="active",
    ).first()
    if row is not None:
        return row.value
    spec = get_supported(indicator_code, param_key)
    if spec is None:
        raise ValueError(f"Parameter '{param_key}' untuk indikator '{indicator_code}' tidak didukung.")
    return spec["default_value"]


def evaluate_observation(indicator_code: str, param_key: str, observed: Decimal | float | str | None) -> dict:
    """Bandingkan satu nilai observasi terhadap threshold aktif.

    Mengembalikan status 'melebihi' bila observed > threshold, selain itu 'normal'.
    Tidak pernah mengubah nilai ekonomi; hanya status diagnostik.
    """
    threshold = active_threshold_value(indicator_code, param_key)
    spec = get_supported(indicator_code, param_key)
    if observed is None or (isinstance(observed, str) and not observed.strip()):
        return {
            "indicatorCode": indicator_code, "paramKey": param_key,
            "threshold": str(threshold), "unit": spec["unit"] if spec else "",
            "observed": None, "exceeded": False, "status": "tidak-tersedia",
            "impact": "Data observasi belum tersedia; threshold tidak dievaluasi.",
        }
    try:
        value = Decimal(str(observed))
    except Exception:
        return {
            "indicatorCode": indicator_code, "paramKey": param_key,
            "threshold": str(threshold), "unit": spec["unit"] if spec else "",
            "observed": str(observed), "exceeded": False, "status": "tidak-valid",
            "impact": "Nilai observasi tidak dapat dibandingkan terhadap threshold.",
        }
    exceeded = value > threshold
    return {
        "indicatorCode": indicator_code, "paramKey": param_key,
        "threshold": str(threshold), "unit": spec["unit"] if spec else "",
        "observed": str(value), "exceeded": exceeded,
        "status": "melebihi" if exceeded else "normal",
        "impact": (
            f"Nilai terbaru {value} melebihi batas {threshold} {spec['unit']}."
            if exceeded and spec else
            f"Nilai terbaru {value} berada dalam batas {threshold} {spec['unit']}."
            if spec else "Evaluasi selesai."
        ),
    }


def latest_published_value(indicator_code: str):
    """Ambil nilai observasi terbaru yang sudah dipublikasi + direview.

    Mengembalikan (value, unit, period_label) atau (None, None, None).
    Fungsi ini read-only terhadap Economic Engine.
    """
    from indicators.models import Indicator, Observation

    indicator = Indicator.objects.filter(code=indicator_code).first()
    if indicator is None:
        return None, None, None
    latest = (
        Observation.objects.filter(
            indicator=indicator,
            validation_status=Observation.Status.PUBLISHED,
            reviewed_by__isnull=False,
            reviewed_at__isnull=False,
        )
        .order_by("observation_date", "id")
        .last()
    )
    if latest is None:
        return None, indicator.unit, None
    return latest.value, latest.unit or indicator.unit, latest.period_label
