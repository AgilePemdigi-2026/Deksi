"""Snapshot validation. No network access or economic calculation belongs here."""
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils import timezone


def fail():
    raise ValidationError('Invalid source trace snapshot.')


def keys(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        fail()


def text(value, required=False, limit=2000):
    if value is None and not required:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        fail()


def optional(value):
    return value.strip() or None if isinstance(value, str) else value


def decimal_string(value):
    if value is None:
        return None
    if isinstance(value, (float, bool)):
        fail()
    try:
        number = Decimal(value)
        fixed = format(number, '.4f')
        if not number.is_finite() or Decimal(fixed) != number or not re.fullmatch(r'-?(?:0|[1-9]\d{0,15})\.\d{4}', fixed):
            fail()
        return fixed
    except (InvalidOperation, ValueError, TypeError):
        fail()


def safe_url(value):
    if not isinstance(value, str) or not value or '\\' in value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return None
        parsed.port
        return value
    except ValueError:
        return None


def period(value):
    keys(value, 'type year quarter month label')
    kind, year, quarter, month = (value[k] for k in ('type', 'year', 'quarter', 'month'))
    if type(year) is not int or not 1 <= year <= 9999:
        fail()
    if kind == 'annual':
        valid = quarter is None and month is None
    elif kind == 'quarterly':
        valid = type(quarter) is int and 1 <= quarter <= 4 and month is None
    elif kind == 'monthly':
        valid = type(month) is int and 1 <= month <= 12 and quarter is None
    else:
        valid = False
    if not valid:
        fail()
    text(value['label'], required=True, limit=50)


def uuid_text(value):
    if not isinstance(value, str):
        fail()
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError):
        fail()


def aware_timestamp(value):
    if value is None:
        return
    try:
        parsed = datetime.fromisoformat(value)
        if not timezone.is_aware(parsed):
            fail()
    except (ValueError, TypeError):
        fail()


def validate_input(item):
    keys(item, 'key label value unit period source_data_point_id source_revision_id price_concept base_year')
    text(item['key'], required=True, limit=100)
    for key in ('label', 'unit', 'price_concept'):
        text(item[key])
    if item['value'] is not None and (not isinstance(item['value'], str) or decimal_string(item['value']) != item['value']):
        fail()
    if item['period'] is not None:
        period(item['period'])
    for key in ('source_data_point_id', 'source_revision_id'):
        if item[key] is not None:
            uuid_text(item[key])
    if (item['source_data_point_id'] is None) != (item['source_revision_id'] is None):
        fail()
    if item['base_year'] is not None and (type(item['base_year']) is not int or not 1 <= item['base_year'] <= 9999):
        fail()


def digest(snapshot):
    try:
        encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError):
        fail()
    if len(encoded) > 131072:
        fail()
    return hashlib.sha256(encoded).hexdigest()


def validate_snapshot(revision):
    s = revision.snapshot
    digest(s)
    keys(s, 'identity indicator observation source official_value calculation data_origin')
    identity = s['identity']
    keys(identity, 'indicator_id data_point_id trace_id revision_id revision_sequence schema_version source_version')
    expected = {'indicator_id': str(revision.indicator_id), 'data_point_id': str(revision.data_point_id),
                'trace_id': str(revision.source_trace_id), 'revision_id': str(revision.id),
                'revision_sequence': revision.sequence, 'schema_version': revision.schema_version}
    if (any(type(identity[k]) is not type(v) or identity[k] != v for k, v in expected.items())
            or type(revision.schema_version) is not int or revision.schema_version != 1
            or type(revision.sequence) is not int or revision.sequence < 1):
        fail()
    text(identity['source_version'], limit=20)
    indicator = s['indicator']
    keys(indicator, 'code name unit data_type')
    text(indicator['code'], required=True, limit=50)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', indicator['code']):
        fail()
    text(indicator['name'], required=True, limit=200)
    text(indicator['unit'], limit=50)
    if indicator['data_type'] not in ('official', 'derived'):
        fail()
    observation = s['observation']
    keys(observation, 'value data_layer period')
    if observation['value'] is not None and (not isinstance(observation['value'], str) or decimal_string(observation['value']) != observation['value']):
        fail()
    if observation['data_layer'] != ('derived' if indicator['data_type'] == 'derived' else 'clean'):
        fail()
    period(observation['period'])
    source = s['source']
    keys(source, 'institution_name institution_code publication_name publication_url release_date fetched_at')
    for key in ('institution_name', 'institution_code', 'publication_name'):
        text(source[key], limit=300)
    if source['publication_url'] is not None and (not isinstance(source['publication_url'], str)
            or len(source['publication_url']) > 2000 or safe_url(source['publication_url']) != source['publication_url']):
        fail()
    if source['release_date'] is not None:
        try:
            if date.fromisoformat(source['release_date']).isoformat() != source['release_date']:
                fail()
        except (TypeError, ValueError):
            fail()
    aware_timestamp(source['fetched_at'])
    official = s['official_value']
    keys(official, 'value unit period')
    if official['value'] is not None and (not isinstance(official['value'], str) or decimal_string(official['value']) != official['value']):
        fail()
    text(official['unit'], limit=50)
    text(official['period'], limit=50)
    calculation = s['calculation']
    if indicator['data_type'] == 'official':
        if calculation is not None:
            fail()
    else:
        keys(calculation, 'formula_id formula_version expression inputs')
        for key in ('formula_id', 'formula_version', 'expression'):
            text(calculation[key])
        if not isinstance(calculation['inputs'], list) or len(calculation['inputs']) > 100:
            fail()
        seen = set()
        for item in calculation['inputs']:
            validate_input(item)
            if item['key'] in seen:
                fail()
            seen.add(item['key'])
    if s['data_origin'] not in ('unknown', 'demo', 'official_source'):
        fail()


def capture_revision(trace_id, *, data_origin='unknown'):
    from django.db import transaction
    from .models import EconomicIndicator, IndicatorDataPoint, SourceTrace, SourceTraceRevision

    with transaction.atomic():
        trace = SourceTrace.objects.select_for_update().get(pk=trace_id)
        point = IndicatorDataPoint.objects.select_for_update().get(pk=trace.data_point_id)
        indicator = EconomicIndicator.objects.select_for_update().get(pk=point.indicator_id)
        previous = SourceTraceRevision.objects.filter(source_trace=trace).first()
        if previous and (previous.data_point_id != point.id or previous.indicator_id != indicator.id):
            fail()
        revision = SourceTraceRevision(
            source_trace=trace, data_point=point, indicator=indicator,
            sequence=previous.sequence + 1 if previous else 1, previous_revision=previous,
        )
        calculation = None
        if indicator.data_type == 'derived':
            detail = trace.formula_inputs_detail
            detail = detail if isinstance(detail, dict) and detail.get('schema_version') == 1 else {}
            inputs = detail.get('inputs', [])
            try:
                if not isinstance(inputs, list) or len(inputs) > 100:
                    fail()
                for item in inputs:
                    validate_input(item)
            except ValidationError:
                inputs = []
            calculation = {
                'formula_id': optional(detail.get('formula_id')),
                'formula_version': optional(detail.get('formula_version')),
                'expression': optional(trace.formula_used), 'inputs': inputs,
            }
        revision.snapshot = {
            'identity': {
                'indicator_id': str(indicator.id), 'data_point_id': str(point.id),
                'trace_id': str(trace.id), 'revision_id': str(revision.id),
                'revision_sequence': revision.sequence, 'schema_version': revision.schema_version,
                'source_version': optional(trace.version),
            },
            'indicator': {'code': indicator.code, 'name': indicator.name,
                          'unit': optional(indicator.unit), 'data_type': indicator.data_type},
            'observation': {
                'value': decimal_string(point.value), 'data_layer': point.data_layer,
                'period': {'type': point.period_type, 'year': point.period_year,
                           'quarter': point.period_quarter, 'month': point.period_month, 'label': point.period_label},
            },
            'source': {
                'institution_name': optional(trace.institution_name), 'institution_code': optional(trace.institution_code),
                'publication_name': optional(trace.publication_name), 'publication_url': safe_url(trace.publication_url),
                'release_date': trace.release_date.isoformat() if trace.release_date is not None else None,
                'fetched_at': trace.fetched_at.isoformat() if trace.fetched_at is not None else None,
            },
            'official_value': {'value': decimal_string(trace.official_value),
                               'unit': optional(trace.official_unit), 'period': optional(trace.official_period)},
            'calculation': calculation, 'data_origin': data_origin,
        }
        revision.save()
        return revision


def review_revision(revision_id, reviewer, decision, *, expected_digest):
    from django.contrib.auth import get_user_model
    from django.core.exceptions import PermissionDenied
    from django.db import models, transaction
    from .models import SourceTraceRevision

    actor = get_user_model().objects.filter(pk=getattr(reviewer, 'pk', None)).first()
    if not actor or not actor.is_active or not actor.is_staff or not actor.has_perm('indicators.publish_sourcetracerevision'):
        raise PermissionDenied('Review permission is required.')
    if decision not in ('published', 'rejected'):
        fail()
    with transaction.atomic():
        revision = SourceTraceRevision.objects.select_for_update().get(pk=revision_id)
        validate_snapshot(revision)
        if revision.publication_status != 'draft' or revision.content_sha256 != expected_digest or digest(revision.snapshot) != expected_digest:
            raise ValidationError('This exact draft must be reviewed once; reload before retrying.')
        now = timezone.now()
        # The controlled lifecycle write cannot change frozen content or inherit another approval.
        changed = models.QuerySet(model=SourceTraceRevision, using=revision._state.db).filter(
            pk=revision.id, publication_status='draft', content_sha256=expected_digest,
            reviewed_by__isnull=True, reviewed_at__isnull=True, published_at__isnull=True,
        ).update(publication_status=decision, reviewed_by_id=actor.id, reviewed_at=now,
                 published_at=now if decision == 'published' else None)
        if changed != 1:
            fail()
        revision.refresh_from_db()
        return revision


def public_revisions():
    from .models import SourceTraceRevision

    return SourceTraceRevision.objects.filter(
        publication_status='published', reviewed_by__isnull=False,
        reviewed_at__isnull=False, published_at__isnull=False,
    )
