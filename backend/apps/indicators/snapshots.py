"""Frozen public facts. No network access, economic calculation or legacy JSON passthrough."""
import hashlib
import json
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone


SCHEMA_VERSION = 1


def text(value):
    return value if isinstance(value, str) and value.strip() else None


def decimal_string(value):
    if value is None:
        return None
    try:
        if isinstance(value, bool) or isinstance(value, float):
            raise ValueError
        number = Decimal(value)
        with localcontext() as context:
            context.prec = 40
            rounded = number.quantize(Decimal('0.0001'))
        if not number.is_finite() or number != rounded or abs(number) >= Decimal('10000000000000000'):
            raise ValueError
        return format(rounded, '.4f')
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError('Invalid decimal facts.') from None


def safe_url(value):
    value = text(value)
    if value is None or re.search(r'[\x00-\x20\x7f\\]', value):
        return None
    try:
        parts = urlsplit(value)
        if parts.username is not None or parts.password is not None:
            return None
        URLValidator(schemes=['http', 'https'])(value)
    except (ValidationError, ValueError):
        return None
    return value


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, datetime) or timezone.is_naive(value):
        raise ValidationError('Acquisition timestamp must be timezone-aware.')
    return value.isoformat()


def digest(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def require(condition):
    if not condition:
        raise ValidationError('Invalid snapshot facts.')


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected.split()))


def valid_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def validate(snapshot, *, point_id, trace_id, revision_id, sequence, schema_version):
    keys(snapshot, 'identity indicator observation source data_origin change official_value calculation limitations')
    identity = snapshot['identity']
    keys(identity, 'indicator_id data_point_id trace_id revision_id revision_sequence schema_version source_version')
    require(valid_uuid(identity['indicator_id']))
    require(identity['data_point_id'] == str(point_id) and identity['trace_id'] == (str(trace_id) if trace_id else None))
    require(identity['revision_id'] == str(revision_id) and identity['revision_sequence'] == sequence)
    require(type(sequence) is int and sequence > 0 and identity['schema_version'] == schema_version == SCHEMA_VERSION)
    require(identity['source_version'] is None or isinstance(identity['source_version'], str))
    indicator = snapshot['indicator']
    keys(indicator, 'code name short_name category definition methodology unit data_type')
    require(isinstance(indicator['code'], str) and 0 < len(indicator['code']) <= 50)
    require(isinstance(indicator['name'], str) and bool(indicator['name'].strip()))
    require(indicator['category'] in {'pdb', 'inflasi', 'fiskal', 'moneter', 'investasi', 'tenaga_kerja'})
    require(indicator['data_type'] in {'official', 'derived'})
    for field in ['short_name', 'definition', 'methodology', 'unit']:
        require(indicator[field] is None or isinstance(indicator[field], str))
    observation = snapshot['observation']
    keys(observation, 'value data_layer period fetched_at')
    require(observation['value'] is None or isinstance(observation['value'], str))
    require(decimal_string(observation['value']) == observation['value'])
    require(observation['data_layer'] == {'official': 'clean', 'derived': 'derived'}[indicator['data_type']])
    period = observation['period']
    keys(period, 'type year quarter month label')
    require(type(period['year']) is int and 1 <= period['year'] <= 9999)
    require(isinstance(period['label'], str) and bool(period['label'].strip()))
    if period['type'] == 'annual':
        require(period['quarter'] is None and period['month'] is None)
    elif period['type'] == 'quarterly':
        require(type(period['quarter']) is int and 1 <= period['quarter'] <= 4 and period['month'] is None)
    elif period['type'] == 'monthly':
        require(type(period['month']) is int and 1 <= period['month'] <= 12 and period['quarter'] is None)
    else:
        raise ValidationError('Unsupported observation frequency.')
    source = snapshot['source']
    keys(source, 'institution_name institution_code publication_name publication_url release_date fetched_at')
    for field in ['institution_name', 'institution_code', 'publication_name']:
        require(source[field] is None or isinstance(source[field], str))
    require(source['publication_url'] is None or safe_url(source['publication_url']) == source['publication_url'])
    if source['release_date'] is not None:
        require(isinstance(source['release_date'], str) and date.fromisoformat(source['release_date']).isoformat() == source['release_date'])
    for value in [source['fetched_at'], observation['fetched_at']]:
        if value is not None:
            require(isinstance(value, str) and timezone.is_aware(datetime.fromisoformat(value)))
    require(snapshot['data_origin'] in {'unknown', 'demo', 'official_source'})
    require(snapshot['change'] is None)
    keys(snapshot['official_value'], 'value unit period')
    official = snapshot['official_value']
    require(official['value'] is None or isinstance(official['value'], str))
    require(decimal_string(official['value']) == official['value'])
    require(all(official[f] is None or isinstance(official[f], str) for f in ['unit', 'period']))
    if indicator['data_type'] == 'official':
        require(snapshot['calculation'] is None)
    else:
        keys(snapshot['calculation'], 'formula_id formula_version expression inputs')
        require(snapshot['calculation']['formula_id'] is None and snapshot['calculation']['formula_version'] is None)
        require(snapshot['calculation']['expression'] is None or isinstance(snapshot['calculation']['expression'], str))
        require(snapshot['calculation']['inputs'] == [])
    require(isinstance(snapshot['limitations'], list) and set(snapshot['limitations']) <= {'source_url_rejected', 'formula_inputs_unavailable'})


def capture_facts(point, trace, *, revision_id, sequence, data_origin):
    indicator = point.indicator
    source_url = safe_url(trace.publication_url) if trace else None
    limitations = []
    if trace and text(trace.publication_url) and source_url is None:
        limitations.append('source_url_rejected')
    if indicator.data_type == 'derived':
        limitations.append('formula_inputs_unavailable')
    return {
        'identity': {
            'indicator_id': str(indicator.pk), 'data_point_id': str(point.pk),
            'trace_id': str(trace.pk) if trace else None, 'revision_id': str(revision_id),
            'revision_sequence': sequence, 'schema_version': SCHEMA_VERSION,
            'source_version': text(trace.version) if trace else None,
        },
        'indicator': {
            'code': indicator.code, 'name': indicator.name, 'short_name': text(indicator.short_name),
            'category': indicator.category, 'definition': text(indicator.description),
            'methodology': text(indicator.methodology), 'unit': text(indicator.unit),
            'data_type': indicator.data_type,
        },
        'observation': {
            'value': decimal_string(point.value), 'data_layer': point.data_layer,
            'period': {'type': point.period_type, 'year': point.period_year,
                       'quarter': point.period_quarter, 'month': point.period_month, 'label': point.period_label},
            'fetched_at': timestamp(point.fetched_at),
        },
        'source': {
            'institution_name': text(trace.institution_name) if trace else None,
            'institution_code': text(trace.institution_code) if trace else None,
            'publication_name': text(trace.publication_name) if trace else None,
            'publication_url': source_url,
            'release_date': trace.release_date.isoformat() if trace and trace.release_date else None,
            'fetched_at': timestamp(trace.fetched_at) if trace else None,
        },
        'data_origin': data_origin, 'change': None,
        'official_value': {
            'value': decimal_string(trace.official_value) if trace else None,
            'unit': text(trace.official_unit) if trace else None,
            'period': text(trace.official_period) if trace else None,
        },
        'calculation': None if indicator.data_type == 'official' else {
            'formula_id': None, 'formula_version': None,
            'expression': text(trace.formula_used) if trace else None, 'inputs': [],
        },
        'limitations': limitations,
    }
