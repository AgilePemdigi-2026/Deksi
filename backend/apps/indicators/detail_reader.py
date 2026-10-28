"""Public read projection over frozen, reviewed revisions, never mutable working rows."""
from contextlib import contextmanager
from copy import deepcopy
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Count, OuterRef, Subquery
from django.urls import reverse
from rest_framework.exceptions import APIException

from .models import SourceTraceRevision


class DetailProblem(APIException):
    def __init__(self, code='indicator_detail_unavailable', status=503):
        self.status_code = status
        self.public_code = code
        super().__init__('Data indikator belum dapat disajikan.')


@contextmanager
def consistent_read():
    # PostgreSQL count, selection and page rows must share one request snapshot.
    outer = connection.in_atomic_block
    with transaction.atomic():
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                if not outer:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                else:
                    cursor.execute('SHOW transaction_isolation')
                    if cursor.fetchone()[0] not in {'repeatable read', 'serializable'}:
                        raise DetailProblem()
        yield


def public_revisions():
    return SourceTraceRevision.objects.filter(
        publication_status='published', reviewed_by_id__isnull=False,
        reviewed_at__isnull=False, published_at__isnull=False,
    ).exclude(snapshot__data_origin='demo')


def latest_points(code):
    latest = public_revisions().filter(data_point_id=OuterRef('data_point_id')).order_by('-sequence').values('id')[:1]
    return public_revisions().filter(id=Subquery(latest), snapshot__indicator__code=code)


def series(code, period_type):
    query = latest_points(code)
    frequencies = list(query.order_by().values_list('snapshot__observation__period__type', flat=True).distinct()[:4])
    if not frequencies:
        raise DetailProblem('not_found', 404)
    if any(f not in {'annual', 'quarterly', 'monthly'} for f in frequencies):
        raise DetailProblem()
    if period_type is None:
        if len(frequencies) != 1:
            raise DetailProblem('series_selection_required', 400)
        period_type = frequencies[0]
    query = query.filter(snapshot__observation__period__type=period_type)
    contexts = list(query.order_by().values_list(
        'snapshot__identity__indicator_id', 'snapshot__indicator__unit', 'snapshot__indicator__data_type',
    ).distinct()[:2])
    if len(contexts) > 1:
        raise DetailProblem('inconsistent_series')
    period_keys = ['snapshot__observation__period__'+key for key in ['year', 'quarter', 'month']]
    if query.order_by().values(*period_keys).annotate(total=Count('id')).filter(total__gt=1).exists():
        raise DetailProblem('ambiguous_series')
    return query.order_by(*period_keys), period_type, contexts[0] if contexts else None


def validate_revision(revision):
    try:
        revision.validate_content()
    except (ValidationError, TypeError, ValueError, KeyError):
        raise DetailProblem() from None
    return revision


def links(revision, *, history_available=True):
    code = revision.snapshot['indicator']['code']
    return {
        'current': reverse('indicator-detail-current', kwargs={'code': code}),
        'revision': reverse('indicator-detail-revision', kwargs={
            'code': code, 'data_point_id': str(revision.data_point_id), 'revision_id': str(revision.pk),
        }),
        'history': reverse('indicator-detail-history', kwargs={'code': code})+'?period_type='+revision.snapshot['observation']['period']['type'] if history_available else None,
        # F7 backend is not implemented here. Never advertise a proposed endpoint as live.
        'source_trace': None,
    }


def detail_projection(revision, *, history_available=True):
    validate_revision(revision)
    snapshot = revision.snapshot
    public = {k: deepcopy(snapshot[k]) for k in ['identity', 'indicator', 'observation', 'source', 'data_origin', 'change']}
    missing = []
    for section, fields in {
        'indicator': ['definition', 'methodology', 'unit'],
        'observation': ['value', 'fetched_at'],
        'source': ['institution_name', 'institution_code', 'publication_name', 'publication_url', 'release_date', 'fetched_at'],
    }.items():
        missing.extend('snapshot.'+section+'.'+field for field in fields if snapshot[section][field] is None)
    if snapshot['identity']['source_version'] is None:
        missing.append('snapshot.identity.source_version')
    warnings = ['change_evidence_unavailable', 'source_trace_endpoint_unavailable'] + snapshot['limitations']
    if snapshot['data_origin'] == 'unknown':
        warnings.append('data_origin_unknown')
    if not history_available:
        warnings.append('history_context_changed')
    return {
        'snapshot': public,
        'publication': {'status': 'published', 'published_at': revision.published_at.isoformat()},
        'metadata': {'status': 'partial' if missing else 'complete', 'missing_fields': missing,
                     'warnings': warnings, 'verification_status': 'unassessed'},
        'links': links(revision, history_available=history_available),
    }


def current_detail(code, period_type=None):
    query, _, _ = series(code, period_type)
    revision = query.reverse().first()
    if revision is None:
        raise DetailProblem('not_found', 404)
    return detail_projection(revision)


def pinned_detail(code, point_id, revision_id):
    try:
        point_id, revision_id = UUID(point_id), UUID(revision_id)
    except (ValueError, TypeError, AttributeError):
        raise DetailProblem('not_found', 404) from None
    revision = public_revisions().filter(pk=revision_id, data_point_id=point_id, snapshot__indicator__code=code).first()
    if revision is None:
        raise DetailProblem('not_found', 404)
    validate_revision(revision)
    frozen = revision.snapshot
    try:
        _, _, context = series(code, frozen['observation']['period']['type'])
        expected = (frozen['identity']['indicator_id'], frozen['indicator']['unit'], frozen['indicator']['data_type'])
        available = context == expected
    except DetailProblem:
        available = False
    return detail_projection(revision, history_available=available)


def history(code, period_type, page):
    query, frequency, context = series(code, period_type)
    count = query.count()
    if page > max(1, (count + 19) // 20):
        raise DetailProblem('not_found', 404)
    rows = list(query[(page-1)*20:page*20])
    for row in rows:
        validate_revision(row)
    def page_link(number):
        return reverse('indicator-detail-history', kwargs={'code': code})+f'?period_type={frequency}&page={number}'
    return {
        'series': {'indicator_id': context[0] if context else None, 'code': code,
                   'unit': context[1] if context else None, 'data_type': context[2] if context else None, 'period_type': frequency},
        'view': 'current_published_per_observation', 'gap_policy': 'break_on_null_or_missing_period',
        'count': count, 'next': page_link(page+1) if page*20 < count else None,
        'previous': page_link(page-1) if page > 1 else None,
        'results': [{
            'identity': {k: row.snapshot['identity'][k] for k in ['indicator_id', 'data_point_id', 'revision_id', 'revision_sequence']},
            'period': deepcopy(row.snapshot['observation']['period']),
            'value': row.snapshot['observation']['value'], 'unit': row.snapshot['indicator']['unit'],
            'data_type': row.snapshot['indicator']['data_type'], 'data_layer': row.snapshot['observation']['data_layer'],
            'links': {k: v for k, v in links(row).items() if k in {'revision', 'source_trace'}},
        } for row in rows],
    }
