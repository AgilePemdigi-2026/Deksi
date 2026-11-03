"""
Model Feedback - menyimpan umpan balik yang dikirim pengguna publik.

Kolom identitas pengirim (sender_name, sender_email) bersifat opsional sesuai SRS
agar pengguna dapat mengirim tanpa membuat akun.  Kolom related_* menghubungkan
umpan balik ke indikator atau periode tertentu sehingga Admin dapat menindaklanjuti
dengan konteks yang cukup.
"""

from typing import ClassVar

from django.db import models


class Feedback(models.Model):
    class Category(models.TextChoices):
        DATA_ERROR = "data_error", "Kesalahan Data"
        METHODOLOGY = "methodology", "Metodologi / Penjelasan"
        VISUALIZATION = "visualization", "Visualisasi"
        SOURCE = "source", "Sumber Data"
        OTHER = "other", "Lainnya"

    class Status(models.TextChoices):
        PENDING = "pending", "Menunggu Ditinjau"
        IN_REVIEW = "in_review", "Sedang Ditinjau"
        RESOLVED = "resolved", "Diselesaikan"
        REJECTED = "rejected", "Ditolak"

    # Isi umpan balik
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name="Kategori",
    )
    description = models.TextField(verbose_name="Deskripsi")

    # Identitas pengirim - opsional
    sender_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Nama Pengirim")
    sender_email = models.EmailField(blank=True, default="", verbose_name="Email Pengirim")

    # Pengaitan dengan indikator / versi tertentu - opsional
    related_indicator_code = models.CharField(
        max_length=32, blank=True, default="", verbose_name="Kode Indikator Terkait"
    )
    related_period = models.CharField(max_length=50, blank=True, default="", verbose_name="Periode Terkait")

    # Status penanganan
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )
    admin_notes = models.TextField(blank=True, default="", verbose_name="Catatan Admin")

    # Metadata teknis
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Pengirim")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dikirim Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui")

    class Meta:
        db_table = "feedback"
        ordering: ClassVar[list[str]] = ["-created_at"]
        verbose_name = "Umpan Balik"
        verbose_name_plural = "Umpan Balik"

    def __str__(self) -> str:
        sender = self.sender_name or self.sender_email or "Anonim"
        return f"[{self.get_category_display()}] {sender} - {self.created_at:%Y-%m-%d}"
