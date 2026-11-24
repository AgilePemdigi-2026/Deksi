"""Evaluasi preferensi + pencatatan event notifikasi.

Pemisahan tegas: record_event selalu mencatat; should_notify menentukan
apakah event menjadi notifikasi aktif. Mematikan preferensi tidak
menghapus pencatatan error operasional.
"""
from indicators.notification_model import NotificationEvent, NotificationPreference

DEFAULTS = {
    NotificationPreference.Kind.SYNC_FAILED: True,
    NotificationPreference.Kind.THRESHOLD_EXCEEDED: False,
    NotificationPreference.Kind.VALIDATION_FAILED: True,
}

DESCRIPTIONS = {
    NotificationPreference.Kind.SYNC_FAILED: "Proses akuisisi sumber gagal.",
    NotificationPreference.Kind.THRESHOLD_EXCEEDED: "Diagnostic Engine menghasilkan peringatan.",
    NotificationPreference.Kind.VALIDATION_FAILED: "Data gagal melewati validasi.",
}


def should_notify(kind: str) -> bool:
    pref = NotificationPreference.objects.filter(kind=kind).first()
    if pref is None:
        return bool(DEFAULTS.get(kind, False))
    return bool(pref.enabled)


def record_event(*, kind: str, source_id: str = "", message: str = "") -> NotificationEvent:
    """Catat event; tandai notified hanya bila preferensi aktif."""
    notified = should_notify(kind)
    return NotificationEvent.objects.create(
        kind=kind,
        source_id_snapshot=(source_id or "")[:32],
        notified=notified,
        safe_message=(message or "")[:500],
    )
