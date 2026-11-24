"""Feature 24: API konfigurasi threshold diagnostik (staff only)."""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.views.decorators.http import require_GET, require_http_methods

from indicators.diagnostic_engine import evaluate_observation, latest_published_value
from indicators.models import Indicator
from indicators.source_admin_views import _parse_json_body, _require_staff
from indicators.threshold_model import DiagnosticThreshold, DiagnosticThresholdAudit
from indicators.threshold_registry import SUPPORTED_THRESHOLDS, all_supported, get_supported
from indicators.views import json_error, json_success


def _serialize_row(code: str, spec: dict, row: DiagnosticThreshold | None, latest_value=None) -> dict:
    value = row.value if row else spec["default_value"]
    return {
        "indicatorCode": code,
        "indicatorName": spec.get("indicatorName") or code,
        "category": spec["category"],
        "paramKey": spec["param_key"],
        "label": spec["label"],
        "value": str(value),
        "unit": spec["unit"],
        "minAllowed": str(spec["min_allowed"]),
        "maxAllowed": str(spec["max_allowed"]),
        "description": spec["description"],
        "status": row.status if row else "active",
        "configured": row is not None,
        "version": row.version if row else 0,
        "updatedAt": row.updated_at.isoformat() if row and row.updated_at else None,
        "updatedBy": row.updated_by.get_username() if row and row.updated_by else None,
        "latestValue": str(latest_value) if latest_value is not None else None,
    }


def _resolve_indicator_name(code: str) -> str:
    indicator = Indicator.objects.filter(code=code).first()
    if indicator is not None:
        return indicator.name
    names = {"pdb": "PDB", "inflasi": "Inflasi", "fiskal": "Fiskal",
             "investasi": "Investasi", "birate": "BI-Rate", "tpt": "Pengangguran"}
    return names.get(code, code)


def _validate_payload(code: str, spec: dict, data: dict) -> tuple[Decimal, str | None]:
    if "value" not in data:
        return Decimal("0"), "Field 'value' wajib diisi."
    raw = data["value"]
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return Decimal("0"), "Nilai threshold harus berupa angka."
    unit = str(data.get("unit", spec["unit"])).strip()
    if unit != spec["unit"]:
        return Decimal("0"), f"Satuan harus '{spec['unit']}' sesuai definisi parameter."
    if value < spec["min_allowed"] or value > spec["max_allowed"]:
        return Decimal("0"), (
            f"Nilai batas tidak valid. Nilai threshold berada di luar rentang yang diperbolehkan "
            f"({spec['min_allowed']}-{spec['max_allowed']} {spec['unit']}). "
            f"Periksa kembali nilai dan satuan yang digunakan."
        )
    _ = code
    return value, None


@require_GET
def threshold_list(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    rows = {(r.indicator_code, r.param_key): r for r in DiagnosticThreshold.objects.all()}
    items = []
    for code in sorted(SUPPORTED_THRESHOLDS):
        for spec in SUPPORTED_THRESHOLDS[code]:
            enriched = dict(spec, indicatorName=_resolve_indicator_name(code))
            latest, _, _ = latest_published_value(code)
            items.append(_serialize_row(code, enriched, rows.get((code, spec["param_key"])), latest))
    return json_success({"thresholds": items, "count": len(items)})


@require_GET
def threshold_supported(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    return json_success({"supported": all_supported()})


@require_GET
def threshold_detail(request, code: str, param: str):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    spec = get_supported(code, param)
    if spec is None:
        if code not in SUPPORTED_THRESHOLDS:
            return json_error(f"Indikator '{code}' tidak terdaftar atau tidak mendukung threshold.", status=404)
        return json_error(f"Parameter '{param}' tidak didukung untuk indikator '{code}'.", status=404)
    indicator = Indicator.objects.filter(code=code).first()
    if indicator is None:
        return json_error(f"Indikator '{code}' tidak terdaftar di database.", status=404)
    enriched = dict(spec, indicatorName=indicator.name)
    row = DiagnosticThreshold.objects.filter(indicator_code=code, param_key=param).first()
    latest, latest_unit, period = latest_published_value(code)
    item = _serialize_row(code, enriched, row, latest)
    evaluation = evaluate_observation(code, param, latest)
    return json_success({"threshold": item, "evaluation": evaluation,
                         "latestPeriod": period, "latestUnit": latest_unit})


@require_http_methods(["PUT"])
def threshold_update(request, code: str, param: str):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    spec = get_supported(code, param)
    if spec is None:
        if code not in SUPPORTED_THRESHOLDS:
            return json_error(f"Indikator '{code}' tidak terdaftar atau tidak mendukung threshold.", status=404)
        return json_error(f"Parameter '{param}' tidak didukung untuk indikator '{code}'.", status=404)
    indicator = Indicator.objects.filter(code=code).first()
    if indicator is None:
        return json_error(f"Indikator '{code}' tidak terdaftar di database.", status=404)
    data, err = _parse_json_body(request)
    if err:
        return json_error(err, status=400)
    value, problem = _validate_payload(code, spec, data)
    if problem:
        return json_error(problem, status=400)
    status = str(data.get("status", "active")).strip() or "active"
    if status not in ("active", "inactive"):
        return json_error("Field 'status' harus 'active' atau 'inactive'.", status=400)
    with transaction.atomic():
        row = DiagnosticThreshold.objects.select_for_update().filter(
            indicator_code=code, param_key=param).first()
        old = _serialize_row(code, dict(spec, indicatorName=indicator.name), row)
        if row is None:
            row = DiagnosticThreshold.objects.create(
                indicator_code=code, param_key=param, value=value, unit=spec["unit"],
                min_allowed=spec["min_allowed"], max_allowed=spec["max_allowed"],
                status=status, version=1, updated_by=request.user,
            )
        else:
            row.value = value
            row.unit = spec["unit"]
            row.min_allowed = spec["min_allowed"]
            row.max_allowed = spec["max_allowed"]
            row.status = status
            row.version += 1
            row.updated_by = request.user
            row.save()
        new = _serialize_row(code, dict(spec, indicatorName=indicator.name), row)
        DiagnosticThresholdAudit.objects.create(
            indicator_code=code, param_key=param, old_value=old, new_value=new,
            actor=request.user, reason=str(data.get("reason", ""))[:500],
        )
    latest, _, _ = latest_published_value(code)
    evaluation = evaluate_observation(code, param, latest)
    return json_success({"threshold": new, "evaluation": evaluation,
                         "message": "Konfigurasi tersimpan"})


@require_GET
def threshold_history(request, code: str, param: str):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    if get_supported(code, param) is None:
        return json_error(f"Parameter '{param}' untuk indikator '{code}' tidak didukung.", status=404)
    rows = DiagnosticThresholdAudit.objects.filter(
        indicator_code=code, param_key=param).order_by("-created_at", "-id")[:50]
    return json_success({"history": [{
        "oldValue": r.old_value, "newValue": r.new_value,
        "actor": r.actor.get_username() if r.actor else None,
        "reason": r.reason, "createdAt": r.created_at.isoformat() if r.created_at else None,
    } for r in rows], "count": len(rows)})


@require_GET
def diagnostic_evaluate(request):
    """Bukti integrasi: Diagnostic Engine membaca threshold aktif + observasi terbaru."""
    denied = _require_staff(request)
    if denied is not None:
        return denied
    code = (request.GET.get("indicator") or request.GET.get("code") or "").strip()
    param = (request.GET.get("param") or "").strip()
    if not code:
        return json_error("Parameter 'indicator' wajib diisi.", status=400)
    if code not in SUPPORTED_THRESHOLDS:
        return json_error(f"Indikator '{code}' tidak terdaftar atau tidak mendukung threshold.", status=404)
    if not param:
        param = SUPPORTED_THRESHOLDS[code][0]["param_key"]
    spec = get_supported(code, param)
    if spec is None:
        return json_error(f"Parameter '{param}' tidak didukung untuk indikator '{code}'.", status=404)
    latest, unit, period = latest_published_value(code)
    result = evaluate_observation(code, param, latest)
    result["latestUnit"] = unit
    result["latestPeriod"] = period
    return json_success({"diagnostic": result})
