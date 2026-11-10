"""Staff-only endpoint for durable, explicitly requested resynchronization."""
import uuid

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from indicators.models import Source
from indicators.resync_model import ResyncJob
from indicators.source_admin_views import _parse_json_body, _require_staff
from indicators.sync_history_model import SyncRun
from indicators.views import json_error


def _job_response(job):
    response = JsonResponse({"id": str(job.pk), "status": job.status}, status=202)
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def resync_status(request, job_id):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    job = ResyncJob.objects.select_related("source", "resolved_by").filter(pk=job_id).first()
    if job is None:
        return json_error("Pekerjaan tidak ditemukan.", status=404)
    response = JsonResponse({
        "id": str(job.pk), "sourceId": job.source.source_id, "status": job.status,
        "requestedAt": job.requested_at.isoformat(),
        "finishedAt": job.finished_at.isoformat() if job.finished_at else None,
        "runId": str(job.run_id) if job.run_id else None, "message": job.safe_message or None,
        "resolvedBy": job.resolved_by.get_username() if job.resolved_by else None,
        "resolvedAt": job.resolved_at.isoformat() if job.resolved_at else None,
        "resolutionReason": job.resolution_reason or None,
    })
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def active_resync(request, source_id):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    if not Source.objects.filter(source_id=source_id).exists():
        return json_error("Sumber tidak ditemukan.", status=404)
    job = ResyncJob.objects.select_related("source").filter(
        source__source_id=source_id, status__in=[ResyncJob.Status.QUEUED, ResyncJob.Status.RUNNING],
    ).first()
    payload = None if job is None else {
        "id": str(job.pk), "sourceId": job.source.source_id, "status": job.status,
        "requestedAt": job.requested_at.isoformat(), "finishedAt": None,
        "runId": str(job.run_id) if job.run_id else None, "message": job.safe_message or None,
    }
    response = JsonResponse({"job": payload})
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def reconcile_resync(request, job_id):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    data, error = _parse_json_body(request)
    if error or set(data) != {"confirmed", "reason"} or data.get("confirmed") is not True:
        return json_error("Konfirmasi pemeriksaan manual wajib diberikan.", status=400)
    reason = data.get("reason")
    if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 500:
        return json_error("Alasan pemeriksaan harus 10-500 karakter.", status=400)
    with transaction.atomic():
        job = ResyncJob.objects.select_for_update().filter(pk=job_id).first()
        if job is None:
            return json_error("Pekerjaan tidak ditemukan.", status=404)
        if job.status != ResyncJob.Status.RUNNING or job.run_id is None:
            return json_error("Hanya pekerjaan dengan hasil belum tercatat dapat diperiksa.", status=409)
        run = SyncRun.objects.select_for_update().get(pk=job.run_id)
        if run.status != SyncRun.Status.RUNNING:
            return json_error("Riwayat pekerjaan telah berubah.", status=409)
        message = "Hasil tidak diketahui; pemeriksaan manual telah dicatat."
        run.status = SyncRun.Status.UNKNOWN
        run.safe_message = message
        run.save(update_fields=["status", "safe_message"])
        job.status = ResyncJob.Status.UNKNOWN
        job.resolved_by = request.user
        job.resolved_at = timezone.now()
        job.resolution_reason = reason.strip()
        job.safe_message = message
        job.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_reason", "safe_message"])
    response = JsonResponse({"id": str(job.pk), "status": job.status})
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def request_resync(request, source_id):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    data, error = _parse_json_body(request)
    if error or set(data) != {"requestId"}:
        return json_error(error or "Permintaan sinkronisasi tidak valid.", status=400)
    try:
        key = uuid.UUID(data["requestId"])
    except (ValueError, AttributeError, TypeError):
        return json_error("Identitas permintaan tidak valid.", status=400)
    try:
        with transaction.atomic():
            source = Source.objects.select_for_update().filter(source_id=source_id).first()
            if source is None:
                return json_error("Sumber tidak ditemukan.", status=404)
            previous = ResyncJob.objects.filter(request_key=key).first()
            if previous:
                if previous.requested_by_id != request.user.pk or previous.source_id != source.pk:
                    return json_error("Identitas permintaan sudah digunakan.", status=409)
                return _job_response(previous)
            if source.source_id != "BPS":
                return json_error("Sinkronisasi ulang untuk sumber ini belum tersedia.", status=400)
            if source.status != Source.SourceStatus.ACTIVE:
                return json_error("Sumber tidak aktif.", status=409)
            if SyncRun.objects.filter(source=source, status=SyncRun.Status.RUNNING).exists():
                return json_error("Sumber masih memiliki sinkronisasi berjalan.", status=409)
            job = ResyncJob.objects.create(source=source, requested_by=request.user, request_key=key)
    except IntegrityError:
        previous = ResyncJob.objects.filter(
            request_key=key, requested_by=request.user, source__source_id=source_id,
        ).first()
        if previous:
            return _job_response(previous)
        return json_error("Sumber sudah memiliki pekerjaan aktif atau identitas permintaan digunakan.", status=409)
    return _job_response(job)
