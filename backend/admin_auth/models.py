from django.db import models


class ResetRateBucket(models.Model):
    """Short-lived HMAC keys only; never store address, IP, token or password."""

    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
