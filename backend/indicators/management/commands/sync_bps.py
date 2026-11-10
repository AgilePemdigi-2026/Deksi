from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from indicators import bps
from indicators.source_status import InactiveSourceError
from indicators.updates import record_update_failure


class Command(BaseCommand):
    help = "Sinkronkan indikator PDB, inflasi, dan TPT dari WebAPI BPS ke database DEKSI."

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--start-year", type=int, default=2016, help="Tahun awal data (default: 2016).")
        parser.add_argument("--end-year", type=int, default=None, help="Tahun akhir data (default: tahun berjalan).")
        parser.add_argument("--username", default="admin", help="Username admin yang dicatat pada log pembaruan.")

    def handle(self, *args, **options):
        user_model = get_user_model()
        user = user_model.objects.filter(username=options["username"]).first()
        try:
            summary = bps.sync_bps_indicators(
                start_year=options["start_year"],
                end_year=options["end_year"],
            )
        except InactiveSourceError as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        except (bps.BpsError, ValidationError) as exc:
            record_update_failure("WebAPI BPS", updated_by=user, message=str(exc))
            self.stderr.write(self.style.ERROR(str(exc)))
            raise SystemExit(2) from exc
        if summary["errors"]:
            message = "; ".join(summary["errors"])
            record_update_failure("WebAPI BPS", updated_by=user, message=message)
            self.stderr.write(self.style.ERROR(f"Sinkronisasi BPS gagal sebagian: {message}"))
            raise SystemExit(2)
        self.stdout.write(self.style.SUCCESS(
            f"Observasi BPS diproses: {summary['observations']}; belum dipublikasikan."))
        for code, period in summary["latest"].items():
            self.stdout.write(self.style.SUCCESS(f"{code}: periode terbaru {period}"))
