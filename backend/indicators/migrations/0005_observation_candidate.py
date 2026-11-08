from typing import ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("indicators", "0004_exact_observation_decimal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations: ClassVar[list] = [
        migrations.CreateModel(
            name="ObservationCandidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payload", models.JSONField()),
                ("base_snapshot", models.JSONField()),
                ("fingerprint", models.CharField(max_length=64, unique=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("published", "Published"),
                                                     ("rejected", "Rejected")], default="pending", max_length=12)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("indicator", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, to="indicators.indicator")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="indicators.source")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
