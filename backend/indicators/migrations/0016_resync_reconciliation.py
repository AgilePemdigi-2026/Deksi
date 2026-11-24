import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("indicators", "0015_resyncjob"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="resyncjob", name="resolved_at", field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resyncjob", name="resolved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="resolved_resync_jobs", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="resyncjob", name="resolution_reason",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="resyncjob", name="status",
            field=models.CharField(choices=[("queued", "Menunggu"), ("running", "Berlangsung"),
                ("success", "Berhasil"), ("failed", "Gagal"), ("cancelled", "Tidak dimulai"),
                ("unknown", "Hasil tidak diketahui")], default="queued", max_length=12),
        ),
        migrations.AlterField(
            model_name="syncrun", name="status",
            field=models.CharField(choices=[("running", "Running"), ("success", "Success"),
                ("failed", "Failed"), ("unknown", "Unknown")], db_index=True, default="running", max_length=8),
        ),
    ]
