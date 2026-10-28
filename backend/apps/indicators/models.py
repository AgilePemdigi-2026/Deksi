import uuid
from django.db import models
from django.utils import timezone


class IndicatorCategory(models.TextChoices):
    """Kategori indikator ekonomi sesuai SRS DEKSI."""
    PDB = 'pdb', 'PDB (Produk Domestik Bruto)'
    INFLASI = 'inflasi', 'Inflasi'
    FISKAL = 'fiskal', 'Fiskal'
    MONETER = 'moneter', 'Moneter & Eksternal'
    INVESTASI = 'investasi', 'Investasi'
    TENAGA_KERJA = 'tenaga_kerja', 'Tenaga Kerja'


class DataType(models.TextChoices):
    """Jenis nilai: resmi dari lembaga atau turunan DEKSI."""
    OFFICIAL = 'official', 'Official Source Value'
    DERIVED = 'derived', 'DEKSI-Derived Metric'


class PublicationStatus(models.TextChoices):
    """Status publikasi indikator."""
    DRAFT = 'draft', 'Draft'
    PENDING_REVIEW = 'pending_review', 'Menunggu Review'
    PUBLISHED = 'published', 'Layak Publikasi'
    REJECTED = 'rejected', 'Ditolak'


class DataSource(models.Model):
    """
    Konfigurasi sumber data resmi (BPS, BI, Kemenkeu, BKPM).
    UC-06: Kelola Sumber Data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='Nama Institusi')
    code = models.CharField(max_length=50, unique=True, verbose_name='Kode Sumber')
    base_url = models.URLField(verbose_name='URL Basis')
    description = models.TextField(blank=True, verbose_name='Deskripsi')

    acquisition_method = models.CharField(
        max_length=50,
        choices=[
            ('api', 'API Resmi'),
            ('file', 'File Resmi (Excel/CSV)'),
            ('html', 'HTML Scraping'),
            ('pdf', 'PDF Fallback'),
        ],
        default='api',
        verbose_name='Metode Akuisisi'
    )

    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    last_fetched_at = models.DateTimeField(null=True, blank=True, verbose_name='Terakhir Diambil')
    last_fetch_status = models.CharField(
        max_length=20,
        choices=[('success', 'Berhasil'), ('failed', 'Gagal'), ('pending', 'Menunggu')],
        default='pending',
        verbose_name='Status Pengambilan'
    )
    last_fetch_message = models.TextField(blank=True, verbose_name='Pesan Status')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'data_sources'
        verbose_name = 'Sumber Data'
        verbose_name_plural = 'Sumber Data'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class EconomicIndicator(models.Model):
    """
    Master data indikator ekonomi.
    Contoh: PDB Atas Dasar Harga Berlaku, Inflasi YoY, BI-Rate, dll.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name='Kode Indikator')
    name = models.CharField(max_length=200, verbose_name='Nama Indikator')
    short_name = models.CharField(max_length=100, verbose_name='Nama Pendek')
    category = models.CharField(
        max_length=20,
        choices=IndicatorCategory.choices,
        verbose_name='Kategori'
    )
    data_type = models.CharField(
        max_length=10,
        choices=DataType.choices,
        default=DataType.OFFICIAL,
        verbose_name='Jenis Data'
    )
    unit = models.CharField(max_length=50, verbose_name='Satuan')
    description = models.TextField(blank=True, verbose_name='Deskripsi')
    methodology = models.TextField(blank=True, verbose_name='Metodologi')

    source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='indicators',
        verbose_name='Sumber Data'
    )

    # Untuk DERIVED: formula kalkulasi Economic Engine
    formula = models.TextField(blank=True, verbose_name='Formula Kalkulasi')
    formula_inputs = models.JSONField(
        default=list, blank=True,
        verbose_name='Input Formula (kode indikator)'
    )

    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    display_order = models.PositiveSmallIntegerField(default=0, verbose_name='Urutan Tampil')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'economic_indicators'
        verbose_name = 'Indikator Ekonomi'
        verbose_name_plural = 'Indikator Ekonomi'
        ordering = ['display_order', 'category', 'name']

    def __str__(self):
        return f"[{self.category}] {self.name}"


class IndicatorDataPoint(models.Model):
    """
    Nilai indikator per periode (time series).
    Menyimpan data RAW, CLEAN, dan DERIVED sesuai SRS.
    UC-02: Dashboard, UC-03: Detail, UC-04: Source Trace.
    """
    class DataLayer(models.TextChoices):
        RAW = 'raw', 'RAW (Data Sumber Asli)'
        CLEAN = 'clean', 'CLEAN (Ternormalisasi)'
        DERIVED = 'derived', 'DERIVED (Hasil Kalkulasi)'

    class PeriodType(models.TextChoices):
        ANNUAL = 'annual', 'Tahunan'
        QUARTERLY = 'quarterly', 'Kuartalan'
        MONTHLY = 'monthly', 'Bulanan'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    indicator = models.ForeignKey(
        EconomicIndicator,
        on_delete=models.CASCADE,
        related_name='data_points',
        verbose_name='Indikator'
    )

    # Periode
    period_type = models.CharField(
        max_length=15,
        choices=PeriodType.choices,
        verbose_name='Tipe Periode'
    )
    period_year = models.PositiveSmallIntegerField(verbose_name='Tahun')
    period_quarter = models.PositiveSmallIntegerField(
        null=True, blank=True,
        choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')],
        verbose_name='Kuartal'
    )
    period_month = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Bulan'
    )
    period_label = models.CharField(max_length=20, verbose_name='Label Periode')

    # Nilai
    value = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        verbose_name='Nilai'
    )
    data_layer = models.CharField(
        max_length=10,
        choices=DataLayer.choices,
        default=DataLayer.CLEAN,
        verbose_name='Layer Data'
    )

    # Status & Publikasi
    publication_status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        verbose_name='Status Publikasi'
    )

    # Trend (dihitung saat data diproses)
    trend_value = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name='Perubahan (vs periode sebelumnya)'
    )
    trend_percent = models.DecimalField(
        max_digits=8, decimal_places=4,
        null=True, blank=True,
        verbose_name='Perubahan (%)'
    )
    trend_direction = models.CharField(
        max_length=10,
        choices=[('up', 'Naik'), ('down', 'Turun'), ('stable', 'Stabil')],
        blank=True,
        verbose_name='Arah Tren'
    )

    # Metadata
    raw_value = models.TextField(blank=True, verbose_name='Nilai RAW Asli')
    notes = models.TextField(blank=True, verbose_name='Catatan')
    fetched_at = models.DateTimeField(null=True, blank=True, verbose_name='Waktu Pengambilan')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Waktu Publikasi')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'indicator_data_points'
        verbose_name = 'Data Point Indikator'
        verbose_name_plural = 'Data Points Indikator'
        ordering = ['-period_year', '-period_quarter', '-period_month']
        unique_together = [('indicator', 'period_type', 'period_year', 'period_quarter', 'period_month', 'data_layer')]

    def __str__(self):
        return f"{self.indicator.code} | {self.period_label} = {self.value}"


class SourceTrace(models.Model):
    """
    Penelusuran sumber (provenance) suatu data point.
    UC-04: Melihat Source Trace.
    Membedakan Official Source Value vs DEKSI-Derived Metric.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_point = models.OneToOneField(
        IndicatorDataPoint,
        on_delete=models.CASCADE,
        related_name='source_trace',
        verbose_name='Data Point'
    )

    # Sumber resmi
    institution_name = models.CharField(max_length=200, verbose_name='Nama Institusi')
    institution_code = models.CharField(max_length=50, blank=True, verbose_name='Kode Institusi')
    publication_name = models.CharField(max_length=300, blank=True, verbose_name='Nama Publikasi/Rilis')
    publication_url = models.URLField(blank=True, verbose_name='Tautan Publikasi Resmi')
    release_date = models.DateField(null=True, blank=True, verbose_name='Tanggal Rilis')

    # Metadata nilai
    official_value = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        verbose_name='Nilai Resmi'
    )
    official_unit = models.CharField(max_length=50, blank=True, verbose_name='Satuan Resmi')
    official_period = models.CharField(max_length=50, blank=True, verbose_name='Periode Resmi')

    # Untuk DERIVED: formula dan input
    formula_used = models.TextField(blank=True, verbose_name='Formula yang Digunakan')
    formula_inputs_detail = models.JSONField(
        default=dict, blank=True,
        verbose_name='Detail Input Formula'
    )

    # Metadata kelengkapan
    is_metadata_complete = models.BooleanField(default=True, verbose_name='Metadata Lengkap')
    incomplete_fields = models.JSONField(
        default=list, blank=True,
        verbose_name='Field Tidak Lengkap'
    )

    # Waktu akuisisi
    fetched_at = models.DateTimeField(null=True, blank=True, verbose_name='Waktu Pengambilan Data')
    version = models.CharField(max_length=20, blank=True, verbose_name='Versi/Revisi')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'source_traces'
        verbose_name = 'Source Trace'
        verbose_name_plural = 'Source Traces'

    def __str__(self):
        return f"Trace: {self.data_point.indicator.code} | {self.institution_name}"


class DiagnosticFlag(models.Model):
    """
    Diagnostic flags dari Diagnostic Engine per data point.
    Digunakan di Dashboard (UC-02) dan Review (UC-08).
    """
    class Severity(models.TextChoices):
        INFO = 'info', 'Informasi'
        WARNING = 'warning', 'Peringatan'
        CRITICAL = 'critical', 'Kritis'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_point = models.ForeignKey(
        IndicatorDataPoint,
        on_delete=models.CASCADE,
        related_name='diagnostic_flags',
        verbose_name='Data Point'
    )
    flag_code = models.CharField(max_length=50, verbose_name='Kode Flag')
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
        verbose_name='Tingkat Keparahan'
    )
    message = models.TextField(verbose_name='Pesan Diagnostik')
    evidence = models.JSONField(default=dict, blank=True, verbose_name='Bukti/Evidence')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diagnostic_flags'
        verbose_name = 'Diagnostic Flag'
        verbose_name_plural = 'Diagnostic Flags'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.flag_code}: {self.data_point}"


class RevisionQuerySet(models.QuerySet):
    """All revision writes go through capture/publication services, not bulk editors."""

    def update(self, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError('Use the revision publication service.')

    def delete(self):
        from django.core.exceptions import ValidationError
        raise ValidationError('Revisions are retained; withdraw publication instead.')

    def bulk_create(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError('Capture revisions individually.')

    def bulk_update(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError('Revision content is immutable.')


class SourceTraceRevision(models.Model):
    """Shared observation snapshot. ORM/Admin protection does not restrict direct SQL."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_point = models.ForeignKey(IndicatorDataPoint, on_delete=models.PROTECT, related_name='revisions')
    source_trace = models.ForeignKey(SourceTrace, on_delete=models.PROTECT, null=True, blank=True, related_name='revisions')
    sequence = models.PositiveIntegerField()
    previous_revision = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    snapshot = models.JSONField()
    snapshot_hash = models.CharField(max_length=64, editable=False)
    publication_status = models.CharField(max_length=20, choices=PublicationStatus.choices, default=PublicationStatus.DRAFT)
    reviewed_by = models.ForeignKey('accounts.AdminUser', on_delete=models.PROTECT, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = RevisionQuerySet.as_manager()

    class Meta:
        db_table = 'source_trace_revisions'
        ordering = ['data_point_id', 'sequence']
        constraints = [
            models.UniqueConstraint(fields=['data_point', 'sequence'], name='unique_point_revision_sequence'),
            models.CheckConstraint(condition=models.Q(sequence__gt=0), name='positive_revision_sequence'),
            models.CheckConstraint(
                condition=~models.Q(publication_status='published') | (
                    models.Q(reviewed_by__isnull=False) & models.Q(reviewed_at__isnull=False) & models.Q(published_at__isnull=False)
                ), name='published_revision_requires_review',
            ),
        ]

    def validate_content(self):
        from django.core.exceptions import ValidationError
        from .snapshots import digest, validate
        try:
            validate(self.snapshot, point_id=self.data_point_id, trace_id=self.source_trace_id,
                     revision_id=self.pk, sequence=self.sequence, schema_version=self.schema_version)
            if self.snapshot_hash != digest(self.snapshot):
                raise ValidationError('Snapshot content does not match its review binding.')
        except (TypeError, ValueError, KeyError, OverflowError):
            raise ValidationError('Invalid snapshot content.') from None

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if not self._state.adding:
            raise ValidationError('Revision content is immutable; capture a new revision.')
        if self.publication_status != PublicationStatus.DRAFT or any([self.reviewed_by_id, self.reviewed_at, self.published_at]):
            raise ValidationError('New revisions must start unreviewed and draft.')
        self.validate_content()
        if self.snapshot['identity']['indicator_id'] != str(self.data_point.indicator_id):
            raise ValidationError('Observation identity mismatch.')
        if self.source_trace_id and self.source_trace.data_point_id != self.data_point_id:
            raise ValidationError('Source Trace belongs to another observation.')
        if self.previous_revision_id and (self.previous_revision.data_point_id != self.data_point_id or self.previous_revision.sequence >= self.sequence):
            raise ValidationError('Invalid revision parent.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError('Revisions are retained; withdraw publication instead.')

    def __str__(self):
        return f'{self.data_point_id} / revision {self.sequence}'
