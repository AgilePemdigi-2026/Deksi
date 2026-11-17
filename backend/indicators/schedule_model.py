"""Feature 23: konfigurasi jadwal pembaruan per sumber."""
from django.conf import settings
from django.db import models


class ScheduleConfig(models.Model):
    source = models.OneToOneField(
        "indicators.Source", on_delete=models.CASCADE, related_name="schedule_config"
    )
    interval_days = models.PositiveIntegerField(default=30)
    run_time = models.TimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    next_run = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_schedule_configs",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "indicators"

    def __str__(self):
        return f"Schedule {self.source_id} v{self.version}"


class ScheduleAudit(models.Model):
    source_id_snapshot = models.CharField(max_length=32)
    old_value = models.JSONField(default=dict)
    new_value = models.JSONField(default=dict)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_schedule_audits",
    )
    reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "indicators"
        ordering = ["-created_at", "-id"]
