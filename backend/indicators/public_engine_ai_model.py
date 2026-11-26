"""Immutable public engine AI requests and human decisions."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PublicEngineAIDailyUsage(models.Model):
    day = models.DateField(unique=True)
    count = models.PositiveIntegerField(default=0)


class PublicEngineAIRequest(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued'
        RUNNING = 'running'
        READY = 'ready'
        FAILED = 'failed'
        UNKNOWN = 'unknown'
        APPROVED = 'approved'
        REJECTED = 'rejected'

    request_key = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    input_digest = models.CharField(max_length=64)
    result_digest = models.CharField(max_length=64)
    period_end = models.DateField()
    snapshot = models.JSONField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED)
    narrative = models.JSONField(null=True)
    error_code = models.CharField(max_length=40, blank=True, default='')
    claimed_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    approved_result_digest = models.CharField(max_length=64, blank=True, default='')
    approved_content_digest = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('period_end', 'input_digest'), name='engine_ai_input_once')]
        indexes = [models.Index(fields=('status', 'id'), name='engine_ai_status_id')]
        permissions = [('review_publicengineairequest', 'Review public Economic Engine AI narratives')]


class PublicEngineAIReview(models.Model):
    request = models.OneToOneField(PublicEngineAIRequest, on_delete=models.PROTECT, related_name='review')
    result_digest = models.CharField(max_length=64)
    content_digest = models.CharField(max_length=64)
    decision = models.CharField(max_length=10, choices=(('approved', 'approved'), ('rejected', 'rejected')))
    notes = models.CharField(max_length=500, blank=True, default='')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reviewed_at = models.DateTimeField(default=timezone.now)
