"""Private PDB narrative lifecycle. Never publishes or edits economic observations."""
import hmac
import re
import uuid
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.utils import timezone

from indicators.ai_facts import FactPackageError, build_fact_package, validate_fact_package
from indicators.ai_narrative_policy import (
    MESSAGES,
    PROMPT_VERSION,
    SUPPORTED_PROMPT_VERSIONS,
    VALIDATOR_VERSION,
    NarrativeError,
    digest,
    model_config,
)
from indicators.ai_narrative_provider import generate, validate_narrative
from indicators.lifecycle import require_reviewer
from indicators.models import AINarrativeDraft, AINarrativeReview, Indicator, Observation, Source

GENERATE_PERMISSION = 'indicators.generate_ainarrativedraft'
REVIEW_PERMISSION = 'indicators.review_ainarrativedraft'
VIEW_PERMISSION = 'indicators.view_ainarrativedraft'


def authorize(user, permission=None):
    if permission:
        return require_reviewer(user, permission)
    for name in (VIEW_PERMISSION, GENERATE_PERMISSION, REVIEW_PERMISSION):
        try:
            return require_reviewer(user, name)
        except PermissionDenied:
            continue
    raise PermissionDenied('Izin narasi diperlukan.')


def capabilities(user):
    values = {}
    for key, permission in (('canRead', None), ('canGenerate', GENERATE_PERMISSION),
                            ('canReview', REVIEW_PERMISSION)):
        try:
            authorize(user, permission)
            values[key] = True
        except PermissionDenied:
            values[key] = False
    try:
        model_config()
        values['generationConfigured'] = True
    except NarrativeError:
        values['generationConfigured'] = False
    return values


def _identifier(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not int or not 0 < value < 2**63:
        raise NarrativeError('invalid_request', 400)


def _request_key(value):
    try:
        key = uuid.UUID(value) if type(value) is str else value
        if type(key) is not uuid.UUID or (type(value) is str and str(key) != value):
            raise ValueError
        return key
    except (ValueError, TypeError, AttributeError):
        raise NarrativeError('invalid_request', 400) from None


def eligible_package(observation_id, comparison_id):
    try:
        package = build_fact_package(observation_id, comparison_id=comparison_id)
    except FactPackageError:
        raise NarrativeError('unavailable_input', 409) from None
    if any(fact is not None and fact['evidence']['status'] != 'integrity_ok'
           for fact in package['facts'].values()):
        raise NarrativeError('unavailable_input', 409)
    return package


def assert_snapshot(draft):
    try:
        validate_fact_package(draft.fact_package)
        selection = draft.fact_package['selection']
        if (draft.input_digest != draft.fact_package['inputDigest']
                or selection['observationId'] != draft.observation_id
                or selection['comparisonObservationId'] != draft.comparison_id):
            raise ValueError
    except (FactPackageError, TypeError, ValueError):
        raise NarrativeError('invalid_snapshot') from None


def current_input_matches(draft):
    assert_snapshot(draft)
    try:
        package = eligible_package(draft.observation_id, draft.comparison_id)
    except NarrativeError:
        raise NarrativeError('stale_input') from None
    if not hmac.compare_digest(package['inputDigest'], draft.input_digest):
        raise NarrativeError('stale_input')


def request_draft(user, *, request_key, observation_id, comparison_id=None, parent_id=None):
    user = authorize(user, GENERATE_PERMISSION)
    key = _request_key(request_key)
    for value, nullable in ((observation_id, False), (comparison_id, True), (parent_id, True)):
        _identifier(value, nullable)
    request_digest = digest({'actorId': user.pk, 'observationId': observation_id,
                             'comparisonId': comparison_id, 'parentId': parent_id})
    existing = AINarrativeDraft.objects.filter(request_key=key).first()
    if existing:
        if existing.request_digest != request_digest or existing.created_by_id != user.pk:
            raise NarrativeError('conflict')
        assert_snapshot(existing)
        return existing
    config = model_config()
    package = eligible_package(observation_id, comparison_id)
    if parent_id is not None:
        parent = AINarrativeDraft.objects.filter(pk=parent_id).first()
        if not parent or parent.observation_id != observation_id or parent.comparison_id != comparison_id:
            raise NarrativeError('conflict')
    try:
        with transaction.atomic():
            return AINarrativeDraft.objects.create(
                request_key=key, request_digest=request_digest, created_by=user,
                observation_id=observation_id, comparison_id=comparison_id, parent_id=parent_id,
                fact_package=package, input_digest=package['inputDigest'], active_slot=1,
                requested_model=config.model, provider_fingerprint=config.fingerprint,
                prompt_version=PROMPT_VERSION, validator_version=VALIDATOR_VERSION)
    except IntegrityError:
        existing = AINarrativeDraft.objects.filter(request_key=key).first()
        if existing and existing.request_digest == request_digest and existing.created_by_id == user.pk:
            return existing
        raise NarrativeError('busy' if existing is None else 'conflict') from None


def serialize_draft(draft):
    assert_snapshot(draft)
    if draft.generation_status == 'ready':
        assert_content(draft)
    review = AINarrativeReview.objects.filter(draft_id=draft.pk).first()
    if review and review.content_digest != draft.content_digest:
        raise NarrativeError('invalid_snapshot')
    expired = (draft.generation_status == 'running' and draft.deadline_at is not None
               and draft.deadline_at <= timezone.now())
    error_code = 'outcome_unknown' if expired else draft.error_code
    return {'id': draft.pk, 'requestKey': str(draft.request_key),
            'generationStatus': 'unknown' if expired else draft.generation_status,
            'reviewStatus': review.decision if review else 'pending',
            'factPackage': draft.fact_package, 'inputDigest': draft.input_digest,
            'contentDigest': draft.content_digest, 'requestedModel': draft.requested_model,
            'reportedModel': draft.reported_model, 'promptVersion': draft.prompt_version,
            'validatorVersion': draft.validator_version, 'narrative': draft.narrative,
            'errorCode': error_code or None, 'errorMessage': MESSAGES.get(error_code),
            'createdAt': draft.created_at.isoformat(),
            'startedAt': draft.started_at.isoformat() if draft.started_at else None,
            'finishedAt': draft.finished_at.isoformat() if draft.finished_at else None,
            'parentId': draft.parent_id, 'active': draft.active_slot == 1,
            'reconciledAt': draft.reconciled_at.isoformat() if draft.reconciled_at else None,
            'review': None if review is None else {'decision': review.decision, 'notes': review.notes,
                'reviewedAt': review.reviewed_at.isoformat(), 'contentDigest': review.content_digest}}


def content_digest(draft, narrative, reported_model):
    return digest({'inputDigest': draft.input_digest, 'requestedModel': draft.requested_model,
                   'reportedModel': reported_model, 'providerFingerprint': draft.provider_fingerprint,
                   'promptVersion': draft.prompt_version, 'validatorVersion': draft.validator_version,
                   'narrative': narrative})


def assert_content(draft):
    assert_snapshot(draft)
    try:
        validate_narrative(draft.narrative, draft.fact_package)
        if (draft.prompt_version not in SUPPORTED_PROMPT_VERSIONS or draft.validator_version != VALIDATOR_VERSION
                or not draft.content_digest or draft.content_digest != content_digest(
                    draft, draft.narrative, draft.reported_model)):
            raise ValueError
    except (NarrativeError, ValueError, TypeError):
        raise NarrativeError('invalid_snapshot') from None


def run_once(*, transport=None):
    """Process at most one claim; the caller must be a dedicated operator runner."""
    config = model_config()
    now = timezone.now()
    with transaction.atomic():
        AINarrativeDraft.objects.filter(generation_status='running', deadline_at__lte=now).update(
            generation_status='unknown', claim=None, finished_at=now, error_code='outcome_unknown')
        draft = AINarrativeDraft.objects.select_for_update().filter(generation_status='queued').order_by('id').first()
        if draft is None:
            return None
        claim = uuid.uuid4()
        changed = AINarrativeDraft.objects.filter(pk=draft.pk, generation_status='queued', active_slot=1).update(
            generation_status='running', claim=claim, started_at=now,
            deadline_at=now + timedelta(seconds=config.timeout + 10))
        if not changed:
            return None
        draft.refresh_from_db()
    error_code, output, reported_model = '', None, None
    try:
        authorize(draft.created_by, GENERATE_PERMISSION)
        current_input_matches(draft)
        if (draft.requested_model != config.model or draft.provider_fingerprint != config.fingerprint
                or draft.prompt_version != PROMPT_VERSION or draft.validator_version != VALIDATOR_VERSION):
            raise NarrativeError('config_changed')
        output, reported_model = generate(config, draft.fact_package, transport=transport)
    except PermissionDenied:
        error_code = 'conflict'
    except NarrativeError as error:
        error_code = error.code
    except Exception:
        # Unexpected interruption cannot prove the POST did not reach the provider.
        error_code = 'outcome_unknown'
    finished = timezone.now()
    with transaction.atomic():
        query = AINarrativeDraft.objects.filter(pk=draft.pk, generation_status='running', claim=claim, active_slot=1)
        if draft.deadline_at <= finished:
            error_code = 'outcome_unknown'
        unknown = error_code == 'outcome_unknown'
        status = 'unknown' if unknown else 'failed' if error_code else 'ready'
        accepted_output = output if not error_code else None
        query.update(generation_status=status, claim=None, active_slot=1 if unknown else None,
            finished_at=finished, error_code=error_code, narrative=accepted_output,
            reported_model=reported_model if not error_code else None,
            content_digest=content_digest(draft, output, reported_model) if accepted_output else None)
    return AINarrativeDraft.objects.get(pk=draft.pk)


def _notes(notes, required=False):
    if not isinstance(notes, str) or len(notes) > 500 or (required and not notes.strip()):
        raise NarrativeError('invalid_request', 400)
    return notes.strip()


@transaction.atomic
def review_draft(user, draft_id, *, content_digest, decision, notes):
    user = authorize(user, REVIEW_PERMISSION)
    _identifier(draft_id)
    notes = _notes(notes, required=decision != 'approved')
    if (decision not in ('approved', 'needs_revision', 'rejected') or not isinstance(content_digest, str)
            or not re.fullmatch(r'[a-f0-9]{64}', content_digest)):
        raise NarrativeError('invalid_request', 400)
    draft = AINarrativeDraft.objects.select_for_update().filter(pk=draft_id).first()
    if draft is None or draft.generation_status != 'ready' or AINarrativeReview.objects.filter(draft=draft).exists():
        raise NarrativeError('not_ready')
    assert_content(draft)
    if not hmac.compare_digest(draft.content_digest, content_digest):
        raise NarrativeError('conflict')
    if decision == 'approved':
        # Match observation staging's master lock order. No joins widen these locks.
        if not Indicator.objects.select_for_update().filter(code='pdb').exists():
            raise NarrativeError('stale_input')
        if not Source.objects.select_for_update().filter(source_id='BPS').exists():
            raise NarrativeError('stale_input')
        ids = [draft.observation_id, *([] if draft.comparison_id is None else [draft.comparison_id])]
        list(Observation.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
        current_input_matches(draft)
    AINarrativeReview.objects.create(draft=draft, content_digest=content_digest,
        decision=decision, notes=notes, reviewed_by=user)
    return draft


@transaction.atomic
def reconcile_draft(user, draft_id, *, acknowledged, notes):
    authorize(user, GENERATE_PERMISSION)
    _identifier(draft_id)
    notes = _notes(notes, required=True)
    if acknowledged is not True:
        raise NarrativeError('invalid_request', 400)
    draft = AINarrativeDraft.objects.select_for_update().filter(pk=draft_id).first()
    expired = (draft is not None and draft.generation_status == 'running' and draft.deadline_at
               and draft.deadline_at <= timezone.now())
    if draft is None or (draft.generation_status != 'unknown' and not expired) or draft.active_slot != 1:
        raise NarrativeError('not_ready')
    AINarrativeDraft.objects.filter(pk=draft.pk).update(generation_status='unknown', active_slot=None,
        claim=None, finished_at=timezone.now(), error_code='outcome_unknown',
        reconciled_at=timezone.now(), reconciliation_notes=notes)
    draft.refresh_from_db()
    return draft
