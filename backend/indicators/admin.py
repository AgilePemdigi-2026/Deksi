from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from indicators.lifecycle import review_candidate
from indicators.models import DataUpdateLog, Indicator, Observation, ObservationCandidate, RawFile, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("source_id", "source_name", "institution", "primary_url")
    search_fields = ("source_id", "source_name", "institution")


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "unit", "aggregation_kind", "sort_order")
    search_fields = ("code", "name")
    list_filter = ("category",)


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "indicator", "source", "observation_date", "period_label",
        "frequency", "data_type", "display_value", "unit", "validation_status",
        "publication_date", "reviewed_by", "reviewed_at",
    )
    list_filter = ("validation_status", "frequency", "data_type", "source", "indicator")
    search_fields = ("indicator__code", "period_label", "unit")
    actions = ("action_validate",)
    readonly_fields = ("validation_status", "reviewed_by", "reviewed_at")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.validation_status == Observation.Status.PUBLISHED:
            return tuple(field.name for field in Observation._meta.fields)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Nilai (presisi sumber)")
    def display_value(self, obj):
        # A callable without ordering also blocks crafted ?o=... lexical sorting on SQLite TEXT.
        return format(obj.value, "f")

    def action_validate(self, request, queryset):
        from indicators.validate import validate_one

        for observation in queryset.filter(validation_status=Observation.Status.PENDING):
            problem = validate_one(observation)
            if problem is None:
                observation.validation_status = Observation.Status.VALIDATED
                observation.validation_notes = ""
            else:
                observation.validation_status = Observation.Status.REJECTED
                observation.validation_notes = problem
            observation.save()
        self.message_user(request, "Validasi admin selesai.")

    action_validate.short_description = "Validasi pelajaran terpilih"

@admin.register(ObservationCandidate)
class ObservationCandidateAdmin(admin.ModelAdmin):
    list_display = ("id", "indicator", "source", "status", "created_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "indicator", "source")
    readonly_fields = tuple(field.name for field in ObservationCandidate._meta.fields)
    actions = ("action_publish", "action_reject")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _review(self, request, queryset, publish):
        completed = 0
        for pk in queryset.values_list("pk", flat=True):
            try:
                review_candidate(pk, request.user, publish=publish,
                                 notes="" if publish else "Ditolak oleh Admin.")
                completed += 1
            except ValidationError as exc:
                self.message_user(request, f"Kandidat {pk}: {'; '.join(exc.messages)}", level=messages.ERROR)
        self.message_user(request, f"Review selesai: {completed} kandidat diproses.")

    @admin.action(description="Review dan publikasikan kandidat terpilih", permissions=["change"])
    def action_publish(self, request, queryset):
        self._review(request, queryset, True)

    @admin.action(description="Tolak kandidat terpilih", permissions=["change"])
    def action_reject(self, request, queryset):
        self._review(request, queryset, False)


@admin.register(RawFile)
class RawFileAdmin(admin.ModelAdmin):
    list_display = (
        "document_name", "source", "period_label", "retrieved_at",
        "checksum_sha256", "file_size_bytes", "parse_status",
    )
    search_fields = ("document_name", "checksum_sha256", "source__source_id")
    list_filter = ("source", "parse_status")
    readonly_fields = ("stored_path", "checksum_sha256", "parsed_time")

    def parsed_time(self, obj):
        return obj.retrieved_at
    parsed_time.short_description = "Waktu pengambilan"

@admin.register(DataUpdateLog)
class DataUpdateLogAdmin(admin.ModelAdmin):
    list_display = ("updated_at", "status", "source", "updated_by", "observation_count")
    list_filter = ("status", "source")
    search_fields = ("source", "message", "updated_by__username")
    readonly_fields = (
        "updated_at", "updated_by", "source", "status", "observation_count", "message",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
