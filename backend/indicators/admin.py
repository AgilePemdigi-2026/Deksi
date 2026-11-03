from django.contrib import admin
from django.utils import timezone

from indicators.models import DataUpdateLog, Indicator, Observation, RawFile, Source
from indicators.updates import record_update_success


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
        "frequency", "data_type", "value", "unit", "validation_status",
        "publication_date", "reviewed_by", "reviewed_at",
    )
    list_filter = ("validation_status", "frequency", "data_type", "source", "indicator")
    search_fields = ("indicator__code", "period_label", "unit")
    actions = ("action_validate", "action_publish")

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

    def action_publish(self, request, queryset):
        published = 0
        sources = set()
        for observation in queryset.filter(validation_status=Observation.Status.VALIDATED).select_related("source"):
            observation.validation_status = Observation.Status.PUBLISHED
            observation.reviewed_by = request.user
            observation.reviewed_at = timezone.now()
            observation.save(update_fields=["validation_status", "reviewed_by", "reviewed_at"])
            sources.add(observation.source.institution)
            published += 1
        if published:
            record_update_success(
                ", ".join(sorted(sources)) or "Observasi DEKSI",
                updated_by=request.user,
                observation_count=published,
                message="Publikasi observasi melalui admin DEKSI.",
            )
        self.message_user(request, f"Publikasi admin selesai: {published} observasi.")

    action_publish.short_description = "Publikasi observasi tervalidasi"


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


# ---------------------------------------------------------------------------
# Fitur 8: Umpan Balik
# ---------------------------------------------------------------------------
from indicators.feedback_model import Feedback  # noqa: E402


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id", "category", "sender_name", "sender_email",
        "related_indicator_code", "related_period",
        "status", "created_at",
    )
    list_filter = ("status", "category")
    search_fields = ("description", "sender_name", "sender_email", "related_indicator_code")
    readonly_fields = ("ip_address", "created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ("action_mark_resolved", "action_mark_in_review")

    @admin.action(description="Tandai sebagai Diselesaikan")
    def action_mark_resolved(self, request, queryset):
        updated = queryset.update(status=Feedback.Status.RESOLVED)
        self.message_user(request, f"{updated} umpan balik ditandai sebagai Diselesaikan.")

    @admin.action(description="Tandai sebagai Sedang Ditinjau")
    def action_mark_in_review(self, request, queryset):
        updated = queryset.update(status=Feedback.Status.IN_REVIEW)
        self.message_user(request, f"{updated} umpan balik ditandai sebagai Sedang Ditinjau.")
