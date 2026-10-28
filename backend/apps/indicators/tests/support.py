from decimal import Decimal

from apps.accounts.models import AdminUser
from apps.indicators.models import EconomicIndicator, IndicatorDataPoint, SourceTrace, SourceTraceRevision


def working_trace(data_type='official'):
    indicator = EconomicIndicator.objects.create(
        code='synthetic_pdb', name='Synthetic test indicator', short_name='TEST',
        category='pdb', data_type=data_type, unit='percent',
    )
    point = IndicatorDataPoint.objects.create(
        indicator=indicator, period_type='quarterly', period_year=2026, period_quarter=1,
        period_label='Synthetic Q1', value=Decimal('5.0500'),
        data_layer='derived' if data_type == 'derived' else 'clean', publication_status='published',
    )
    return SourceTrace.objects.create(data_point=point, institution_name='Synthetic test institution')


def reviewer():
    return AdminUser.objects.create_superuser(email='reviewer@example.invalid', full_name='Synthetic reviewer')


def revision_candidate(trace):
    point, indicator = trace.data_point, trace.data_point.indicator
    rev = SourceTraceRevision(source_trace=trace, data_point=point, indicator=indicator, sequence=1)
    rev.snapshot = {
        'identity': {'indicator_id': str(indicator.id), 'data_point_id': str(point.id),
                     'trace_id': str(trace.id), 'revision_id': str(rev.id), 'revision_sequence': 1,
                     'schema_version': 1, 'source_version': None},
        'indicator': {'code': indicator.code, 'name': indicator.name, 'unit': indicator.unit, 'data_type': indicator.data_type},
        'observation': {'value': '5.0500', 'data_layer': 'clean',
                        'period': {'type': 'quarterly', 'year': 2026, 'quarter': 1, 'month': None, 'label': 'Synthetic Q1'}},
        'source': {'institution_name': trace.institution_name, 'institution_code': None,
                   'publication_name': None, 'publication_url': None, 'release_date': None, 'fetched_at': None},
        'official_value': {'value': None, 'unit': None, 'period': None},
        'calculation': None, 'data_origin': 'demo',
    }
    rev.content_sha256 = '0' * 64
    return rev


def stored_revision(trace):
    rev = revision_candidate(trace)
    rev.save()
    return rev
