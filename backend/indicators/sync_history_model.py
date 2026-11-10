"""Standalone sync-run history model; import from models.py during integration."""
from typing import ClassVar

from django.conf import settings
from django.db import models


class SyncRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        "indicators.Source", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sync_runs",
    )
    source_id_snapshot = models.CharField(max_length=32, blank=True, default="")
    source_name_snapshot = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.RUNNING, db_index=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_sync_runs",
    )
    item_count = models.PositiveIntegerField(null=True, blank=True)
    safe_message = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        app_label = "indicators"
        ordering: ClassVar = ["-started_at", "-id"]
        indexes: ClassVar = [models.Index(fields=["-started_at", "-id"], name="sync_run_started_idx")]

    def __str__(self):
        return f"SyncRun {self.pk}: {self.status}"
