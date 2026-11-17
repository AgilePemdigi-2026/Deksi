"""Feature 26: preferensi notifikasi operasional Admin.

Kanal pengiriman eksternal (email/Telegram/dll) belum tersedia di proyek,
sehingga mekanisme didukung adalah pencatatan event + evaluasi preferensi.
Event operasional selalu dicatat; preferensi mengatur apakah event
dianggap notifikasi aktif. Tanpa secret di model ini.
"""
from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    class Kind(models.TextChoices):
        SYNC_FAILED = "sync_failed", "Gagal sinkronisasi"
        THRESHOLD_EXCEEDED = "threshold_exceeded", "Ambang batas terlewati"
        VALIDATION_FAILED = "validation_failed", "Kegagalan validasi"

    kind = models.CharField(max_length=32, choices=Kind.choices, unique=True)
    enabled = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_notification_prefs",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "indicators"

    def __str__(self):
        return f"Notifikasi {self.kind}: {'aktif' if self.enabled else 'nonaktif'}"


class NotificationEvent(models.Model):
    """Pencatatan event operasional; tidak dihapus saat preferensi dimatikan."""

    kind = models.CharField(max_length=32, choices=NotificationPreference.Kind.choices, db_index=True)
    source_id_snapshot = models.CharField(max_length=32, blank=True, default="")
    notified = models.BooleanField(default=False)
    safe_message = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "indicators"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Event {self.kind} ({'notified' if self.notified else 'logged'})"


class NotificationAudit(models.Model):
    kind = models.CharField(max_length=32)
    old_value = models.JSONField(default=dict)
    new_value = models.JSONField(default=dict)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deksi_notification_audits",
    )
    reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "indicators"
        ordering = ["-created_at", "-id"]
