from django.core.exceptions import ValidationError

from .models import Source


class InactiveSourceError(ValidationError):
    pass


def require_active_source(source: Source) -> None:
    if source.status != Source.SourceStatus.ACTIVE:
        raise InactiveSourceError(f"Sumber {source.source_id} tidak aktif; akuisisi dibatalkan.")
