"""Persistent requests for a single, explicitly selected data source."""
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q


class ResyncJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Menunggu"
        RUNNING = "running", "Berlangsung"
        SUCCESS = "success", "Berhasil"
        FAILED = "failed", "Gagal"
        CANCELLED = "cancelled", "Tidak dimulai"
        UNKNOWN = "unknown", "Hasil tidak diketahui"

    request_key = models.UUIDField(unique=True)
    source = models.ForeignKey("indicators.Source", on_delete=models.PROTECT, related_name="resync_jobs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED)
    run = models.OneToOneField("indicators.SyncRun", on_delete=models.PROTECT, null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    safe_message = models.CharField(max_length=500, blank=True, default="")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="resolved_resync_jobs")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_reason = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        constraints: ClassVar = [models.UniqueConstraint(
            fields=["source"], condition=Q(status__in=["queued", "running"]), name="resync_one_active_source",
        )]
