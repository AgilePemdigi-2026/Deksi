# Merge Feature 19 analysis review audit + Feature 24 diagnostic threshold.
from typing import ClassVar

from django.db import migrations


class Migration(migrations.Migration):

    dependencies: ClassVar = [
        ('indicators', '0019_analysis_review_audit'),
        ('indicators', '0019_diagnostic_threshold'),
    ]

    operations: ClassVar = [
    ]
