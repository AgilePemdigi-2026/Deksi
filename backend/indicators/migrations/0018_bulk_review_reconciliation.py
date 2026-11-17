from typing import ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar = [
        ("indicators", "0017_bulk_candidate_review"),
        ("indicators", "0017_seed_official_sources"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations: ClassVar = [
        migrations.AddField(
            model_name="bulkcandidatereview", name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bulkcandidatereview", name="resolved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="resolved_bulk_candidate_reviews", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="bulkcandidatereview", name="resolution_reason",
            field=models.TextField(blank=True, default=""),
        ),
    ]
