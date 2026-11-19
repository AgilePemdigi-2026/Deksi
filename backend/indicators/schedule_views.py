"""Feature 23: API konfigurasi jadwal pembaruan (staff only)."""
import json
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from indicators.models import Source
from indicators.schedule_model import ScheduleAudit, ScheduleConfig
from indicators.source_admin_views import _parse_json_body, _require_staff
from indicators.views import json_error, json_success

ALLOWED_INTERVAL_DAYS = (1, 365)
DEFAULT_SCHEDULE_TEXT = {
    "BPS": "Mengikuti jadwal rilis WebAPI BPS",
    "KEMENKEU": "Mengikuti edisi APBN KiTa",
    "BI": "Mengikuti dataset BI (harian/event)",
    "BKPM": "Triwulanan PMA/PMDN",
}


def _serialize(cfg: ScheduleConfig | None, source: Source) -> dict:
    return {
        "sourceId": source.source_id,
        "sourceName": source.source_name,
        "institution": source.institution,
        "intervalDays": cfg.interval_days if cfg else 30,
        "runTime": cfg.run_time.strftime("%H:%M") if cfg and cfg.run_time else None,
        "enabled": cfg.enabled if cfg else True,
        "nextRun": cfg.next_run.isoformat() if cfg and cfg.next_run else None,
        "version": cfg.version if cfg else 0,
        "configured": bool(cfg),
        "currentScheduleText": source.update_schedule or DEFAULT_SCHEDULE_TEXT.get(source.source_id, ""),
        "updatedAt": cfg.updated_at.isoformat() if cfg else None,
    }


def _compute_next_run(interval_days: int) -> timezone.datetime:
    return timezone.now() + timedelta(days=interval_days)


@require_GET
def schedule_list(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    items = []
    for s in Source.objects.exclude(status=Source.SourceStatus.ARCHIVED).order_by("source_id"):
        cfg = getattr(s, "schedule_config", None)
        # OneToOne reverse raises DoesNotExist bila belum ada; normalisasi ke None.
        if cfg is not None and not isinstance(cfg, ScheduleConfig):
            cfg = None
        try:
            cfg = s.schedule_config
        except ScheduleConfig.DoesNotExist:
            cfg = None
        items.append(_serialize(cfg, s))
    return json_success({"schedules": items})


@require_http_methods(["PUT"])
def schedule_update(request, source_id):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    try:
        source = Source.objects.get(source_id=source_id)
    except Source.DoesNotExist:
        return json_error(f"Sumber '{source_id}' tidak tersedia.", status=404)
    data, err = _parse_json_body(request)
    if err:
        return json_error(err, status=400)
    try:
        interval = int(data.get("intervalDays"))
    except (TypeError, ValueError):
        return json_error("Interval tidak valid.", status=400)
    if not (ALLOWED_INTERVAL_DAYS[0] <= interval <= ALLOWED_INTERVAL_DAYS[1]):
        return json_error("Interval harus 1–365 hari.", status=400)
    run_time_raw = (data.get("runTime") or "").strip() if data.get("runTime") is not None else ""
    run_time = None
    if run_time_raw:
        try:
            run_time = datetime.strptime(run_time_raw, "%H:%M").time()
        except ValueError:
            return json_error("Format waktu harus HH:MM.", status=400)
    enabled = data.get("enabled", True)
    if not isinstance(enabled, bool):
        return json_error("Flag enabled harus boolean.", status=400)
    if source.status != Source.SourceStatus.ACTIVE:
        return json_error("Hanya sumber aktif yang dapat dijadwalkan.", status=400)

    with transaction.atomic():
        try:
            cfg = source.schedule_config
        except ScheduleConfig.DoesNotExist:
            cfg = None
        old = _serialize(cfg, source)
        next_run = _compute_next_run(interval)
        if cfg is None:
            cfg = ScheduleConfig.objects.create(
                source=source, interval_days=interval, run_time=run_time,
                enabled=enabled, next_run=next_run, version=1, updated_by=request.user,
            )
        else:
            cfg.interval_days = interval
            cfg.run_time = run_time
            cfg.enabled = enabled
            cfg.next_run = next_run
            cfg.version += 1
            cfg.updated_by = request.user
            cfg.save()
        # Sinkronkan teks jadwal di Source agar halaman publik konsisten.
        source.update_schedule = (
            f"Setiap {interval} hari" + (f" pukul {run_time_raw}" if run_time_raw else "")
            + (" (nonaktif)" if not enabled else "")
        )
        source.save(update_fields=["update_schedule"])
        new = _serialize(cfg, source)
        ScheduleAudit.objects.create(
            source_id_snapshot=source.source_id, old_value=old, new_value=new,
            actor=request.user, reason=str(data.get("reason", ""))[:500],
        )
    return json_success({"schedule": new, "message": "Konfigurasi tersimpan"})


@require_GET
def schedule_next(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    cfgs = ScheduleConfig.objects.filter(enabled=True, source__status=Source.SourceStatus.ACTIVE).select_related("source").order_by("next_run")
    items = [{
        "sourceId": c.source.source_id,
        "nextRun": c.next_run.isoformat() if c.next_run else None,
    } for c in cfgs]
    return json_success({"upcoming": items})
