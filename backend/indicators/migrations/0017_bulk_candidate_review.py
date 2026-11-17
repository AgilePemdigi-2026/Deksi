import uuid
from typing import ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar = [
        ("indicators", "0016_resync_reconciliation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations: ClassVar = [
        migrations.CreateModel(
            name="BulkCandidateReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("preview", "Preview"), ("running", "Berlangsung"),
                    ("completed", "Selesai"), ("unknown", "Hasil tidak diketahui")], default="preview", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="bulk_candidate_reviews", to=settings.AUTH_USER_MODEL)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="bulk_candidate_reviews", to="indicators.source")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="BulkCandidateReviewItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("candidate_snapshot", models.JSONField()),
                ("eligible", models.BooleanField(default=False)),
                ("exclusion_reason", models.CharField(blank=True, max_length=100, null=True)),
                ("status", models.CharField(choices=[("excluded", "Dikecualikan"), ("pending", "Menunggu"),
                    ("published", "Dipublikasikan"), ("skipped", "Dilewati"),
                    ("unknown", "Tidak diketahui")], default="pending", max_length=12)),
                ("reason", models.CharField(blank=True, max_length=100, null=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="items", to="indicators.bulkcandidatereview")),
                ("candidate", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="bulk_review_items", to="indicators.observationcandidate")),
            ],
            options={"ordering": ["candidate_id"]},
        ),
        migrations.AddConstraint(
            model_name="bulkcandidatereviewitem",
            constraint=models.UniqueConstraint(fields=("batch", "candidate"), name="bulk_review_candidate_once"),
        ),
    ]
