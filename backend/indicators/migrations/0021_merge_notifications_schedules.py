# Merge Feature 26 notifications + Feature 23 schedules merge lines.
from typing import ClassVar

from django.db import migrations


class Migration(migrations.Migration):

    dependencies: ClassVar = [
        ('indicators', '0020_merge_analysis_notification'),
        ('indicators', '0020_merge_analysis_schedule'),
    ]

    operations: ClassVar = [
    ]
