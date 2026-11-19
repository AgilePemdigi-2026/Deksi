"""Feature 27: pemulihan konfigurasi operasional ke nilai default.

Sumber kebenaran default ada di backend (modul ini + DEFAULTS tiap domain).
Prinsip:
- Hanya domain configurable yang dipulihkan; formula inti Economic Engine,
  data RAW/CLEAN, histori, dan audit log tidak tersentuh.
- Tiap domain dipulihkan dalam transaksinya sendiri; kegagalan satu domain
  tidak merusak domain lain dan konfigurasi valid sebelumnya dipertahankan.
- Domain yang modelnya belum tersedia (belum di-merge dari branch fitur
  lain) dilaporkan `skipped-unsupported`, bukan diarang nilainya.
"""
from django.db import transaction

RESTORABLE_DOMAINS = ("notifications", "schedules", "thresholds")


def _restore_notifications(*, actor):
    from indicators.notification_model import NotificationAudit, NotificationPreference
    from indicators.notification_service import DEFAULTS

    results = []
    with transaction.atomic():
        for kind, default_enabled in DEFAULTS.items():
            pref = NotificationPreference.objects.filter(kind=kind).first()
            old = {"enabled": pref.enabled if pref else None,
                   "version": pref.version if pref else 0}
            if pref is None:
                pref = NotificationPreference.objects.create(
                    kind=kind, enabled=bool(default_enabled), version=1,
                    updated_by=actor,
                )
            else:
                pref.enabled = bool(default_enabled)
                pref.version += 1
                pref.updated_by = actor
                pref.save()
            new = {"enabled": pref.enabled, "version": pref.version}
            NotificationAudit.objects.create(
                kind=kind, old_value=old, new_value=new,
                actor=actor, reason="restore-default",
            )
            results.append({"kind": kind, "status": "restored", "value": new})
    return results


def _restore_schedules(*, actor):
    try:
        from indicators.schedule_model import ScheduleAudit, ScheduleConfig
    except ImportError:
        return [{"kind": "schedules", "status": "skipped-unsupported",
                 "detail": "Model jadwal belum tersedia di branch ini."}]
    from indicators.schedule_views import DEFAULT_SCHEDULE_TEXT

    results = []
    with transaction.atomic():
        for cfg in ScheduleConfig.objects.select_related("source").all():
            source = cfg.source
            old = {"intervalDays": cfg.interval_days, "enabled": cfg.enabled,
                   "version": cfg.version}
            default_text = DEFAULT_SCHEDULE_TEXT.get(source.source_id, "")
            cfg.interval_days = 30
            cfg.run_time = None
            cfg.enabled = True
            cfg.next_run = None
            cfg.version += 1
            cfg.updated_by = actor
            cfg.save()
            source.update_schedule = default_text
            source.save(update_fields=["update_schedule"])
            new = {"intervalDays": cfg.interval_days, "enabled": cfg.enabled,
                   "version": cfg.version}
            ScheduleAudit.objects.create(
                source_id_snapshot=source.source_id, old_value=old,
                new_value=new, actor=actor, reason="restore-default",
            )
            results.append({"kind": source.source_id, "status": "restored", "value": new})
    if not results:
        results.append({"kind": "schedules", "status": "restored-empty",
                        "detail": "Tidak ada konfigurasi jadwal tersimpan."})
    return results


def _restore_thresholds(*, actor):  # noqa: ARG001
    try:
        from indicators import threshold_model  # noqa: F401
    except ImportError:
        return [{"kind": "thresholds", "status": "skipped-unsupported",
                 "detail": "Model threshold belum tersedia; formula inti tidak diubah."}]
    return [{"kind": "thresholds", "status": "skipped-unsupported",
             "detail": "Restore threshold mengikuti definisi resmi model."}]


def restore_domains(*, domains, actor):
    handlers = {
        "notifications": _restore_notifications,
        "schedules": _restore_schedules,
        "thresholds": _restore_thresholds,
    }
    out = {}
    for domain in domains:
        if domain not in handlers:
            out[domain] = [{"kind": domain, "status": "rejected",
                             "detail": f"Domain '{domain}' tidak dikenal."}]
            continue
        out[domain] = handlers[domain](actor=actor)
    return out
