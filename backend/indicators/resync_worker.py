"""One-at-a-time worker for explicitly queued BPS resynchronizations."""
from contextlib import contextmanager

from django.db import transaction
from django.utils import timezone

from indicators import bps
from indicators.models import Source
from indicators.resync_model import ResyncJob
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import create_sync_run, finalize_sync_run

# Hanya api_bps yang dapat dijalankan end-to-end.
# Jangan antrekan/eksekusi metode lain agar tidak menghasilkan riwayat gagal palsu.
RESYNCABLE_METHODS = frozenset({"api_bps"})


def _resync_method(source) -> str:
    method = (getattr(source, "acquisition_method", "") or "").strip()
    if not method and getattr(source, "source_id", "") == "BPS":
        return "api_bps"
    return method


class JobFencedError(Exception):
    pass


@contextmanager
def _job_write_guard(job_id, run_id):
    with transaction.atomic():
        job = ResyncJob.objects.select_for_update().get(pk=job_id)
        if job.status != ResyncJob.Status.RUNNING or job.run_id != run_id:
            raise JobFencedError
        yield


def claim_next_job():
    candidates = list(ResyncJob.objects.filter(status=ResyncJob.Status.QUEUED)
                      .order_by("requested_at", "pk").values_list("pk", "source_id")[:100])
    for job_id, source_pk in candidates:
        with transaction.atomic():
            source = Source.objects.select_for_update().get(pk=source_pk)
            job = ResyncJob.objects.select_for_update().get(pk=job_id)
            if job.status != ResyncJob.Status.QUEUED:
                continue
            if source.status != Source.SourceStatus.ACTIVE:
                job.status = ResyncJob.Status.CANCELLED
                job.finished_at = timezone.now()
                job.safe_message = "Sumber tidak aktif; sinkronisasi tidak dimulai."
                job.save(update_fields=["status", "finished_at", "safe_message"])
                return job
            _method = _resync_method(source)
            if _method not in RESYNCABLE_METHODS:
                job.status = ResyncJob.Status.CANCELLED
                job.finished_at = timezone.now()
                job.safe_message = "Sumber belum didukung; sinkronisasi tidak dimulai."
                job.save(update_fields=["status", "finished_at", "safe_message"])
                return job
            if SyncRun.objects.filter(source=source, status=SyncRun.Status.RUNNING).exists():
                continue
            run = create_sync_run(source=source, actor=job.requested_by)
            job.run = run
            job.status = ResyncJob.Status.RUNNING
            job.save(update_fields=["run", "status"])
            return job
    return None


def process_one():
    job = claim_next_job()
    if job is None or job.status != ResyncJob.Status.RUNNING:
        return job
    try:
        with _job_write_guard(job.pk, job.run_id):
            locked_src = Source.objects.get(pk=job.source_id)
            method = _resync_method(locked_src)
            if method != "api_bps":
                raise ValueError("Metode sumber tidak lagi didukung untuk resync.")
            source = bps._get_or_create_source()
            if source.pk != job.source_id:
                raise ValueError("Identitas sumber berubah.")
        result = bps._sync_bps_started(
            source, start_year=2016, end_year=None,
            write_guard=lambda: _job_write_guard(job.pk, job.run_id),
        )
        has_errors = bool(result["errors"])
        stage = "fetch_series" if has_errors else None
    except JobFencedError:
        return ResyncJob.objects.get(pk=job.pk)
    except ValueError:
        # Konfigurasi berubah setelah claim: batalkan tanpa riwayat gagal palsu.
        with transaction.atomic():
            locked = ResyncJob.objects.select_for_update().get(pk=job.pk)
            if locked.status != ResyncJob.Status.RUNNING or locked.run_id != job.run_id:
                return locked
            run = SyncRun.objects.select_for_update().get(pk=locked.run_id)
            if run.status == SyncRun.Status.RUNNING:
                run.status = SyncRun.Status.UNKNOWN
                run.finished_at = timezone.now()
                run.safe_message = "Metode sumber berubah; sinkronisasi dibatalkan."
                run.save(update_fields=["status", "finished_at", "safe_message"])
            locked.status = ResyncJob.Status.CANCELLED
            locked.finished_at = timezone.now()
            locked.safe_message = "Metode sumber berubah; sinkronisasi dibatalkan."
            locked.save(update_fields=["status", "finished_at", "safe_message"])
        return locked
    except Exception:
        has_errors = True
        stage = None
    with transaction.atomic():
        locked = ResyncJob.objects.select_for_update().get(pk=job.pk)
        if locked.status != ResyncJob.Status.RUNNING or locked.run_id != job.run_id:
            return locked
        run = finalize_sync_run(locked.run, success=not has_errors, failure_stage=stage)
        locked.status = ResyncJob.Status.FAILED if has_errors else ResyncJob.Status.SUCCESS
        locked.finished_at = run.finished_at
        locked.safe_message = run.safe_message or ""
        locked.save(update_fields=["status", "finished_at", "safe_message"])
    return locked
