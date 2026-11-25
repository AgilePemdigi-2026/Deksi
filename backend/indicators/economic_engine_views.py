"""Public deterministic calculations from reviewed source observations."""
from datetime import date

from django.views.decorators.http import require_GET

from indicators.economic_engine import METHOD_VERSION, SCHEMA_VERSION, calculate_gdp_shares
from indicators.models import Observation
from indicators.views import json_error, json_success


@require_GET
def gdp_shares(request):
    if set(request.GET) - {"quarter"} or len(request.GET.getlist("quarter")) > 1:
        return json_error("Parameter periode tidak valid atau ambigu.", status=400)
    try:
        requested = request.GET.get("quarter")
        if requested is None:
            latest = Observation.objects.filter(
                indicator__code="pdb_nominal", source__source_id="BPS",
                validation_status=Observation.Status.PUBLISHED, reviewed_by__isnull=False, reviewed_at__isnull=False,
                frequency="quarterly", data_type="level", unit="Rp miliar",
            ).order_by("-observation_date", "-id").first()
            if latest is None:
                return json_success({"schemaVersion": SCHEMA_VERSION, "methodVersion": METHOD_VERSION,
                    "metrics": {}, "reason": "PDB nominal yang direview belum tersedia."})
            quarter = latest.observation_date
        else:
            quarter = date.fromisoformat(requested)
            if quarter.isoformat() != requested:
                raise ValueError("Noncanonical period")
        shares = calculate_gdp_shares(quarter)
    except ValueError:
        return json_error("Periode tidak valid: gunakan tanggal akhir triwulan.", status=400)
    return json_success({"schemaVersion": SCHEMA_VERSION, "methodVersion": METHOD_VERSION, "metrics": shares})


@require_GET
def trade_unavailable(request):
    return json_success({"available": False, "reason": "Kecocokan metodologi ekspor dan impor belum diverifikasi."})
