"""Feature-6 public GET endpoints. Global accounts authentication is unchanged."""
import logging
import re

from django.db import DatabaseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .detail_reader import DetailProblem, consistent_read, current_detail, history, pinned_detail

logger = logging.getLogger(__name__)


class IndicatorDetailRead(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ['get', 'head', 'options']
    kind = 'current'

    def get(self, request, code, **kwargs):
        allowed = {'current': {'period_type'}, 'history': {'period_type', 'page'}, 'revision': set()}[self.kind]
        query = request.query_params
        if any(key not in allowed or len(query.getlist(key)) != 1 for key in query):
            raise DetailProblem('invalid_request', 400)
        frequency = query.get('period_type')
        if frequency is not None and frequency not in {'annual', 'quarterly', 'monthly'}:
            raise DetailProblem('invalid_request', 400)
        page = query.get('page', '1')
        if not re.fullmatch(r'[1-9][0-9]{0,8}', page):
            raise DetailProblem('invalid_request', 400)
        if len(code) > 50:
            raise DetailProblem('not_found', 404)
        try:
            with consistent_read():
                if self.kind == 'current':
                    data = current_detail(code, frequency)
                elif self.kind == 'history':
                    data = history(code, frequency, int(page))
                else:
                    data = pinned_detail(code, kwargs['data_point_id'], kwargs['revision_id'])
        except DatabaseError:
            logger.error('Indicator detail storage read failed.')
            raise DetailProblem() from None
        return Response({'success': True, 'message': 'Data indikator publik.', 'data': data})

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        codes = {400: 'invalid_request', 404: 'not_found', 405: 'method_not_allowed', 429: 'throttled', 503: 'indicator_detail_unavailable'}
        response.data = {
            'success': False, 'message': 'Data indikator tidak ditemukan.' if response.status_code == 404 else 'Permintaan belum dapat dipenuhi.',
            'data': None, 'error': {'code': exc.public_code if isinstance(exc, DetailProblem) else codes.get(response.status_code, 'request_failed')},
        }
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response
