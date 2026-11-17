"""Authenticated source-bound candidate listing and explicit human review."""
import hmac

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from indicators.lifecycle import require_reviewer, review_candidate
from indicators.models import Indicator, ObservationCandidate, Source
from indicators.source_admin_views import _parse_json_body, _require_staff
from indicators.views import json_error


def _authorize(request):
    denied = _require_staff(request)
    if denied is not None:
        return denied
    try:
        require_reviewer(request.user)
    except (PermissionDenied, get_user_model().DoesNotExist):
        return json_error('Izin review kandidat diperlukan.', status=403)
    return None


def _serialize(candidate):
    payload = candidate.payload
    previous = candidate.base_snapshot.get('observation') or {}
    indicator = candidate.base_snapshot.get('indicator')
    indicator = indicator if isinstance(indicator, dict) else {}
    source = candidate.base_snapshot.get('source')
    source = source if isinstance(source, dict) else {}
    raw = candidate.base_snapshot.get('candidate_raw')
    evidence = None if not isinstance(raw, dict) else {
        'documentName': raw.get('document_name'), 'periodLabel': raw.get('period_label'),
        'retrievedAt': raw.get('retrieved_at'), 'checksumSha256': raw.get('checksum_sha256'),
    }
    return {
        'id': candidate.pk, 'fingerprint': candidate.fingerprint,
        'indicator': indicator.get('code'), 'indicatorName': indicator.get('name'),
        'sourceId': candidate.source.source_id, 'sourceName': source.get('source_name'),
        'sourceUrl': source.get('primary_url'),
        'period': payload.get('period_label'), 'observationDate': payload.get('observation_date'),
        'publicationDate': payload.get('publication_date'), 'frequency': payload.get('frequency'),
        'dataType': payload.get('data_type'), 'value': payload.get('value'), 'unit': payload.get('unit'),
        'rawFileId': payload.get('raw_file_id'), 'rawEvidence': evidence, 'status': candidate.status,
        'previousValue': previous.get('value'), 'previousUnit': previous.get('unit'),
        'previousPeriod': previous.get('period_label'),
        'createdAt': candidate.created_at.isoformat(),
        'reviewedAt': candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
        'reviewedBy': candidate.reviewed_by.get_username() if candidate.reviewed_by else None,
        'reviewNotes': candidate.review_notes,
    }


@require_GET
def candidate_list(request, source_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    if not Source.objects.filter(source_id=source_id).exists():
        return json_error('Sumber tidak ditemukan.', status=404)
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1 or page > 100000:
            raise ValueError
    except ValueError:
        return json_error('Halaman tidak valid.', status=400)
    status = request.GET.get('status', 'pending')
    if status not in {'pending', 'published', 'rejected'}:
        return json_error('Status tidak valid.', status=400)
    query = ObservationCandidate.objects.filter(source__source_id=source_id, status=status).select_related(
        'indicator', 'source', 'reviewed_by').order_by('-created_at', '-id')
    total = query.count()
    size = 20
    items = [_serialize(c) for c in query[(page - 1) * size:page * size]]
    response = JsonResponse({'items': items, 'page': page, 'pageSize': size, 'total': total,
                             'hasNext': page * size < total})
    response['Cache-Control'] = 'no-store'
    return response


@require_GET
def analysis_result_list(request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1 or page > 100000:
            raise ValueError
    except ValueError:
        return json_error('Halaman tidak valid.', status=400)
    status = request.GET.get('status', 'all')
    if status not in {'all', 'pending', 'published', 'rejected'}:
        return json_error('Status tidak valid.', status=400)
    query = ObservationCandidate.objects.select_related('indicator', 'source', 'reviewed_by')
    if status != 'all':
        query = query.filter(status=status)
    query = query.order_by('-created_at', '-id')
    total = query.count()
    size = 20
    items = [_serialize(candidate) for candidate in query[(page - 1) * size:page * size]]
    response = JsonResponse({'items': items, 'page': page, 'pageSize': size, 'total': total,
                             'hasNext': page * size < total})
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def candidate_review(request, source_id, candidate_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    data, error = _parse_json_body(request)
    if error or data is None or set(data) != {'decision', 'fingerprint', 'notes'}:
        return json_error('Permintaan review tidak valid.', status=400)
    decision, fingerprint, notes = data['decision'], data['fingerprint'], data['notes']
    if (decision not in ('publish', 'reject') or not isinstance(fingerprint, str) or len(fingerprint) != 64
            or not fingerprint.isascii() or not isinstance(notes, str) or len(notes) > 500
            or (decision == 'reject' and not notes.strip())):
        return json_error('Keputusan, identitas, atau alasan tidak valid.', status=400)
    try:
        with transaction.atomic():
            candidate = ObservationCandidate.objects.select_for_update(of=("self",)).select_related('source').filter(
                pk=candidate_id, source__source_id=source_id).first()
            if candidate is None:
                return json_error('Kandidat tidak ditemukan.', status=404)
            if candidate.status != 'pending' or not hmac.compare_digest(candidate.fingerprint, fingerprint):
                return json_error('Kandidat berubah atau telah direview. Muat ulang.', status=409)
            # Match staging's indicator -> source lock order; recheck the route binding
            # while source_id is locked so the initial joined filter cannot go stale.
            Indicator.objects.select_for_update().get(pk=candidate.indicator_id)
            if not Source.objects.select_for_update().filter(
                    pk=candidate.source_id, source_id=source_id).exists():
                return json_error('Kandidat tidak ditemukan.', status=404)
            review_candidate(candidate.pk, request.user, publish=decision == 'publish', notes=notes.strip())
    except PermissionDenied:
        return json_error('Izin review kandidat diperlukan.', status=403)
    except ValidationError:
        return json_error('Kandidat tidak dapat direview; periksa perubahan atau validasi data.', status=409)
    response = JsonResponse({'id': candidate_id, 'status': 'published' if decision == 'publish' else 'rejected'})
    response['Cache-Control'] = 'no-store'
    return response


@require_GET
def candidate_detail(request, source_id, candidate_id):
    denied = _authorize(request)
    if denied is not None:
        return denied
    candidate = ObservationCandidate.objects.select_related('indicator', 'source', 'reviewed_by').filter(
        pk=candidate_id, source__source_id=source_id).first()
    if candidate is None:
        return json_error('Kandidat tidak ditemukan.', status=404)
    response = JsonResponse({'candidate': _serialize(candidate)})
    response['Cache-Control'] = 'no-store'
    return response
