"""Persistence helpers for the independent synchronization history."""

from django.db import transaction
from django.utils import timezone

from indicators.models import Source
from indicators.source_status import ActiveSyncError, InactiveSourceError
from indicators.sync_history_model import SyncRun


def begin_sync_run(*, source: Source, actor=None, started_at=None) -> SyncRun:
    """Atomically check the current source state and register a run, then release locks."""
    with transaction.atomic():
        locked_source = Source.objects.select_for_update().get(pk=source.pk)
        if locked_source.status != Source.SourceStatus.ACTIVE:
            raise InactiveSourceError(
                f"Sumber {locked_source.source_id} tidak aktif; akuisisi dibatalkan."
            )
        from indicators.resync_model import ResyncJob

        if (SyncRun.objects.filter(source=locked_source, status=SyncRun.Status.RUNNING).exists()
                or ResyncJob.objects.filter(source=locked_source, status__in=["queued", "running"]).exists()):
            raise ActiveSyncError("Sumber memiliki sinkronisasi atau antrean aktif.")
        return create_sync_run(source=locked_source, actor=actor, started_at=started_at)

# Only deliberately bounded, generic operator-facing messages are persisted.
_SAFE_MESSAGES = {
    "success": "Sinkronisasi selesai.",
    "failed": "Sinkronisasi gagal. Periksa log operasional.",
}
_SAFE_FAILURE_STAGES = {
    "fetch_series": "Pengambilan data gagal pada satu atau lebih seri. Penyebab rinci tidak tersedia.",
    "fetch_document": "Pengambilan atau pembacaan dokumen gagal. Penyebab rinci tidak tersedia.",
    "read_file": "Pembacaan berkas gagal. Penyebab rinci tidak tersedia.",
    "store_file": "Penyimpanan berkas gagal. Penyebab rinci tidak tersedia.",
    "process_data": "Pemrosesan data gagal. Penyebab rinci tidak tersedia.",
    "multiple_stages": "Beberapa tahap pemrosesan gagal. Penyebab rinci tidak tersedia.",
}


def create_sync_run(*, source=None, actor=None, started_at=None) -> SyncRun:
    """Create a running record in a short atomic block; actor may be unknown."""
    return SyncRun.objects.create(
        source=source,
        source_id_snapshot=source.source_id if source else "",
        source_name_snapshot=source.source_name if source else "",
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        started_at=started_at or timezone.now(),
        status=SyncRun.Status.RUNNING,
        item_count=None,
        safe_message=None,
    )


def finalize_sync_run(run_or_id, *, success: bool, item_count=None, finished_at=None, failure_stage=None) -> SyncRun:
    """Finalize once, rejecting invalid counts and never persisting exception text."""
    if item_count is not None and (isinstance(item_count, bool) or not isinstance(item_count, int) or item_count < 0):
        raise ValueError("item_count harus integer non-negatif atau None.")
    run_id = run_or_id.pk if isinstance(run_or_id, SyncRun) else run_or_id
    with transaction.atomic():
        run = SyncRun.objects.select_for_update().get(pk=run_id)
        if run.status != SyncRun.Status.RUNNING:
            raise ValueError("SyncRun sudah difinalisasi.")
        run.status = SyncRun.Status.SUCCESS if success else SyncRun.Status.FAILED
        run.finished_at = finished_at or timezone.now()
        run.item_count = item_count
        run.safe_message = _SAFE_MESSAGES[run.status]
        if not success and failure_stage in _SAFE_FAILURE_STAGES:
            run.safe_message = _SAFE_FAILURE_STAGES[failure_stage]
        run.save(update_fields=["status", "finished_at", "item_count", "safe_message"])
    return run
