"""Session/CSRF protected narrative-only endpoints; no public publication path."""
import re
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, RequestDataTooBig
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from indicators import ai_narrative as service
from indicators.ai_narrative_policy import NarrativeError
from indicators.ai_narrative_provider import strict_json
from indicators.models import AINarrativeDraft, Indicator
from indicators.source_admin_views import _require_staff
from indicators.views import published_observations


def _json(body, status=200):
    response = JsonResponse(body, status=status)
    response['Cache-Control'] = 'no-store'
    return response


def _guard(permission=None, *, capabilities_only=False):
    def decorate(view):
        @wraps(view)
        def call(request, *args, **kwargs):
            denied = _require_staff(request)
            if denied is not None:
                return denied
            try:
                if not capabilities_only:
                    service.authorize(request.user, permission)
                return view(request, *args, **kwargs)
            except (PermissionDenied, ObjectDoesNotExist):
                return _json({'code': 'forbidden', 'error': 'Izin narasi Admin diperlukan.'}, 403)
            except NarrativeError as error:
                return _json({'code': error.code, 'error': str(error)}, error.status)
        return call
    return decorate


def _body(request, names):
    try:
        if request.content_type != 'application/json' or int(request.META.get('CONTENT_LENGTH') or 0) > 8192:
            raise ValueError
        raw = request.body
        if len(raw) > 8192:
            raise ValueError
        body = strict_json(raw.decode('utf-8'))
        if type(body) is not dict or set(body) != names:
            raise ValueError
        return body
    except (ValueError, TypeError, UnicodeError, RecursionError, RequestDataTooBig):
        raise NarrativeError('invalid_request', 400) from None


def _page(request, allowed=None):
    names = {'page'} if allowed is None else allowed
    if set(request.GET) - names or any(len(values) != 1 for _name, values in request.GET.lists()):
        raise NarrativeError('invalid_request', 400)
    text = request.GET.get('page', '1')
    if not re.fullmatch(r'[1-9][0-9]{0,5}', text):
        raise NarrativeError('invalid_request', 400)
    return int(text)


def _paginated(query, page, serializer):
    total = query.count()
    return {'items': [serializer(row) for row in query[(page - 1) * 20:page * 20]],
            'page': page, 'pageSize': 20, 'total': total, 'hasNext': page * 20 < total}


@require_GET
@_guard(capabilities_only=True)
def capabilities(request):
    return _json(service.capabilities(request.user))


@require_GET
@_guard()
def observations(request):
    page = _page(request)
    indicator = Indicator.objects.filter(code='pdb').first()
    if indicator is None:
        return _json({'items': [], 'page': page, 'pageSize': 20, 'total': 0, 'hasNext': False})
    query = published_observations(indicator).filter(
        source__source_id='BPS', unit='%', frequency='quarterly', data_type='yoy').order_by('-observation_date', '-id')
    return _json(_paginated(query, page, lambda row: {
        'id': row.pk, 'value': format(row.value, '.6f'), 'unit': row.unit,
        'period': row.period_label, 'observationDate': row.observation_date.isoformat(),
        'publicationDate': row.publication_date.isoformat() if row.publication_date else None}))


@require_http_methods(['GET', 'POST'])
@_guard()
def collection(request):
    if request.method == 'GET':
        return _json(_paginated(AINarrativeDraft.objects.select_related('review').order_by('-id'),
                                _page(request), service.serialize_draft))
    body = _body(request, {'requestKey', 'observationId', 'comparisonId', 'parentId'})
    existed = AINarrativeDraft.objects.filter(request_key=service._request_key(body['requestKey'])).exists()
    draft = service.request_draft(request.user, request_key=body['requestKey'], observation_id=body['observationId'],
                                  comparison_id=body['comparisonId'], parent_id=body['parentId'])
    return _json({'draft': service.serialize_draft(draft)}, 200 if existed else 202)


@require_GET
@_guard()
def lookup(request):
    _page(request, {'requestKey'})
    key = service._request_key(request.GET.get('requestKey'))
    draft = AINarrativeDraft.objects.select_related('review').filter(request_key=key, created_by=request.user).first()
    return _json({'draft': None if draft is None else service.serialize_draft(draft)})


@require_GET
@_guard()
def detail(request, draft_id):
    _page(request, set())
    draft = AINarrativeDraft.objects.select_related('review').filter(pk=draft_id).first()
    if draft is None:
        return _json({'code': 'not_found', 'error': 'Draft tidak ditemukan.'}, 404)
    return _json({'draft': service.serialize_draft(draft)})


@require_POST
@_guard(service.REVIEW_PERMISSION)
def review(request, draft_id):
    body = _body(request, {'contentDigest', 'decision', 'notes'})
    draft = service.review_draft(request.user, draft_id, content_digest=body['contentDigest'],
                                  decision=body['decision'], notes=body['notes'])
    return _json({'draft': service.serialize_draft(draft)})


@require_POST
@_guard(service.GENERATE_PERMISSION)
def reconcile(request, draft_id):
    body = _body(request, {'acknowledged', 'notes'})
    draft = service.reconcile_draft(request.user, draft_id, acknowledged=body['acknowledged'], notes=body['notes'])
    return _json({'draft': service.serialize_draft(draft)})
