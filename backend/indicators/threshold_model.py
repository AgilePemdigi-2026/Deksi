"""Feature 24: model konfigurasi threshold diagnostik + audit.

Pemisahan tegas:
- Nilai ekonomi resmi dan hasil Economic Engine tersimpan di Observation.
- Model di sini hanya menyimpan parameter ambang diagnostik yang configurable.
- Perubahan threshold tidak pernah menulis ulang Observation.
"""
from django.conf import settings
from django.db import models


class DiagnosticThreshold(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        INACTIVE = "inactive", "Nonaktif"

    indicator_code = models.CharField(max_length=32, db_index=True)
    param_key = models.CharField(max_length=64, db_index=True)
    value = models.DecimalField(max_digits=24, decimal_places=6)
    unit = models.CharField(max_length=50)
    min_allowed = models.DecimalField(max_digits=24, decimal_places=6)
    max_allowed = models.DecimalField(max_digits=24, decimal_places=6)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_threshold_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "indicators"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["indicator_code", "param_key"], name="threshold_indicator_param_once"),
        ]
        ordering = ["indicator_code", "param_key"]  # noqa: RUF012

    def __str__(self):
        return f"Threshold {self.indicator_code}/{self.param_key} = {self.value} {self.unit} (v{self.version})"


class DiagnosticThresholdAudit(models.Model):
    indicator_code = models.CharField(max_length=32, db_index=True)
    param_key = models.CharField(max_length=64, db_index=True)
    old_value = models.JSONField(default=dict)
    new_value = models.JSONField(default=dict)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_threshold_audits",
    )
    reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "indicators"
        ordering = ["-created_at", "-id"]  # noqa: RUF012
