from django.utils import timezone

from .models import DataUpdateLog

MONTHS_ID = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Agu",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Des",
}


def record_update_success(
    source: str, updated_by=None, observation_count: int = 0, message: str = "",
    event_kind: str = DataUpdateLog.EventKind.UNKNOWN,
) -> DataUpdateLog:
    return DataUpdateLog.objects.create(
        updated_at=timezone.now(),
        updated_by=updated_by,
        source=source,
        status=DataUpdateLog.Status.SUCCESS,
        event_kind=event_kind,
        observation_count=observation_count,
        message=message,
    )


def record_update_failure(source: str, updated_by=None, message: str = "") -> DataUpdateLog:
    return DataUpdateLog.objects.create(
        updated_at=timezone.now(),
        updated_by=updated_by,
        source=source,
        status=DataUpdateLog.Status.FAILED,
        observation_count=0,
        message=message,
    )


def latest_successful_update() -> DataUpdateLog | None:
    return DataUpdateLog.objects.filter(
        status=DataUpdateLog.Status.SUCCESS, event_kind=DataUpdateLog.EventKind.PUBLICATION
    ).first()


def latest_attempt() -> DataUpdateLog | None:
    return DataUpdateLog.objects.first()


def jakarta_time(value):
    if value is None:
        return None
    return timezone.localtime(value)


def format_jakarta(value) -> str | None:
    local = jakarta_time(value)
    if local is None:
        return None
    return f"{local.day:02d} {MONTHS_ID[local.month]} {local.year}, {local.hour:02d}:{local.minute:02d} WIB"


def serialize_update_log(log: DataUpdateLog | None) -> dict | None:
    if log is None:
        return None
    local = jakarta_time(log.updated_at)
    return {
        "updatedAt": local.isoformat() if local else None,
        "formatted": format_jakarta(log.updated_at),
        "updatedBy": log.updated_by.get_username() if log.updated_by else None,
        "source": log.source,
        "status": log.status,
        "observationCount": log.observation_count,
        "message": log.message,
    }
