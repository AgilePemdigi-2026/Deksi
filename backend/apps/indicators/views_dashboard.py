import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EconomicIndicator, IndicatorCategory
from .serializers import DashboardCardSerializer

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """
    UC-02: Dashboard Indikator Ekonomi.
    GET /api/v1/indicators/dashboard/

    Query params:
      ?category=pdb|inflasi|fiskal|moneter|investasi|tenaga_kerja
      ?year=2024
      ?period_type=annual|quarterly|monthly

    Public – tidak perlu login.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Ambil semua indikator aktif
        qs = (
            EconomicIndicator.objects
            .filter(is_active=True)
            .select_related('source')
            .prefetch_related('data_points', 'data_points__diagnostic_flags')
            .order_by('display_order', 'category')
        )

        # ── Filter kategori ───────────────────────────────────────────────
        category = request.query_params.get('category', '').strip().lower()
        if category:
            valid = [c.value for c in IndicatorCategory]
            if category not in valid:
                return Response(
                    {'success': False,
                     'message': f'Kategori tidak valid. Pilihan: {", ".join(valid)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            qs = qs.filter(category=category)

        # ── Filter tahun ──────────────────────────────────────────────────
        year = request.query_params.get('year', '').strip()
        if year and not year.isdigit():
            return Response(
                {'success': False, 'message': 'Parameter year harus berupa angka.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DashboardCardSerializer(
            qs, many=True,
            context={
                'request': request,
                'filter_year': int(year) if year else None,
            }
        )
        data = serializer.data

        # Statistik ringkas
        has_data      = any(card.get('latest_data') for card in data)
        total_with_data = sum(1 for c in data if c.get('latest_data'))

        # Ringkasan per kategori
        cat_summary = {}
        for card in data:
            cat       = card['category']
            cat_label = card['category_display']
            cat_summary.setdefault(cat, {'label': cat_label, 'count': 0, 'has_data': False})
            cat_summary[cat]['count'] += 1
            if card.get('latest_data'):
                cat_summary[cat]['has_data'] = True

        # Filter aktif yang diterapkan
        active_filters = {}
        if category: active_filters['category'] = category
        if year:     active_filters['year']     = int(year)

        return Response({
            'success': True,
            'message': None if has_data else 'Belum ada data yang dipublikasikan.',
            'meta': {
                'total_indicators': len(data),
                'indicators_with_data': total_with_data,
                'has_published_data': has_data,
                'active_filters': active_filters,
                'categories': list(cat_summary.values()),
                'generated_at': timezone.now().isoformat(),
            },
            'data': data,
        }, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    """
    Daftar kategori + jumlah indikator.
    GET /api/v1/indicators/categories/
    Public.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        categories = []
        for code, label in IndicatorCategory.choices:
            count = EconomicIndicator.objects.filter(category=code, is_active=True).count()
            categories.append({'code': code, 'label': label, 'indicator_count': count})
        return Response({'success': True, 'data': categories})
