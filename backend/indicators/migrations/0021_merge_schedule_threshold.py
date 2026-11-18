# Merge Feature 23 schedules + Feature 24 thresholds merge lines.
from typing import ClassVar

from django.db import migrations


class Migration(migrations.Migration):

    dependencies: ClassVar = [
        ('indicators', '0020_merge_analysis_schedule'),
        ('indicators', '0020_merge_analysis_threshold'),
    ]

    operations: ClassVar = [
    ]
