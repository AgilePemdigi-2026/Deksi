"""Feature 27: endpoint pemulihan default (staff only)."""
from django.views.decorators.http import require_http_methods

from indicators.config_restore_service import RESTORABLE_DOMAINS, restore_domains
from indicators.source_admin_views import _parse_json_body, _require_staff
from indicators.views import json_error, json_success


@require_http_methods(["POST"])
def config_restore(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    data, err = _parse_json_body(request)
    if err:
        return json_error(err, status=400)
    domains = data.get("domains", list(RESTORABLE_DOMAINS))
    if not isinstance(domains, list) or not domains or not all(
        isinstance(d, str) for d in domains
    ):
        return json_error("Field domains harus list string tidak kosong.", status=400)
    unknown = [d for d in domains if d not in RESTORABLE_DOMAINS]
    if unknown:
        return json_error(f"Domain tidak dikenal: {', '.join(unknown)}.", status=400)
    results = restore_domains(domains=domains, actor=request.user)
    failed = [d for d, items in results.items()
              for i in items if i.get("status") == "rejected"]
    if failed:
        return json_error("Pemulihan ditolak untuk domain yang tidak dikenal.", status=400)
    return json_success({
        "results": results,
        "message": "Konfigurasi dikembalikan ke pengaturan awal",
    })
