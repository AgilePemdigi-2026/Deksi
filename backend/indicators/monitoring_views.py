"""Feature 19: Dashboard Monitoring Admin (read-only, staff only).

Sumber kebenaran: Source, SyncRun, ResyncJob, Observation, DataUpdateLog.
Tidak membuat status buatan; tidak menghapus data valid terakhir.
"""
from django.db.models import Count, Max
from django.views.decorators.http import require_GET

from indicators.models import DataUpdateLog, Observation, Source
from indicators.resync_model import ResyncJob
from indicators.source_admin_views import _require_staff
from indicators.sync_history_model import SyncRun
from indicators.views import json_error, json_success


def _quality_status():
    """Ringkasan kualitas dari observasi validated/published vs total."""
    total = Observation.objects.count()
    validated = Observation.objects.filter(
        validation_status__in=[Observation.Status.VALIDATED, Observation.Status.PUBLISHED]
    ).count()
    if total == 0:
        return {"label": "Belum ada data", "validated": 0, "total": 0}
    label = "Baik" if validated == total else "Perlu perhatian" if validated * 2 >= total else "Buruk"
    return {"label": label, "validated": validated, "total": total}


@require_GET
def admin_monitoring_summary(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    total_sources = Source.objects.count()
    active_sources = Source.objects.filter(status=Source.SourceStatus.ACTIVE).count()
    inactive_sources = total_sources - active_sources

    sync_counts = dict(
        SyncRun.objects.values_list("status").annotate(c=Count("id")).values_list("status", "c")
    )
    success = sync_counts.get(SyncRun.Status.SUCCESS, 0)
    failed = sync_counts.get(SyncRun.Status.FAILED, 0)
    running = sync_counts.get(SyncRun.Status.RUNNING, 0)

    last_run = SyncRun.objects.order_by("-started_at").first()
    last_update = DataUpdateLog.objects.order_by("-updated_at").first()

    return json_success({
        "totalSources": total_sources,
        "activeSources": active_sources,
        "inactiveSources": inactive_sources,
        "syncSuccess": success,
        "syncFailed": failed,
        "syncRunning": running,
        "quality": _quality_status(),
        "lastSyncAt": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
        "lastUpdateAt": last_update.updated_at.isoformat() if last_update and last_update.updated_at else None,
    })


@require_GET
def admin_monitoring_sources(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    # Status sinkronisasi terakhir per sumber dari SyncRun terbaru.
    latest_runs = (
        SyncRun.objects.order_by("source_id", "-started_at")
        .values("source_id", "status", "started_at", "finished_at", "safe_message")
    )
    latest_by_source = {}
    for row in latest_runs:
        if row["source_id"] not in latest_by_source:
            latest_by_source[row["source_id"]] = row

    last_obs = (
        Observation.objects.values("source_id")
        .annotate(last_period=Max("period_label"), last_date=Max("observation_date"), count=Count("id"))
    )
    obs_by_source = {r["source_id"]: r for r in last_obs}

    items = []
    for s in Source.objects.order_by("source_id"):
        run = latest_by_source.get(s.pk)
        obs = obs_by_source.get(s.pk, {})
        items.append({
            "sourceId": s.source_id,
            "sourceName": s.source_name,
            "institution": s.institution,
            "status": s.status,
            "active": s.status == Source.SourceStatus.ACTIVE,
            "lastSyncStatus": run["status"] if run else None,
            "lastSyncAt": run["started_at"].isoformat() if run and run["started_at"] else None,
            "lastSyncMessage": (run["safe_message"] or "") if run else "",
            "lastPeriod": obs.get("last_period"),
            "lastObservationDate": obs.get("last_date").isoformat() if obs.get("last_date") else None,
            "observationCount": obs.get("count", 0),
            "updateSchedule": s.update_schedule or "",
        })
    return json_success({"sources": items})


@require_GET
def admin_monitoring_run_detail(request, run_id):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    try:
        run = SyncRun.objects.select_related("actor", "source").get(pk=run_id)
    except (SyncRun.DoesNotExist, ValueError):
        return json_error("Riwayat proses tidak ditemukan.", status=404)
    job = getattr(run, "resyncjob", None)
    duration = None
    if run.started_at and run.finished_at:
        duration = (run.finished_at - run.started_at).total_seconds()
    return json_success({
        "id": str(run.pk),
        "sourceId": run.source_id_snapshot or (run.source.source_id if run.source else None),
        "sourceName": run.source_name_snapshot or (run.source.source_name if run.source else None),
        "status": run.status,
        "startedAt": run.started_at.isoformat() if run.started_at else None,
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        "durationSeconds": duration,
        "actor": run.actor.get_username() if run.actor else None,
        "itemCount": run.item_count,
        "message": run.safe_message or "",
        "resyncJobId": str(job.pk) if job else None,
        "stages": ["akuisisi", "validasi", "pemrosesan"],
    })


@require_GET
def admin_monitoring_history(request):
    """Riwayat pemrosesan: delegasi ke SyncRun terbaru (filter ringan)."""
    denied = _require_staff(request)
    if denied is not None:
        return denied
    try:
        page = int(request.GET.get("page", "1"))
        page_size = int(request.GET.get("pageSize", "20"))
        if page < 1 or page_size < 1 or page_size > 100:
            raise ValueError
    except ValueError:
        return json_error("Parameter pagination tidak valid.", status=400)
    status_filter = request.GET.get("status")
    source_filter = request.GET.get("sourceId")
    qs = SyncRun.objects.select_related("actor").order_by("-started_at", "-id")
    if status_filter in SyncRun.Status.values:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source_id_snapshot=source_filter)
    total = qs.count()
    rows = qs[(page - 1) * page_size:page * page_size]
    items = [{
        "id": str(r.pk),
        "sourceId": r.source_id_snapshot or None,
        "sourceName": r.source_name_snapshot or None,
        "status": r.status,
        "startedAt": r.started_at.isoformat() if r.started_at else None,
        "finishedAt": r.finished_at.isoformat() if r.finished_at else None,
        "actor": r.actor.get_username() if r.actor else None,
        "itemCount": r.item_count,
        "message": r.safe_message or "",
    } for r in rows]
    return json_success({"items": items, "page": page, "pageSize": page_size, "total": total})
