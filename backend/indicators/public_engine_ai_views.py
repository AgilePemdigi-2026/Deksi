"""Public request intake/read and staff-only human review."""
import json
import re

from django.core.exceptions import PermissionDenied, RequestDataTooBig
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from indicators.public_engine_ai import PublicEngineAIError, _review_digest, create_request, review_request, serialize_public
from indicators.models import PublicEngineAIRequest


def _json(data, status=200):
    response = JsonResponse(data, status=status)
    response.content = response.content.replace(b'<', b'\\u003c').replace(b'>', b'\\u003e').replace(b'&', b'\\u0026')
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _read_body(request, expected):
    try:
        raw_length = request.META.get('CONTENT_LENGTH', '')
        if request.content_type != 'application/json' or not raw_length.isdigit() or int(raw_length) > 4096:
            raise ValueError
        raw = request.body
        if len(raw) > 4096:
            raise ValueError
        body = json.loads(raw)
        if type(body) is not dict or set(body) != expected:
            raise ValueError
        return body
    except (ValueError, TypeError, UnicodeError, RequestDataTooBig):
        raise PublicEngineAIError('invalid_request') from None


@require_POST
def public_request(request):
    try:
        body = _read_body(request, {'requestKey', 'quarter'})
        row, created = create_request(body['requestKey'], body['quarter'])
        return _json({'request': {'requestKey': str(row.request_key), 'status': row.status,
                                  'period': row.snapshot['period'], 'resultDigest': row.result_digest}},
                     202 if created else 200)
    except PublicEngineAIError as error:
        return _json({'code': error.code, 'error': 'Permintaan engine AI tidak dapat diproses.'}, error.status)


@require_GET
def public_result(request, request_key):
    if set(request.GET):
        return _json({'code': 'invalid_request'}, 400)
    try:
        key = str(request_key)
        if not re.fullmatch(r'[0-9a-f-]{36}', key):
            raise ValueError
        row = PublicEngineAIRequest.objects.filter(request_key=key).first()
        if not row:
            return _json({'code': 'not_found'}, 404)
        return _json({'request': serialize_public(row)})
    except (ValueError, TypeError):
        return _json({'code': 'invalid_request'}, 400)


@require_GET
def admin_queue(request):
    user = request.user
    if not (user.is_authenticated and user.is_active and user.is_staff
            and user.has_perm('indicators.review_publicengineairequest')):
        return _json({'code': 'forbidden'}, 403)
    rows = PublicEngineAIRequest.objects.filter(status=PublicEngineAIRequest.Status.READY).order_by('id')[:100]
    items = []
    from indicators.public_engine_ai import calculate_snapshot
    for row in rows:
        try:
            fresh = calculate_snapshot(row.period_end.isoformat())
        except (PublicEngineAIError, ValueError, TypeError):
            continue
        if fresh['inputDigest'] != row.input_digest or fresh['resultDigest'] != row.result_digest:
            continue
        items.append({'id': row.pk, 'period': row.snapshot['period'], 'resultDigest': row.result_digest,
                      'contentDigest': _review_digest(row), 'snapshot': row.snapshot, 'narrative': row.narrative})
    return _json({'items': items})


@require_POST
def admin_review(request, request_id):
    user = request.user
    if not (user.is_authenticated and user.is_active and user.is_staff
            and user.has_perm('indicators.review_publicengineairequest')):
        return _json({'code': 'forbidden'}, 403)
    try:
        body = _read_body(request, {'contentDigest', 'decision', 'notes'})
        row = review_request(user, request_id, result_digest=body['contentDigest'],
                             decision=body['decision'], notes=body['notes'])
        return _json({'id': row.pk, 'status': row.status, 'resultDigest': row.approved_result_digest,
                      'contentDigest': row.approved_content_digest})
    except PermissionDenied:
        return _json({'code': 'forbidden'}, 403)
    except PublicEngineAIError as error:
        return _json({'code': error.code}, error.status)
