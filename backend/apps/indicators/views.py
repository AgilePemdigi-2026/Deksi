from uuid import UUID
import re

from django.core.exceptions import ValidationError as SnapshotValidationError
from django.db import DatabaseError
from django.db.models import Count, Window
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SourceTraceSerializer
from .source_trace import fail, public_revisions


class SourceTraceView(APIView):
    kind = 'current'
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ['get', 'head', 'options']

    def handle_exception(self, exc):
        if isinstance(exc, (SnapshotValidationError, DatabaseError)):
            return Response({'success': False, 'message': 'Source Trace sementara tidak tersedia.',
                             'data': None, 'error': {'code': 'source_trace_unavailable'}}, status=503)
        response = super().handle_exception(exc)
        codes = {400: 'invalid_request', 404: 'not_found', 405: 'method_not_allowed', 429: 'throttled'}
        response.data = {'success': False, 'message': 'Permintaan tidak dapat dipenuhi.',
                         'data': None, 'error': {'code': codes.get(response.status_code, 'request_failed')}}
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response

    def get(self, request, code, data_point_id, revision_id=None, invalid_path=None):
        if self.kind == 'not_found':
            raise NotFound()
        try:
            point_id = UUID(data_point_id)
            if str(point_id) != data_point_id:
                raise ValueError
            if revision_id is not None and str(UUID(revision_id)) != revision_id:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise NotFound()
        allowed = {'page'} if self.kind == 'history' else set()
        if any(key not in allowed or len(values) != 1 for key, values in request.query_params.lists()):
            raise ValidationError('Unsupported or duplicate query parameters.')
        revisions = public_revisions().filter(data_point_id=point_id, snapshot__indicator__code=code)
        if self.kind != 'revision' and revisions.order_by().values('source_trace_id').distinct().count() > 1:
            fail()
        if self.kind == 'history':
            page_text = request.query_params.get('page', '1')
            if not re.fullmatch(r'[0-9]{1,9}', page_text) or int(page_text) < 1:
                raise ValidationError('Invalid page.')
            page = int(page_text)
            # Count and page share one PostgreSQL statement snapshot, including concurrent publication.
            rows = list(revisions.annotate(total_count=Window(Count('pk')))[(page - 1) * 20:page * 20])
            if not rows:
                raise NotFound()
            results = []
            for row in rows:
                detail = SourceTraceSerializer(row).data
                results.append({'revision_id': str(row.id), 'revision_sequence': row.sequence,
                                'source_version': detail['snapshot']['identity']['source_version'],
                                'published_at': detail['publication']['published_at'], 'url': detail['links']['revision']})
            count = rows[0].total_count
            data = {'count': count, 'next': f'{request.path}?page={page + 1}' if page * 20 < count else None,
                    'previous': f'{request.path}?page={page - 1}' if page > 1 else None, 'results': results}
            return Response({'success': True, 'message': 'Riwayat revisi tersedia.', 'data': data})
        if self.kind == 'revision':
            revisions = revisions.filter(pk=revision_id)
        revision = revisions.first()
        if revision is None:
            raise NotFound()
        return Response({'success': True, 'message': 'Source Trace tersedia.',
                         'data': SourceTraceSerializer(revision).data})
