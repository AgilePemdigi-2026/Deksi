import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('indicators', '0026_merge_ai_narrative_main'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='PublicEngineAIDailyUsage',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('day', models.DateField(unique=True)), ('count', models.PositiveIntegerField(default=0))],
        ),
        migrations.CreateModel(
            name='PublicEngineAIRequest',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('request_key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                    ('input_digest', models.CharField(max_length=64)), ('result_digest', models.CharField(max_length=64)),
                    ('period_end', models.DateField()), ('snapshot', models.JSONField()),
                    ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('ready', 'Ready'), ('failed', 'Failed'), ('unknown', 'Unknown'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='queued', max_length=12)),
                    ('narrative', models.JSONField(null=True)), ('error_code', models.CharField(blank=True, default='', max_length=40)),
                    ('claimed_at', models.DateTimeField(null=True)), ('completed_at', models.DateTimeField(null=True)),
                    ('approved_result_digest', models.CharField(blank=True, default='', max_length=64)),
                    ('approved_content_digest', models.CharField(blank=True, default='', max_length=64)),
                    ('created_at', models.DateTimeField(default=django.utils.timezone.now))],
            options={'permissions': [('review_publicengineairequest', 'Review public Economic Engine AI narratives')]},
        ),
        migrations.AddConstraint(model_name='publicengineairequest', constraint=models.UniqueConstraint(fields=('period_end', 'input_digest'), name='engine_ai_input_once')),
        migrations.AddIndex(model_name='publicengineairequest', index=models.Index(fields=['status', 'id'], name='engine_ai_status_id')),
        migrations.CreateModel(
            name='PublicEngineAIReview',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('result_digest', models.CharField(max_length=64)),
                    ('content_digest', models.CharField(max_length=64)),
                    ('decision', models.CharField(choices=[('approved', 'approved'), ('rejected', 'rejected')], max_length=10)),
                    ('notes', models.CharField(blank=True, default='', max_length=500)),
                    ('reviewed_at', models.DateTimeField(default=django.utils.timezone.now)),
                    ('request', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='review', to='indicators.publicengineairequest')),
                    ('reviewed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL))],
        ),
    ]
