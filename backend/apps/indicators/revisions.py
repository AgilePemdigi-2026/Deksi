"""Capture frozen facts and explicitly review/publish them. Never run on public GET."""
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from .models import EconomicIndicator, IndicatorDataPoint, SourceTrace, SourceTraceRevision, PublicationStatus
from .snapshots import capture_facts, digest


@transaction.atomic
def capture_revision(point_id, *, data_origin='unknown'):
    # Consistent lock order: master -> point -> optional trace. No source I/O.
    indicator_id = IndicatorDataPoint.objects.values_list('indicator_id', flat=True).get(pk=point_id)
    indicator = EconomicIndicator.objects.select_for_update().get(pk=indicator_id)
    point = IndicatorDataPoint.objects.select_for_update().get(pk=point_id)
    if point.indicator_id != indicator.pk:
        raise ValidationError('Observation moved while being captured; retry.')
    point.indicator = indicator
    trace = SourceTrace.objects.select_for_update().filter(data_point_id=point.pk).first()
    previous = SourceTraceRevision.objects.filter(data_point_id=point.pk).order_by('-sequence').first()
    if previous and previous.snapshot['identity']['indicator_id'] != str(indicator.pk):
        raise ValidationError('A revised indicator requires a new observation identity.')
    sequence = previous.sequence + 1 if previous else 1
    revision_id = uuid.uuid4()
    snapshot = capture_facts(point, trace, revision_id=revision_id, sequence=sequence, data_origin=data_origin)
    return SourceTraceRevision.objects.create(
        id=revision_id, data_point=point, source_trace=trace, sequence=sequence,
        previous_revision=previous, snapshot=snapshot, snapshot_hash=digest(snapshot),
    )


def _reviewer(actor):
    if not getattr(actor, 'is_authenticated', False) or not getattr(actor, 'pk', None):
        raise PermissionDenied('An authorized reviewer is required.')
    user = get_user_model().objects.get(pk=actor.pk)
    if not user.is_active or not user.is_staff or not (user.is_superuser or user.role in {'reviewer', 'superadmin'}):
        raise PermissionDenied('An authorized reviewer is required.')
    return user


@transaction.atomic
def submit_revision(revision_id, actor):
    _reviewer(actor)
    revision = SourceTraceRevision.objects.select_for_update().get(pk=revision_id)
    revision.validate_content()
    if revision.publication_status != PublicationStatus.DRAFT:
        raise ValidationError('Only a draft may be submitted.')
    # Intentionally bypass the public QuerySet guard only for this controlled transition.
    models.QuerySet.update(SourceTraceRevision.objects.filter(pk=revision.pk), publication_status=PublicationStatus.PENDING_REVIEW)
    revision.refresh_from_db()
    return revision


@transaction.atomic
def publish_revision(revision_id, actor):
    user = _reviewer(actor)
    revision = SourceTraceRevision.objects.select_for_update().get(pk=revision_id)
    revision.validate_content()
    if revision.publication_status != PublicationStatus.PENDING_REVIEW:
        raise ValidationError('Publish requires a submitted revision, not a working point status.')
    if revision.snapshot['data_origin'] == 'demo':
        raise ValidationError('Demo revisions cannot enter the production publication path.')
    now = timezone.now()
    models.QuerySet.update(
        SourceTraceRevision.objects.filter(pk=revision.pk),
        publication_status=PublicationStatus.PUBLISHED,
        reviewed_by_id=user.pk, reviewed_at=now, published_at=now,
    )
    revision.refresh_from_db()
    return revision


@transaction.atomic
def withdraw_revision(revision_id, actor):
    _reviewer(actor)
    revision = SourceTraceRevision.objects.select_for_update().get(pk=revision_id)
    if revision.publication_status != PublicationStatus.PUBLISHED:
        raise ValidationError('Only a published revision may be withdrawn.')
    # Preserve the original review/publication facts. Full lifecycle audit is out of scope.
    models.QuerySet.update(SourceTraceRevision.objects.filter(pk=revision.pk), publication_status=PublicationStatus.REJECTED)
    revision.refresh_from_db()
    return revision
