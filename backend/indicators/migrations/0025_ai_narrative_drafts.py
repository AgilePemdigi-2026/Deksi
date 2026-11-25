"""Private narrative revisions; no alteration of observation review or published data."""
from typing import ClassVar

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ('indicators', '0024_kemenkeu_online_choice'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations: ClassVar[list] = [
        migrations.CreateModel(
            name='AINarrativeDraft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_key', models.UUIDField(editable=False, unique=True)),
                ('request_digest', models.CharField(editable=False, max_length=64)),
                ('observation_id', models.PositiveBigIntegerField(editable=False)),
                ('comparison_id', models.PositiveBigIntegerField(editable=False, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('fact_package', models.JSONField(editable=False)),
                ('input_digest', models.CharField(editable=False, max_length=64)),
                ('requested_model', models.CharField(editable=False, max_length=160)),
                ('provider_fingerprint', models.CharField(editable=False, max_length=64)),
                ('prompt_version', models.CharField(editable=False, max_length=40)),
                ('validator_version', models.CharField(editable=False, max_length=40)),
                ('generation_status', models.CharField(choices=[(v, v) for v in (
                    'queued', 'running', 'ready', 'failed', 'unknown')],
                    default='queued', editable=False, max_length=12)),
                ('active_slot', models.PositiveSmallIntegerField(editable=False, null=True, unique=True)),
                ('claim', models.UUIDField(editable=False, null=True)),
                ('started_at', models.DateTimeField(editable=False, null=True)),
                ('deadline_at', models.DateTimeField(editable=False, null=True)),
                ('finished_at', models.DateTimeField(editable=False, null=True)),
                ('error_code', models.CharField(blank=True, default='', editable=False, max_length=64)),
                ('narrative', models.JSONField(editable=False, null=True)),
                ('reported_model', models.CharField(editable=False, max_length=160, null=True)),
                ('content_digest', models.CharField(editable=False, max_length=64, null=True)),
                ('reconciled_at', models.DateTimeField(editable=False, null=True)),
                ('reconciliation_notes', models.CharField(blank=True, default='', editable=False, max_length=500)),
                ('created_by', models.ForeignKey(editable=False,
                    on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(editable=False, null=True,
                    on_delete=django.db.models.deletion.PROTECT, to='indicators.ainarrativedraft')),
            ],
            options={'ordering': ['-id'], 'default_permissions': ('view',), 'permissions': [
                ('generate_ainarrativedraft', 'Request and reconcile AI narrative drafts'),
                ('review_ainarrativedraft', 'Review an exact AI narrative revision')]},
        ),
        migrations.CreateModel(
            name='AINarrativeReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_digest', models.CharField(editable=False, max_length=64)),
                ('decision', models.CharField(choices=[(v, v) for v in (
                    'approved', 'needs_revision', 'rejected')], editable=False, max_length=16)),
                ('notes', models.CharField(blank=True, default='', editable=False, max_length=500)),
                ('reviewed_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('draft', models.OneToOneField(editable=False, on_delete=django.db.models.deletion.PROTECT,
                    related_name='review', to='indicators.ainarrativedraft')),
                ('reviewed_by', models.ForeignKey(editable=False,
                    on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-id'], 'default_permissions': ('view',)},
        ),
    ]
