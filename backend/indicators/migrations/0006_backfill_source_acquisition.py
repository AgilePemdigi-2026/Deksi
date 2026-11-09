# Backfill registry akuisisi untuk 4 sumber resmi yang sudah ada.
# Nilai mengikuti handler yang benar-benar terimplementasi di codebase:
# BPS -> WebAPI JSON (bps.py), KEMENKEU -> PDF KiTa (fiscal.py/kemenkeu.py),
# BI -> XLSX lokal (ingest.py), BKPM -> ZIP-CSV lokal (ingest.py).

from django.db import migrations


BACKFILL = {
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


def backfill_sources(apps, schema_editor):
    Source = apps.get_model("indicators", "Source")
    for source_id, values in BACKFILL.items():
        Source.objects.filter(source_id=source_id, acquisition_method="").update(**values)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("indicators", "0005_source_acquisition_method_source_data_format_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_sources, noop),
    ]
