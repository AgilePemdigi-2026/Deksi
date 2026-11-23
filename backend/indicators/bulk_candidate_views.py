"""Persistent, reviewer-bound bulk candidate previews and review results."""
from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from indicators.candidate_views import _authorize, _serialize
from indicators.lifecycle import review_candidate
from indicators.models import (
    BulkCandidateReview,
    BulkCandidateReviewItem,
    ObservationCandidate,
    RawFile,
    Source,
)
from indicators.source_admin_views import _parse_json_body
from indicators.storage import verified_raw_bytes
from indicators.views import json_error

MAX_PREVIEW_ITEMS = 500
PREVIEW_TTL = timedelta(minutes=15)


def _eligibility(candidate):
    payload = candidate.payload if isinstance(candidate.payload, dict) else {}
    raw_id = payload.get("raw_file_id")
    if not isinstance(raw_id, int) or isinstance(raw_id, bool) or raw_id <= 0:
        return False, "missing_raw_file"
    if candidate.source.source_id == "BPS":
        observation_date = payload.get("observation_date")
        if not isinstance(observation_date, str):
            return False, "invalid_observation_date"
        try:
            date.fromisoformat(observation_date)
        except ValueError:
            return False, "invalid_observation_date"
        if not isinstance(payload.get("period_label"), str) or not payload["period_label"].strip():
            return False, "missing_period_label"
    publication_date = payload.get("publication_date")
    if publication_date is None and candidate.source.source_id in ("BPS", "BKPM", "BI"):
        pass  # BPS, BKPM, BI observations may lack an independently established release date.
    elif not isinstance(publication_date, str):
        return False, "missing_publication_date"
    else:
        try:
            date.fromisoformat(publication_date)
        except ValueError:
            return False, "invalid_publication_date"
    snapshot = candidate.base_snapshot if isinstance(candidate.base_snapshot, dict) else {}
    raw = snapshot.get("candidate_raw")
    if not isinstance(raw, dict) or raw.get("id") != raw_id or raw.get("source_id") != candidate.source_id:
        return False, "raw_snapshot_source_mismatch"
    if candidate.source.source_id == "BPS":
        raw_file = RawFile.objects.filter(pk=raw_id, source_id=candidate.source_id).first()
        if raw_file is None:
            return False, "raw_file_unavailable"
        if (raw.get("checksum_sha256") != raw_file.checksum_sha256
                or raw.get("file_size_bytes") != raw_file.file_size_bytes):
            return False, "raw_file_invalid"
        try:
            verified_raw_bytes(raw_file)
        except OSError:
            return False, "raw_file_unavailable"
        except ValueError:
            return False, "raw_file_invalid"
    return True, None


def _counts(batch):
    grouped = {
        row["status"]: row["count"]
        for row in batch.items.values("status").order_by().annotate(count=Count("id"))
    }
    total = sum(grouped.values())
    eligible = batch.items.filter(eligible=True).count()
    excluded = grouped.get(BulkCandidateReviewItem.Status.EXCLUDED, 0)
    published = grouped.get(BulkCandidateReviewItem.Status.PUBLISHED, 0)
    skipped = grouped.get(BulkCandidateReviewItem.Status.SKIPPED, 0)
    unknown = grouped.get(BulkCandidateReviewItem.Status.UNKNOWN, 0)
    pending = grouped.get(BulkCandidateReviewItem.Status.PENDING, 0)
    return {"total": total, "eligible": eligible, "excluded": excluded, "published": published,
            "skipped": skipped, "pending": pending, "unknown": unknown}


def _result(batch):
    return {
        "id": str(batch.pk),
        "status": batch.status,
        "resolvedAt": batch.resolved_at.isoformat() if batch.resolved_at else None,
        "resolvedBy": batch.resolved_by.get_username() if batch.resolved_by_id else None,
        "resolutionReason": batch.resolution_reason or None,
        "items": [{"id": item.candidate_id, "status": item.status,
                   "reason": item.reason or item.exclusion_reason}
                  for item in batch.items.order_by("candidate_id")],
        "counts": _counts(batch),
    }


def _no_store(response):
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def bulk_candidate_preview(request, source_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    data, error = _parse_json_body(request)
    if error or data is None or data != {}:
        return json_error("Permintaan preview tidak valid.", status=400)
    try:
        reviewer = request.user
        with transaction.atomic():
            source = Source.objects.filter(source_id=source_id).first()
            if source is None:
                return json_error("Sumber tidak ditemukan.", status=404)
            # Chunked snapshot: freeze the oldest MAX pending rows per batch.
            # Later batches pick up the remainder; rows arriving after this
            # snapshot are never added silently.
            pending_qs = (ObservationCandidate.objects.filter(source=source, status="pending")
                          .select_related("indicator", "source", "reviewed_by")
                          .order_by("pk"))
            total_pending = pending_qs.count()
            candidates = list(pending_qs[:MAX_PREVIEW_ITEMS])
            batch = BulkCandidateReview.objects.create(
                source=source, reviewer=reviewer, expires_at=timezone.now() + PREVIEW_TTL,
            )
            rows, items = [], []
            for candidate in candidates:
                eligible, reason = _eligibility(candidate)
                serialized = _serialize(candidate)
                rows.append(BulkCandidateReviewItem(
                    batch=batch, candidate=candidate, candidate_snapshot=serialized,
                    eligible=eligible, exclusion_reason=reason,
                    status=(BulkCandidateReviewItem.Status.PENDING if eligible
                            else BulkCandidateReviewItem.Status.EXCLUDED),
                    reason=reason,
                ))
                items.append({**serialized, "eligible": eligible, "exclusionReason": reason})
            BulkCandidateReviewItem.objects.bulk_create(rows)
        eligible_count = sum(1 for item in items if item["eligible"])
        return _no_store(JsonResponse({
            "id": str(batch.pk), "status": "preview", "expiresAt": batch.expires_at.isoformat(),
            "total": len(items), "eligible": eligible_count, "excluded": len(items) - eligible_count,
            "totalPending": total_pending, "hasMore": total_pending > len(items),
            "items": items,
        }))
    except PermissionDenied:
        return json_error("Izin review kandidat diperlukan.", status=403)


@require_POST
def bulk_candidate_confirm(request, source_id, batch_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    data, error = _parse_json_body(request)
    if (error or not isinstance(data, dict) or set(data) != {"confirmed"}
            or data["confirmed"] is not True):
        return json_error("Konfirmasi tidak valid.", status=400)
    try:
        with transaction.atomic():
            # Serialize confirmations for this source; the per-item work stays outside this lock.
            source = Source.objects.select_for_update().filter(source_id=source_id).first()
            if source is None:
                return json_error("Sumber tidak ditemukan.", status=404)
            batch = BulkCandidateReview.objects.select_for_update().filter(
                pk=batch_id, source=source, reviewer_id=request.user.pk).first()
            if batch is None:
                return json_error("Preview tidak ditemukan.", status=404)
            if batch.status != BulkCandidateReview.Status.PREVIEW:
                return _no_store(JsonResponse(_result(batch)))
            if BulkCandidateReview.objects.filter(
                    source=source, status__in=[BulkCandidateReview.Status.RUNNING,
                                               BulkCandidateReview.Status.UNKNOWN],
                    resolved_at__isnull=True).exclude(pk=batch.pk).exists():
                return json_error("Ada operasi sumber ini yang belum pasti; periksa hasilnya sebelum konfirmasi baru.",
                                  status=409)
            if batch.expires_at <= timezone.now():
                return json_error("Preview kedaluwarsa; buat preview baru.", status=409)
            batch.status = BulkCandidateReview.Status.RUNNING
            batch.confirmed_at = timezone.now()
            batch.save(update_fields=["status", "confirmed_at"])
    except (ValueError, TypeError):
        return json_error("Preview tidak ditemukan.", status=404)

    for item_id in list(BulkCandidateReviewItem.objects.filter(batch_id=batch_id, eligible=True)
                        .order_by("candidate_id").values_list("pk", flat=True)):
        try:
            with transaction.atomic():
                # A manual resolution fences this request's remaining writes.
                current_batch = BulkCandidateReview.objects.select_for_update().get(pk=batch_id)
                if current_batch.resolved_at is not None:
                    break
                item = BulkCandidateReviewItem.objects.select_for_update().get(
                    pk=item_id, batch_id=batch_id, status=BulkCandidateReviewItem.Status.PENDING)
                candidate = ObservationCandidate.objects.select_for_update().get(pk=item.candidate_id)
                # The individual lifecycle checks internal integrity, not the fingerprint shown in preview.
                if candidate.fingerprint != item.candidate_snapshot["fingerprint"]:
                    raise ValidationError("Kandidat berubah setelah preview.")
                eligible, reason = _eligibility(candidate)
                if not eligible:
                    item.status = BulkCandidateReviewItem.Status.SKIPPED
                    item.reason = reason
                    item.save(update_fields=["status", "reason"])
                    continue
                review_candidate(item.candidate_id, request.user, publish=True)
                item.status = BulkCandidateReviewItem.Status.PUBLISHED
                item.reason = None
                item.save(update_fields=["status", "reason"])
        except ValidationError:
            BulkCandidateReviewItem.objects.filter(pk=item_id, status=BulkCandidateReviewItem.Status.PENDING).update(
                status=BulkCandidateReviewItem.Status.SKIPPED, reason="candidate_changed_or_review_failed")
        except Exception:
            # The current item's transaction rolled back. Its outcome is deliberately uncertain;
            # readback never retries this or any other item.
            BulkCandidateReviewItem.objects.filter(pk=item_id, status=BulkCandidateReviewItem.Status.PENDING).update(
                status=BulkCandidateReviewItem.Status.UNKNOWN, reason="review_outcome_unknown")
            BulkCandidateReview.objects.filter(pk=batch_id, resolved_at__isnull=True).update(
                status=BulkCandidateReview.Status.UNKNOWN)
            break

    BulkCandidateReview.objects.filter(pk=batch_id, status=BulkCandidateReview.Status.RUNNING,
                                       resolved_at__isnull=True).update(
        status=BulkCandidateReview.Status.COMPLETED)
    batch = BulkCandidateReview.objects.get(pk=batch_id)
    return _no_store(JsonResponse(_result(batch)))

@require_POST
def bulk_candidate_reconcile(request, source_id, batch_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    data, error = _parse_json_body(request)
    if (error or not isinstance(data, dict) or set(data) != {"acknowledged", "reason"}
            or data["acknowledged"] is not True or not isinstance(data["reason"], str)
            or not 1 <= len(data["reason"].strip()) <= 500):
        return json_error("Alasan dan konfirmasi pemeriksaan manual diperlukan.", status=400)
    with transaction.atomic():
        batches = BulkCandidateReview.objects.select_for_update().filter(
            pk=batch_id, source__source_id=source_id)
        if not request.user.is_superuser:
            batches = batches.filter(reviewer_id=request.user.pk)
        batch = batches.first()
        if batch is None:
            return json_error("Review bulk tidak ditemukan.", status=404)
        if batch.status == BulkCandidateReview.Status.PREVIEW and batch.reviewer_id != request.user.pk:
            return json_error("Review bulk tidak ditemukan.", status=404)
        if batch.resolved_at is not None:
            return _no_store(JsonResponse(_result(batch)))
        if batch.status not in {BulkCandidateReview.Status.RUNNING, BulkCandidateReview.Status.UNKNOWN}:
            return json_error("Hanya operasi belum pasti yang dapat ditutup.", status=409)
        batch.items.filter(status=BulkCandidateReviewItem.Status.PENDING).update(
            status=BulkCandidateReviewItem.Status.UNKNOWN, reason="manual_reconciliation")
        batch.status = BulkCandidateReview.Status.UNKNOWN
        batch.resolved_at = timezone.now()
        batch.resolved_by = request.user
        batch.resolution_reason = data["reason"].strip()
        batch.save(update_fields=["status", "resolved_at", "resolved_by", "resolution_reason"])
    return _no_store(JsonResponse(_result(batch)))


@require_GET
def bulk_candidate_status(request, source_id, batch_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    batches = BulkCandidateReview.objects.filter(pk=batch_id, source__source_id=source_id)
    if not request.user.is_superuser:
        batches = batches.filter(reviewer_id=request.user.pk)
    batch = batches.first()
    if batch is None:
        return json_error("Review bulk tidak ditemukan.", status=404)
    if batch.status == BulkCandidateReview.Status.PREVIEW and batch.reviewer_id != request.user.pk:
        return json_error("Review bulk tidak ditemukan.", status=404)
    if batch.status == BulkCandidateReview.Status.PREVIEW:
        return json_error("Preview belum dikonfirmasi.", status=409)
    if batch.status not in {BulkCandidateReview.Status.RUNNING, BulkCandidateReview.Status.COMPLETED,
                            BulkCandidateReview.Status.UNKNOWN}:
        return json_error("Status review bulk tidak valid.", status=409)
    return _no_store(JsonResponse(_result(batch)))


@require_GET
def bulk_candidate_active(request, source_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    unresolved = BulkCandidateReview.objects.filter(
        source__source_id=source_id, resolved_at__isnull=True,
        status__in=[BulkCandidateReview.Status.RUNNING, BulkCandidateReview.Status.UNKNOWN])
    if request.user.is_superuser:
        batch = unresolved.first()
    else:
        batch = unresolved.filter(reviewer_id=request.user.pk).first()
    if batch is None:
        history = BulkCandidateReview.objects.filter(
            source__source_id=source_id,
            status__in=[BulkCandidateReview.Status.RUNNING, BulkCandidateReview.Status.UNKNOWN,
                       BulkCandidateReview.Status.COMPLETED])
        if request.user.is_superuser:
            history = history.filter(Q(reviewer_id=request.user.pk) | Q(resolved_by_id=request.user.pk))
        else:
            history = history.filter(reviewer_id=request.user.pk)
        batch = history.first()
    return _no_store(JsonResponse({"batch": _result(batch) if batch is not None else None}))
