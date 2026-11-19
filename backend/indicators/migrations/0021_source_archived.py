from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar = [("indicators", "0020_merge_analysis_schedule")]

    operations: ClassVar = [
        migrations.AlterField(
            model_name="source",
            name="status",
            field=models.CharField(
                choices=[("active", "Aktif"), ("inactive", "Nonaktif"), ("archived", "Diarsipkan")],
                db_default="active", default="active", max_length=16,
            ),
        ),
    ]
