from django.conf import settings
from django.db import models
from django.utils import timezone

from indicators.fields import ObservationDecimalField


class Source(models.Model):
    class AcquisitionMethod(models.TextChoices):
        API_BPS = "api_bps", "API resmi (WebAPI BPS)"
        PDF_KITA = "pdf_kita", "PDF resmi (APBN KiTa Kemenkeu)"
        FILE_XLSX = "file_xlsx", "File resmi (XLSX dataset)"
        FILE_ZIP_CSV = "file_zip_csv", "File resmi (ZIP berisi CSV)"

    class DataFormat(models.TextChoices):
        JSON = "json", "JSON"
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "XLSX"
        ZIP_CSV = "zip_csv", "ZIP-CSV"

    class SourceStatus(models.TextChoices):
        ACTIVE = "active", "Aktif"
        INACTIVE = "inactive", "Nonaktif"

    source_id = models.CharField(max_length=32, unique=True)
    source_name = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    primary_url = models.URLField(max_length=500)
    description = models.TextField(blank=True, default="")
    # db_default menjaga kompatibilitas INSERT dari versi model lama
    # (mis. migrasi balik pada uji migrasi) yang tak mengenal kolom ini.
    acquisition_method = models.CharField(
        max_length=32, choices=AcquisitionMethod.choices, blank=True, default="", db_default=""
    )
    endpoint_url = models.URLField(max_length=1000, blank=True, default="", db_default="")
    data_format = models.CharField(max_length=16, choices=DataFormat.choices, blank=True, default="", db_default="")
    frequency = models.CharField(max_length=16, blank=True, default="", db_default="")
    update_schedule = models.CharField(max_length=200, blank=True, default="", db_default="")
    status = models.CharField(
        max_length=16, choices=SourceStatus.choices, default=SourceStatus.ACTIVE, db_default=SourceStatus.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.source_id} ({self.institution})"


def source_config_snapshot(source: "Source") -> dict:
    """Snapshot konfigurasi tanpa secret (model Source tidak menyimpan secret)."""
    return {
        "sourceId": source.source_id,
        "sourceName": source.source_name,
        "institution": source.institution,
        "primaryUrl": source.primary_url,
        "description": source.description or "",
        "acquisitionMethod": source.acquisition_method or "",
        "endpointUrl": source.endpoint_url or "",
        "dataFormat": source.data_format or "",
        "frequency": source.frequency or "",
        "updateSchedule": source.update_schedule or "",
        "status": source.status,
    }


class SourceRevision(models.Model):
    """Riwayat revisi konfigurasi sumber. Tidak pernah dihapus/diubah saat edit."""

    class Action(models.TextChoices):
        CREATE = "tambah", "Tambah sumber"
        UPDATE = "edit", "Edit sumber"

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveIntegerField()
    action = models.CharField(max_length=16, choices=Action.choices)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    changed_fields = models.JSONField(default=list)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deksi_source_revisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        unique_together = [("source", "version")]

    def __str__(self) -> str:
        return f"{self.source.source_id} v{self.version} ({self.action})"


class RawFile(models.Model):
    class ParseStatus(models.TextChoices):
        PENDING = "pending"
        PARSED = "parsed"
        FAILED = "failed"

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="raw_files")
    document_name = models.CharField(max_length=300)
    source_url = models.URLField(max_length=1000, blank=True, default="")
    period_label = models.CharField(max_length=100, blank=True, default="")
    retrieved_at = models.DateTimeField(null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    stored_path = models.CharField(max_length=500, blank=True, default="")
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    parse_status = models.CharField(max_length=16, choices=ParseStatus.choices, default=ParseStatus.PENDING)
    parse_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-retrieved_at", "-id"]
        unique_together = [("source", "checksum_sha256")]

    def __str__(self) -> str:
        return f"{self.source.source_id}: {self.document_name}"


class Indicator(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    unit = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    footnote = models.TextField(blank=True, default="")
    aggregation_kind = models.CharField(max_length=16, default="avg")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


class Observation(models.Model):
    class Frequency(models.TextChoices):
        DAILY = "daily"
        MONTHLY = "monthly"
        QUARTERLY = "quarterly"
        SEMIANNUAL = "semiannual"
        ANNUAL = "annual"
        ADHOC = "adhoc"

    class DataType(models.TextChoices):
        LEVEL = "level"
        YOY = "yoy"
        CUMULATIVE_YTD = "cumulative_ytd"
        DERIVED_SUM = "derived_sum"
        EVENT = "event"

    class Status(models.TextChoices):
        PENDING = "pending"
        VALIDATED = "validated"
        PUBLISHED = "published"
        REJECTED = "rejected"

    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="observations")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="observations")
    raw_file = models.ForeignKey(RawFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="observations")
    observation_date = models.DateField()
    period_label = models.CharField(max_length=100)
    frequency = models.CharField(max_length=12, choices=Frequency.choices)
    data_type = models.CharField(max_length=20, choices=DataType.choices)
    value = ObservationDecimalField(max_digits=24, decimal_places=6)
    unit = models.CharField(max_length=50)
    publication_date = models.DateField(null=True, blank=True)
    validation_status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    validation_notes = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["indicator", "observation_date", "id"]
        unique_together = [("indicator", "source", "observation_date", "data_type")]

    def __str__(self) -> str:
        return f"{self.indicator.code} {self.period_label} = {self.value} {self.unit}"

class ObservationCandidate(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PUBLISHED = "published"
        REJECTED = "rejected"

    indicator = models.ForeignKey(Indicator, on_delete=models.PROTECT)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    payload = models.JSONField()
    base_snapshot = models.JSONField()
    fingerprint = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Kandidat {self.pk}: {self.indicator.code} ({self.status})"


class DataUpdateLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success"
        FAILED = "failed"

    updated_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deksi_data_updates",
    )
    source = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUCCESS)
    observation_count = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return f"{self.updated_at.isoformat()} {self.status} {self.source}"


# Re-export agar migration discovery berfungsi dari satu modul
from indicators.feedback_model import Feedback, FeedbackAuditLog  # noqa: E402, F401
