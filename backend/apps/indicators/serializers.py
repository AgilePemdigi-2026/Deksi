from rest_framework import serializers
from .models import EconomicIndicator, IndicatorDataPoint, SourceTrace, DiagnosticFlag


class DiagnosticFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticFlag
        fields = ['id', 'flag_code', 'severity', 'message', 'created_at']


class DashboardCardSerializer(serializers.ModelSerializer):
    """Kartu ringkasan per indikator untuk Dashboard (UC-02)."""
    category_display  = serializers.CharField(source='get_category_display', read_only=True)
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    source_name       = serializers.CharField(source='source.name', read_only=True, default=None)
    latest_data       = serializers.SerializerMethodField()

    class Meta:
        model = EconomicIndicator
        fields = [
            'id', 'code', 'name', 'short_name',
            'category', 'category_display',
            'data_type', 'data_type_display',
            'unit', 'source_name', 'latest_data',
        ]

    def get_latest_data(self, obj):
        year_filter = self.context.get('filter_year')
        qs = obj.data_points.filter(
            publication_status='published',
            data_layer__in=['clean', 'derived'],
        )
        if year_filter:
            qs = qs.filter(period_year=year_filter)
        latest = qs.order_by('-period_year', '-period_quarter', '-period_month').first()
        if not latest:
            return None
        flags = DiagnosticFlagSerializer(latest.diagnostic_flags.all(), many=True).data
        return {
            'id': str(latest.id),
            'period_label': latest.period_label,
            'value': str(latest.value) if latest.value is not None else None,
            'unit': obj.unit,
            'trend_value': str(latest.trend_value) if latest.trend_value is not None else None,
            'trend_percent': str(latest.trend_percent) if latest.trend_percent is not None else None,
            'trend_direction': latest.trend_direction,
            'fetched_at': latest.fetched_at,
            'published_at': latest.published_at,
            'diagnostic_flags': flags,
        }


class TimeSeriesSerializer(serializers.ModelSerializer):
    """Satu titik data untuk grafik tren."""
    class Meta:
        model = IndicatorDataPoint
        fields = [
            'period_label', 'period_year', 'period_quarter',
            'period_month', 'value', 'trend_percent', 'trend_direction',
        ]


class SourceTraceSerializer(serializers.ModelSerializer):
    """UC-04: Provenance lengkap suatu data point."""
    indicator_code   = serializers.CharField(source='data_point.indicator.code', read_only=True)
    indicator_name   = serializers.CharField(source='data_point.indicator.name', read_only=True)
    period_label     = serializers.CharField(source='data_point.period_label', read_only=True)
    data_type        = serializers.CharField(source='data_point.indicator.data_type', read_only=True)
    data_type_display = serializers.CharField(
        source='data_point.indicator.get_data_type_display', read_only=True
    )

    class Meta:
        model = SourceTrace
        fields = [
            'id', 'indicator_code', 'indicator_name', 'period_label',
            'data_type', 'data_type_display',
            'institution_name', 'institution_code',
            'publication_name', 'publication_url', 'release_date',
            'official_value', 'official_unit', 'official_period',
            'formula_used', 'formula_inputs_detail',
            'is_metadata_complete', 'incomplete_fields',
            'fetched_at', 'version',
        ]
