"""Join the main schema and AI draft branches; no schema or data operations."""
from typing import ClassVar

from django.db import migrations


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ('indicators', '0025_ai_narrative_drafts'),
        ('indicators', '0025_merge_20261124_2326'),
    ]
    operations: ClassVar[list] = []
