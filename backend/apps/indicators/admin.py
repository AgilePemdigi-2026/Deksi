from django.contrib import admin
from .models import DataSource, EconomicIndicator, IndicatorDataPoint, SourceTrace, DiagnosticFlag


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'acquisition_method', 'is_active', 'last_fetch_status', 'last_fetched_at')
    list_filter = ('acquisition_method', 'is_active', 'last_fetch_status')
    search_fields = ('name', 'code')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(EconomicIndicator)
class EconomicIndicatorAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'data_type', 'unit', 'is_active', 'display_order')
    list_filter = ('category', 'data_type', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('display_order',)


@admin.register(IndicatorDataPoint)
class IndicatorDataPointAdmin(admin.ModelAdmin):
    list_display = ('indicator', 'period_label', 'value', 'data_layer', 'publication_status', 'trend_direction')
    list_filter = ('data_layer', 'publication_status', 'period_type', 'indicator__category')
    search_fields = ('indicator__code', 'indicator__name', 'period_label')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(SourceTrace)
class SourceTraceAdmin(admin.ModelAdmin):
    list_display = ('data_point', 'institution_name', 'release_date', 'is_metadata_complete')
    list_filter = ('is_metadata_complete',)
    search_fields = ('institution_name', 'data_point__indicator__code')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(DiagnosticFlag)
class DiagnosticFlagAdmin(admin.ModelAdmin):
    list_display = ('flag_code', 'severity', 'data_point', 'created_at')
    list_filter = ('severity',)
    search_fields = ('flag_code', 'message')
    readonly_fields = ('id', 'created_at')
