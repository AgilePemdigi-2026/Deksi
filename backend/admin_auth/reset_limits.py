from datetime import datetime
from datetime import timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import ResetRateBucket

WINDOW_SECONDS = 900


def consume(scope, identity, limit):
    """Fixed 15-minute windows; atomic writes shared by all application processes."""
    now = timezone.now()
    window = int(now.timestamp()) // WINDOW_SECONDS
    key = salted_hmac("deksi.reset.rate.v1", f"{scope}:{window}:{identity}", algorithm="sha256").hexdigest()
    expired = list(ResetRateBucket.objects.filter(expires_at__lte=now).values_list("pk", flat=True)[:200])
    if expired:
        ResetRateBucket.objects.filter(pk__in=expired).delete()
    eligible = ResetRateBucket.objects.filter(pk=key, count__lt=limit)
    if eligible.update(count=F("count") + 1):
        return True
    try:
        with transaction.atomic():
            ResetRateBucket.objects.create(
                key=key,
                count=1,
                expires_at=datetime.fromtimestamp((window + 1) * WINDOW_SECONDS, tz=datetime_timezone.utc),
            )
        return True
    except IntegrityError:
        return bool(eligible.update(count=F("count") + 1))
