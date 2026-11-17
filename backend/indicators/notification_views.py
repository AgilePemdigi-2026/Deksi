"""Feature 26: API preferensi notifikasi (staff only)."""
from django.db import transaction
from django.views.decorators.http import require_GET, require_http_methods

from indicators.notification_model import NotificationAudit, NotificationPreference
from indicators.notification_service import DESCRIPTIONS, record_event, should_notify
from indicators.source_admin_views import _parse_json_body, _require_staff
from indicators.views import json_error, json_success


def _serialize(pref: NotificationPreference | None, kind: str) -> dict:
    enabled = pref.enabled if pref else None
    from indicators.notification_service import DEFAULTS
    return {
        "kind": kind,
        "label": NotificationPreference.Kind(kind).label,
        "description": DESCRIPTIONS.get(kind, ""),
        "enabled": enabled if enabled is not None else bool(DEFAULTS.get(kind, False)),
        "configured": pref is not None,
        "version": pref.version if pref else 0,
        "updatedAt": pref.updated_at.isoformat() if pref and pref.updated_at else None,
        "updatedBy": pref.updated_by.get_username() if pref and pref.updated_by else None,
    }


@require_GET
def notification_list(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    prefs = {p.kind: p for p in NotificationPreference.objects.all()}
    items = [_serialize(prefs.get(kind), kind) for kind in NotificationPreference.Kind.values]
    return json_success({"notifications": items, "channel": "event-log"})


@require_http_methods(["PUT"])
def notification_update(request, kind):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    if kind not in NotificationPreference.Kind.values:
        return json_error(f"Jenis notifikasi '{kind}' tidak didukung.", status=404)
    data, err = _parse_json_body(request)
    if err:
        return json_error(err, status=400)
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        return json_error("Flag enabled harus boolean.", status=400)
    with transaction.atomic():
        pref = NotificationPreference.objects.filter(kind=kind).first()
        old = _serialize(pref, kind)
        if pref is None:
            pref = NotificationPreference.objects.create(
                kind=kind, enabled=enabled, version=1, updated_by=request.user,
            )
        else:
            pref.enabled = enabled
            pref.version += 1
            pref.updated_by = request.user
            pref.save()
        new = _serialize(pref, kind)
        NotificationAudit.objects.create(
            kind=kind, old_value=old, new_value=new,
            actor=request.user, reason=str(data.get("reason", ""))[:500],
        )
    return json_success({"notification": new, "message": "Konfigurasi tersimpan"})


@require_GET
def notification_events(request):
    """Daftar event terakhir untuk verifikasi pemicu mengikuti preferensi."""
    denied = _require_staff(request)
    if denied is not None:
        return denied
    try:
        limit = min(int(request.GET.get("limit", "20")), 100)
    except ValueError:
        return json_error("Parameter limit tidak valid.", status=400)
    rows = NotificationEvent.objects.order_by("-created_at", "-id")[:limit]
    return json_success({"events": [{
        "kind": r.kind, "sourceId": r.source_id_snapshot or None,
        "notified": r.notified, "message": r.safe_message,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]})
