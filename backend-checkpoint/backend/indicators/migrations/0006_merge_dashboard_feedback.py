from typing import ClassVar

from django.db import migrations


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("indicators", "0004_feedback_model"),
        ("indicators", "0005_observation_candidate"),
    ]

    operations: ClassVar[list] = []
