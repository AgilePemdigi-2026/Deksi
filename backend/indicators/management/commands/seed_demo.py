"""Seed explicitly isolated synthetic data; never operate on the ordinary database."""

import os
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from indicators.feedback_model import Feedback
from indicators.models import Indicator, Observation, ObservationCandidate, RawFile, Source

DATA = (
    ("pdb", "PDB (SIMULASI)", "PDB", "%", "yoy", (4.7, 4.8, 4.9, 5.0, 5.1, 5.0, 5.2, 5.1)),
    ("inflasi", "Inflasi (SIMULASI)", "Inflasi", "%", "yoy", (2.8, 2.7, 2.6, 2.5, 2.6, 2.4, 2.5, 2.3)),
    ("fiskal", "Fiskal (SIMULASI)", "Fiskal", "Rp triliun", "level", (180, 190, 200, 210, 220, 230, 240, 250)),
    ("investasi", "Investasi (SIMULASI)", "Investasi", "Rp triliun", "level", (110, 115, 120, 125, 130, 135, 140, 145)),
    ("birate", "BI Rate (SIMULASI)", "Moneter", "%", "level", (6.0, 6.0, 5.75, 5.75, 5.5, 5.5, 5.25, 5.25)),
    ("tpt", "Pengangguran (SIMULASI)", "Tenaga Kerja", "%", "level", (5.5, 5.4, 5.4, 5.3, 5.3, 5.2, 5.2, 5.1)),
)


def is_isolated_demo_database():
    return (
        os.environ.get("DJANGO_SETTINGS_MODULE") == "backend.settings_demo"
        and connection.settings_dict["ENGINE"] == "django.db.backends.sqlite3"
        and str(connection.settings_dict["NAME"]) == "/data/deksi-demo.sqlite3"
    )


class Command(BaseCommand):
    help = "Isi database demo terisolasi yang kosong dengan data simulasi; bukan data resmi."

    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            or not getattr(settings, "DEKSI_SYNTHETIC_DEMO", False)
            or not is_isolated_demo_database()
        ):
            raise CommandError("Diperlukan settings demo lokal dan database /data/deksi-demo.sqlite3.")
        with transaction.atomic():
            models = (Indicator, Observation, ObservationCandidate, RawFile, Source, Feedback, get_user_model())
            if any(model.objects.exists() for model in models):
                raise CommandError("Database tidak kosong; tidak ada data yang ditambahkan atau ditimpa.")
            reviewer = get_user_model().objects.create_user(
                username="demo-simulation-not-human-review", is_active=False
            )
            source = Source.objects.create(
                source_id="DEMO_SIMULASI",
                source_name="DATA SIMULASI - BUKAN DATA RESMI",
                institution="SIMULASI LOKAL - BUKAN INSTANSI RESMI",
                primary_url="https://example.invalid/demo",
                description="Data dibuat untuk demo; bukan sumber, angka, atau verifikasi resmi.",
            )
            for order, (code, name, category, unit, kind, values) in enumerate(DATA):
                indicator = Indicator.objects.create(
                    code=code,
                    name=name,
                    category=category,
                    unit=unit,
                    sort_order=order,
                    description="DATA SIMULASI UNTUK DEMO - BUKAN ANGKA RESMI",
                    footnote="Simulasi lokal, bukan data resmi atau review manusia.",
                )
                for index, value in enumerate(values):
                    year, quarter = 2024 + index // 4, index % 4 + 1
                    Observation.objects.create(
                        indicator=indicator,
                        source=source,
                        observation_date=date(year, (quarter - 1) * 3 + 1, 1),
                        period_label=f"SIMULASI Q{quarter} {year}",
                        frequency="quarterly",
                        data_type=kind,
                        value=str(value),
                        unit=unit,
                        validation_status="published",
                        reviewed_by=reviewer,
                        reviewed_at=timezone.now(),
                        validation_notes="SIMULASI: status teknis preview, bukan review manusia atau verifikasi resmi.",
                    )
        self.stdout.write("SIMULASI: 6 indikator, 48 observasi. Bukan data resmi atau review manusia.")
