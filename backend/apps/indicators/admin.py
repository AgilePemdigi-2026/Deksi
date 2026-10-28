from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from .models import DataSource, EconomicIndicator, IndicatorDataPoint, SourceTrace, DiagnosticFlag, SourceTraceRevision
from .source_trace import capture_revision, review_revision


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
    actions = ['capture_draft']

    @admin.action(description='Buat snapshot draft (belum dipublikasikan)', permissions=['change'])
    def capture_draft(self, request, queryset):
        for trace in queryset:
            try:
                revision = capture_revision(trace.id)
                self.log_addition(request, revision, 'Created an unreviewed source trace snapshot.')
                self.message_user(request, f'Draft revisi {revision.sequence} dibuat; review terpisah diperlukan.', messages.SUCCESS)
            except ValidationError:
                self.message_user(request, 'Snapshot tidak dibuat: periksa data dan hubungan observasi.', messages.ERROR)


@admin.register(DiagnosticFlag)
class DiagnosticFlagAdmin(admin.ModelAdmin):
    list_display = ('flag_code', 'severity', 'data_point', 'created_at')
    list_filter = ('severity',)
    search_fields = ('flag_code', 'message')
    readonly_fields = ('id', 'created_at')


@admin.register(SourceTraceRevision)
class SourceTraceRevisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_trace', 'sequence', 'publication_status', 'created_at')
    list_filter = ('publication_status',)
    readonly_fields = tuple(field.name for field in SourceTraceRevision._meta.fields)
    actions = ['publish_selected', 'reject_selected']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_publish_permission(self, request):
        return request.user.is_active and request.user.is_staff and request.user.has_perm('indicators.publish_sourcetracerevision')

    def _review(self, request, queryset, decision):
        for revision in queryset:
            try:
                reviewed = review_revision(revision.id, request.user, decision, expected_digest=revision.content_sha256)
                self.log_change(request, reviewed, f'Review decision: {decision}; content SHA256: {reviewed.content_sha256}')
                self.message_user(request, f'Revisi {revision.sequence}: {decision}.', messages.SUCCESS)
            except (PermissionDenied, ValidationError):
                self.message_user(request, 'Review ditolak: izin, integritas konten, atau status draft tidak sesuai.', messages.ERROR)

    @admin.action(description='Publikasikan revisi yang telah saya tinjau', permissions=['publish'])
    def publish_selected(self, request, queryset):
        self._review(request, queryset, 'published')

    @admin.action(description='Tolak revisi yang telah saya tinjau', permissions=['publish'])
    def reject_selected(self, request, queryset):
        self._review(request, queryset, 'rejected')
