"""Public click-to-queue narrative lifecycle. Provider calls only in explicit worker."""
import hashlib
import json
import os
import uuid
from datetime import date

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from indicators.economic_engine import calculate_gdp_shares
from indicators.models import PublicEngineAIDailyUsage, PublicEngineAIRequest, PublicEngineAIReview

MAX_DAILY_HARD_CAP = 100


class PublicEngineAIError(ValueError):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                                    allow_nan=False).encode()).hexdigest()


def _review_digest(row):
    return _digest({'snapshot': row.snapshot, 'resultDigest': row.result_digest, 'narrative': row.narrative})


def calculate_snapshot(quarter):
    """Pin only available deterministic metrics; missing metrics are omitted, never zero-filled."""
    period_end = date.fromisoformat(quarter)
    metrics = calculate_gdp_shares(period_end)
    available = {key: row for key, row in metrics.items() if row.get('available') is True}
    if not available:
        raise PublicEngineAIError('no_available_metrics', 409)
    result_digest = _digest({key: row['resultDigest'] for key, row in sorted(available.items())})
    snapshot = {'period': next(iter(available.values()))['period'], 'observationDate': quarter,
                'availableMetrics': available, 'resultDigest': result_digest}
    from indicators.ai_engine_pilot import ENGINE_METHOD, ENGINE_SCHEMA, PROMPT_VERSION, SCHEMA_VERSION
    snapshot['inputDigest'] = _digest({'methodVersion': ENGINE_METHOD, 'schemaVersion': ENGINE_SCHEMA,
        'narrativeSchemaVersion': SCHEMA_VERSION, 'promptVersion': PROMPT_VERSION,
        'metrics': {key: row['inputDigest'] for key, row in sorted(available.items())}})
    return snapshot


def create_request(request_key, quarter):
    if not getattr(settings, 'DEKSI_PUBLIC_ENGINE_AI_ENABLED', False):
        raise PublicEngineAIError('disabled', 503)
    try:
        key = uuid.UUID(str(request_key))
        if str(key) != str(request_key):
            raise ValueError
        parsed_quarter = date.fromisoformat(quarter)
        if parsed_quarter.isoformat() != quarter:
            raise ValueError
        keyed = PublicEngineAIRequest.objects.filter(request_key=key).first()
        if keyed:
            if keyed.period_end != parsed_quarter:
                raise PublicEngineAIError('request_conflict', 409)
            return keyed, False
        snapshot = calculate_snapshot(quarter)
    except PublicEngineAIError:
        raise
    except (ValueError, TypeError, AttributeError):
        raise PublicEngineAIError('invalid_request') from None
    existing = PublicEngineAIRequest.objects.filter(period_end=quarter, input_digest=snapshot['inputDigest']).first()
    if existing:
        return existing, False
    limit = min(MAX_DAILY_HARD_CAP, max(0, int(getattr(settings, 'DEKSI_ENGINE_AI_DAILY_LIMIT', 0))))
    if limit == 0:
        raise PublicEngineAIError('quota_disabled', 503)
    today = timezone.localdate()
    try:
        with transaction.atomic():
            PublicEngineAIDailyUsage.objects.get_or_create(day=today)
            changed = PublicEngineAIDailyUsage.objects.filter(day=today, count__lt=limit).update(count=F('count') + 1)
            if not changed:
                raise PublicEngineAIError('daily_limit', 429)
            row = PublicEngineAIRequest.objects.create(request_key=key, input_digest=snapshot['inputDigest'],
                result_digest=snapshot['resultDigest'], period_end=quarter, snapshot=snapshot)
        return row, True
    except IntegrityError:
        existing = PublicEngineAIRequest.objects.filter(period_end=quarter, input_digest=snapshot['inputDigest']).first()
        if existing:
            return existing, False
        existing = PublicEngineAIRequest.objects.filter(request_key=key).first()
        if existing and existing.input_digest == snapshot['inputDigest']:
            return existing, False
        raise PublicEngineAIError('request_conflict', 409) from None


def serialize_public(row):
    try:
        current = calculate_snapshot(row.period_end.isoformat())
    except (PublicEngineAIError, ValueError, TypeError):
        return {'requestKey': str(row.request_key), 'status': 'stale', 'period': row.snapshot['period']}
    if current['inputDigest'] != row.input_digest or current['resultDigest'] != row.result_digest:
        return {'requestKey': str(row.request_key), 'status': 'stale', 'period': row.snapshot['period']}
    result = {'requestKey': str(row.request_key), 'status': row.status, 'period': row.snapshot['period']}
    if (row.status == PublicEngineAIRequest.Status.APPROVED
            and row.approved_result_digest == row.result_digest
            and row.approved_content_digest == _review_digest(row)):
        bindings = {key: {'inputDigest': value['inputDigest'], 'resultDigest': value['resultDigest']}
                    for key, value in row.snapshot['availableMetrics'].items()}
        result.update(resultDigest=row.result_digest, metricsBinding=bindings, narrative=row.narrative)
    return result


def _provider_call(row, transport=None):
    from indicators.ai_engine_pilot import ENGINE_METHOD, ENGINE_SCHEMA, build_engine_package, generate_engine_narrative, gemini_config
    api_key = os.environ.get('GEMINI_API_KEY', '')
    model = getattr(settings, 'DEKSI_PUBLIC_ENGINE_AI_MODEL', '')
    packet = {'schemaVersion': ENGINE_SCHEMA, 'methodVersion': ENGINE_METHOD,
              'metrics': row.snapshot['availableMetrics']}
    package = build_engine_package(packet, workflow_simulated=False)
    config = gemini_config(api_key, model)
    # Fixed provider origin from the Gemini adapter; never derived from user/source input.
    return generate_engine_narrative(config, package, transport=transport)


def call_provider(row, transport=None):
    return _provider_call(row, transport)


def run_once(*, transport=None):
    """Claim one durable request exactly once. Unknown outcomes remain terminal."""
    if not getattr(settings, 'DEKSI_PUBLIC_ENGINE_AI_ENABLED', False):
        return None
    stale_before = timezone.now() - timezone.timedelta(minutes=3)
    PublicEngineAIRequest.objects.filter(status=PublicEngineAIRequest.Status.RUNNING,
        claimed_at__lt=stale_before).update(status=PublicEngineAIRequest.Status.UNKNOWN,
            error_code='outcome_unknown', completed_at=timezone.now())
    with transaction.atomic():
        row = PublicEngineAIRequest.objects.filter(status=PublicEngineAIRequest.Status.QUEUED).order_by('id').first()
        if row is None:
            return None
        changed = PublicEngineAIRequest.objects.filter(pk=row.pk, status=PublicEngineAIRequest.Status.QUEUED).update(
            status=PublicEngineAIRequest.Status.RUNNING, claimed_at=timezone.now())
        if not changed:
            return None
        row.refresh_from_db()
    try:
        narrative, _model = call_provider(row, transport=transport)
        status, error = PublicEngineAIRequest.Status.READY, ''
    except Exception as exc:
        code = getattr(exc, 'code', 'outcome_unknown')
        status, error = ((PublicEngineAIRequest.Status.UNKNOWN, 'outcome_unknown') if code == 'outcome_unknown'
                         else (PublicEngineAIRequest.Status.FAILED, code if code in ('invalid_output', 'unconfigured') else 'provider_error'))
        narrative = None
    PublicEngineAIRequest.objects.filter(pk=row.pk, status=PublicEngineAIRequest.Status.RUNNING).update(
        status=status, narrative=narrative, error_code=error, completed_at=timezone.now())
    return PublicEngineAIRequest.objects.get(pk=row.pk)


def review_request(user, request_id, *, result_digest, decision, notes=''):
    if not (user.is_authenticated and user.is_active and user.is_staff
            and user.has_perm('indicators.review_publicengineairequest')):
        raise PermissionDenied
    if decision not in ('approved', 'rejected') or not isinstance(notes, str) or len(notes) > 500:
        raise PublicEngineAIError('invalid_request')
    with transaction.atomic():
        row = PublicEngineAIRequest.objects.select_for_update().filter(pk=request_id).first()
        if not row:
            raise PublicEngineAIError('not_found', 404)
        try:
            current = calculate_snapshot(row.period_end.isoformat())
        except (PublicEngineAIError, ValueError, TypeError):
            raise PublicEngineAIError('review_conflict', 409) from None
        if (row.status != PublicEngineAIRequest.Status.READY or _review_digest(row) != result_digest
                or current['inputDigest'] != row.input_digest or current['resultDigest'] != row.result_digest):
            raise PublicEngineAIError('review_conflict', 409)
        PublicEngineAIReview.objects.create(request=row, result_digest=row.result_digest,
                                            content_digest=result_digest, decision=decision,
                                            notes=notes, reviewed_by=user)
        row.status = PublicEngineAIRequest.Status.APPROVED if decision == 'approved' else PublicEngineAIRequest.Status.REJECTED
        row.approved_result_digest = row.result_digest if decision == 'approved' else ''
        row.approved_content_digest = result_digest if decision == 'approved' else ''
        row.save(update_fields=('status', 'approved_result_digest', 'approved_content_digest'))
    return row
