from argparse import ArgumentParser
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from indicators.models import Observation
from indicators.management.commands.validate_observations import validate_all
from indicators.updates import record_update_success


class Command(BaseCommand):
    help = (
        "Tindakan review admin (administratior): setelah validasi otomatis, observasi "
        "berstatus validated ditandai published sehingga tersedia pada API publik."
    )

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--username", default="admin", help="Username admin yang dicatat sebagai reviewer")
        parser.add_argument(
            "--auto-create-admin",
            action="store_true",
            help="Buat superuser dengan username terkait bila belum ada (hanya untuk environment lokal).",
        )

    def handle(self, *args, **options):
        username = options["username"]
        user_model = get_user_model()
        user = user_model.objects.filter(username=username).first()
        if user is None:
            if not options["auto_create_admin"]:
                self.stderr.write(
                    f"Admin '{username}' tidak ditemukan. Buat admin dengan "
                    "`python manage.py createsuperuser` atau jalankan ulang dengan --auto-create-admin."
                )
                raise SystemExit(1)
            user = user_model.objects.create_superuser(username, f"{username}@deksi.local", "deksi-admin")
            self.stdout.write(f"Admin '{username}' dibuat (password default hanya untuk lokal).")
        if options["auto_create_admin"]:
            validation_summary = validate_all()
            self.stdout.write(
                f"Validasi ulang: {validation_summary['validated']} tervalidasi, "
                f"{validation_summary['rejected']} ditolak."
            )
        pending = Observation.objects.filter(validation_status=Observation.Status.VALIDATED)
        published = 0
        for observation in pending:
            observation.validation_status = Observation.Status.PUBLISHED
            observation.reviewed_by = user
            observation.reviewed_at = datetime.now(timezone.utc)
            published += 1
        Observation.objects.bulk_update(pending, ["validation_status", "reviewed_by", "reviewed_at"])
        if published:
            record_update_success(
                "Publikasi observasi tervalidasi",
                updated_by=user,
                observation_count=published,
                message="Admin mempublikasikan observasi tervalidasi.",
            )
        self.stdout.write(f"Review admin '{username}': {published} observasi dipublikasikan.")
