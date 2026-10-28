from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import DataSource, EconomicIndicator, IndicatorDataPoint, SourceTrace, DiagnosticFlag, SourceTraceRevision


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


@admin.register(SourceTraceRevision)
class SourceTraceRevisionAdmin(admin.ModelAdmin):
    """Review frozen contents; creation is an explicit capture service operation."""

    list_display = ('id', 'data_point_id', 'sequence', 'publication_status', 'published_at')
    list_filter = ('publication_status',)
    readonly_fields = tuple(field.name for field in SourceTraceRevision._meta.fields)
    actions = ['submit_for_review', 'publish_selected', 'withdraw_selected']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        user = request.user
        if not user.is_active or not user.is_staff or not (user.is_superuser or user.role in {'reviewer', 'superadmin'}):
            return {}
        return super().get_actions(request)

    @admin.action(description='Submit selected draft revisions for review', permissions=['view'])
    def submit_for_review(self, request, queryset):
        from .revisions import submit_revision
        self._apply(request, queryset, submit_revision)

    @admin.action(description='Publish selected reviewed contents', permissions=['view'])
    def publish_selected(self, request, queryset):
        from .revisions import publish_revision
        self._apply(request, queryset, publish_revision)

    @admin.action(description='Withdraw selected published revisions', permissions=['view'])
    def withdraw_selected(self, request, queryset):
        from .revisions import withdraw_revision
        self._apply(request, queryset, withdraw_revision)

    def _apply(self, request, queryset, operation):
        try:
            with transaction.atomic():
                count = 0
                for revision in queryset.order_by('pk'):
                    operation(revision.pk, request.user)
                    count += 1
        except ValidationError:
            self.message_user(request, 'Status atau konten pilihan tidak sesuai. Tidak ada revisi yang diubah.', level=messages.ERROR)
        else:
            self.message_user(request, f'{count} revisi diproses.', level=messages.SUCCESS)
