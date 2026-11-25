"""Private narrative requests and decisions, separate from observation publication."""
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.deletion import ProtectedError
from django.utils import timezone


class AINarrativeDraft(models.Model):
    request_key = models.UUIDField(unique=True, editable=False)
    request_digest = models.CharField(max_length=64, editable=False)
    observation_id = models.PositiveBigIntegerField(editable=False)
    comparison_id = models.PositiveBigIntegerField(null=True, editable=False)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    fact_package = models.JSONField(editable=False)
    input_digest = models.CharField(max_length=64, editable=False)
    requested_model = models.CharField(max_length=160, editable=False)
    provider_fingerprint = models.CharField(max_length=64, editable=False)
    prompt_version = models.CharField(max_length=40, editable=False)
    validator_version = models.CharField(max_length=40, editable=False)
    generation_status = models.CharField(max_length=12, default='queued', choices=[
        (value, value) for value in ('queued', 'running', 'ready', 'failed', 'unknown')], editable=False)
    # One pending/in-flight/uncertain request for the pilot, enforced across processes.
    active_slot = models.PositiveSmallIntegerField(null=True, unique=True, editable=False)
    claim = models.UUIDField(null=True, editable=False)
    started_at = models.DateTimeField(null=True, editable=False)
    deadline_at = models.DateTimeField(null=True, editable=False)
    finished_at = models.DateTimeField(null=True, editable=False)
    error_code = models.CharField(max_length=64, blank=True, default='', editable=False)
    narrative = models.JSONField(null=True, editable=False)
    reported_model = models.CharField(max_length=160, null=True, editable=False)
    content_digest = models.CharField(max_length=64, null=True, editable=False)
    reconciled_at = models.DateTimeField(null=True, editable=False)
    reconciliation_notes = models.CharField(max_length=500, blank=True, default='', editable=False)

    class Meta:
        ordering: ClassVar[list[str]] = ['-id']
        default_permissions = ('view',)
        permissions: ClassVar[list[tuple[str, str]]] = [
            ('generate_ainarrativedraft', 'Request and reconcile AI narrative drafts'),
            ('review_ainarrativedraft', 'Review an exact AI narrative revision'),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Versi draft hanya boleh diubah melalui lifecycle narasi.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ProtectedError('Riwayat draft tidak boleh dihapus melalui model.', {self})


class AINarrativeReview(models.Model):
    draft = models.OneToOneField(AINarrativeDraft, on_delete=models.PROTECT, related_name='review', editable=False)
    content_digest = models.CharField(max_length=64, editable=False)
    decision = models.CharField(max_length=16, choices=[
        (value, value) for value in ('approved', 'needs_revision', 'rejected')], editable=False)
    notes = models.CharField(max_length=500, blank=True, default='', editable=False)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False)
    reviewed_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering: ClassVar[list[str]] = ['-id']
        default_permissions = ('view',)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Keputusan review tidak boleh ditimpa.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ProtectedError('Riwayat keputusan tidak boleh dihapus melalui model.', {self})
