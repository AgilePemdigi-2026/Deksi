# Seed 4 sumber resmi agar docker fresh langsung terisi.
# created dengan defaults persis seperti kode (hindari CandidateConflictError),
# lalu lengkapi kolom akuisisi bila masih kosong.
from django.db import migrations


CODE_DEFAULTS = {
    "BPS": {
        "source_name": "WebAPI BPS",
        "institution": "Badan Pusat Statistik",
        "primary_url": "https://www.bps.go.id/",
        "description": "Data indikator ekonomi resmi dari WebAPI Badan Pusat Statistik.",
    },
    "KEMENKEU": {
        "source_name": "APBN Kinerja dan Tindak Lanjut (APBN KiTa)",
        "institution": "Kementerian Keuangan RI",
        "primary_url": "https://djppr.kemenkeu.go.id/apbnkita",
        "description": (
            "Publikasi APBN KiTa (PDF resmi Kemenkeu), "
            "realisasi kumulatif pendapatan, belanja, defisit."
        ),
    },
    "BI": {
        "source_name": "Bank Indonesia Dataset",
        "institution": "Bank Indonesia",
        "primary_url": "https://www.bi.go.id/",
        "description": "Hasil pengambilan data dataset BI (BI-7Day-RR, Indikator Moneter, Kurs JISDOR).",
    },
    "BKPM": {
        "source_name": "Realisasi Investasi BKPM",
        "institution": "Kementerian Investasi/BKPM",
        "primary_url": "https://realisasiinvestasi.id/",
        "description": "Dataset realisasi investasi triwulanan PMA/PMDN tingkat nasional.",
    },
}

ACQUISITION = {
    "BPS": {
        "acquisition_method": "api_bps",
        "endpoint_url": "https://webapi.bps.go.id/v1",
        "data_format": "json",
        "frequency": "mixed",
        "update_schedule": "Mengikuti jadwal rilis WebAPI BPS",
        "status": "active",
    },
    "KEMENKEU": {
        "acquisition_method": "pdf_kita",
        "endpoint_url": "https://djppr.kemenkeu.go.id/apbnkita",
        "data_format": "pdf",
        "frequency": "monthly",
        "update_schedule": "Mengikuti edisi APBN KiTa",
        "status": "active",
    },
    "BI": {
        "acquisition_method": "file_xlsx",
        "endpoint_url": "",
        "data_format": "xlsx",
        "frequency": "mixed",
        "update_schedule": "Mengikuti dataset BI (harian/event)",
        "status": "active",
    },
    "BKPM": {
        "acquisition_method": "file_zip_csv",
        "endpoint_url": "https://realisasiinvestasi.id/",
        "data_format": "zip_csv",
        "frequency": "quarterly",
        "update_schedule": "Triwulanan PMA/PMDN",
        "status": "active",
    },
}


def seed_sources(apps, schema_editor):
    Source = apps.get_model("indicators", "Source")
    for source_id, defaults in CODE_DEFAULTS.items():
        obj, _ = Source.objects.get_or_create(source_id=source_id, defaults=defaults)
        patch = {}
        for key, value in ACQUISITION[source_id].items():
            if not getattr(obj, key, ""):
                patch[key] = value
        if patch:
            for key, value in patch.items():
                setattr(obj, key, value)
            obj.save(update_fields=list(patch))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("indicators", "0016_resync_reconciliation"),
    ]

    operations = [
        migrations.RunPython(seed_sources, noop),
    ]
