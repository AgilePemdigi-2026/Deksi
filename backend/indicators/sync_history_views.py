"""Staff-only paginated read API for new SyncRun records (not legacy logs)."""
import re

from django.views.decorators.http import require_GET

from indicators.source_admin_views import _require_staff
from indicators.sync_history_model import SyncRun
from indicators.views import json_error, json_success


def _single(request, key):
    values = request.GET.getlist(key)
    if len(values) > 1:
        raise ValueError
    return values[0] if values else None


@require_GET
def admin_sync_history(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    try:
        if set(request.GET) - {"page", "pageSize", "sourceId", "status"}:
            raise ValueError
        page_raw = _single(request, "page")
        size_raw = _single(request, "pageSize")
        source_id = _single(request, "sourceId")
        status = _single(request, "status")
        page = int(page_raw or "1")
        page_size = int(size_raw or "20")
        if page < 1 or page > 1000000 or page_size < 1 or page_size > 100:
            raise ValueError
        if not re.fullmatch(r"[0-9]+", page_raw or "1") or not re.fullmatch(r"[0-9]+", size_raw or "20"):
            raise ValueError
        if source_id is not None and (not source_id or len(source_id) > 32):
            raise ValueError
        if status is not None and status not in SyncRun.Status.values:
            raise ValueError
    except (ValueError, TypeError):
        return json_error("Parameter riwayat sinkronisasi tidak valid.", status=400)

    qs = SyncRun.objects.select_related("actor", "resyncjob__resolved_by").all()
    if source_id is not None:
        qs = qs.filter(source_id_snapshot=source_id)
    if status is not None:
        qs = qs.filter(status=status)
    qs = qs.order_by("-started_at", "-id")
    total = qs.count()
    rows = qs[(page - 1) * page_size:page * page_size]
    items = []
    for row in rows:
        job = getattr(row, "resyncjob", None)
        items.append({
            "id": str(row.pk),
            "sourceId": row.source_id_snapshot or None,
            "sourceName": row.source_name_snapshot or None,
            "status": row.status,
            "startedAt": row.started_at.isoformat() if row.started_at else None,
            "finishedAt": row.finished_at.isoformat() if row.finished_at else None,
            "actor": row.actor.get_username() if row.actor else None,
            "itemCount": row.item_count,
            "message": row.safe_message,
            "resyncJobId": str(job.pk) if job else None,
            "resolvedBy": job.resolved_by.get_username() if job and job.resolved_by else None,
            "resolvedAt": job.resolved_at.isoformat() if job and job.resolved_at else None,
            "resolutionReason": job.resolution_reason or None if job else None,
        })
    return json_success({
        "items": items,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "hasNext": page * page_size < total,
        },
    })
