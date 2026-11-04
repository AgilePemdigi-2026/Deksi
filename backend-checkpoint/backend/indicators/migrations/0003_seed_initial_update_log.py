from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations


SEED_MESSAGE = "Data awal DEKSI dari dataset BI dan BKPM yang sudah tersimpan."


def seed_initial_update(apps, schema_editor):
    DataUpdateLog = apps.get_model("indicators", "DataUpdateLog")
    if DataUpdateLog.objects.exists():
        return
    DataUpdateLog.objects.create(
        updated_at=datetime(2026, 11, 1, 0, 0, tzinfo=ZoneInfo("Asia/Jakarta")),
        source="Dataset awal BI dan BKPM",
        status="success",
        observation_count=0,
        message=SEED_MESSAGE,
    )


def remove_initial_update(apps, schema_editor):
    DataUpdateLog = apps.get_model("indicators", "DataUpdateLog")
    DataUpdateLog.objects.filter(message=SEED_MESSAGE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("indicators", "0002_alter_observation_frequency_dataupdatelog"),
    ]

    operations = [
        migrations.RunPython(seed_initial_update, remove_initial_update),
    ]
