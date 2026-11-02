from argparse import ArgumentParser
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from indicators.ingest import ingest_local_datasets
from indicators.updates import record_update_failure, record_update_success


class Command(BaseCommand):
    help = "Ingest dataset hasil scraping yang sudah ada dari folder scraping (BI xlsx dan BKPM zip CSV) ke RAW storage dan database."

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--dir",
            default=None,
            help="Folder dataset (default: variabel DEKSI_SCRAPING_DIR atau Folder Scrapping di samping proyek).",
        )
        parser.add_argument("--username", default="admin", help="Username admin yang dicatat pada log pembaruan.")

    def handle(self, *args, **options):
        scraping_dir = Path(options["dir"]) if options["dir"] else None
        user_model = get_user_model()
        user = user_model.objects.filter(username=options["username"]).first()
        try:
            summary = ingest_local_datasets(scraping_dir)
        except Exception as exc:
            record_update_failure("Dataset BI dan BKPM", updated_by=user, message=str(exc))
            raise
        count = summary["bi_rows"] + summary["bkpm_quarters"]

        self.stdout.write(f"Folder dataset : {summary['scraping_dir']}")
        self.stdout.write(f"Baris BI       : {summary['bi_rows']}")
        self.stdout.write(f"Triwulan BKPM  : {summary['bkpm_quarters']}")
        if summary["errors"]:
            record_update_failure("Dataset BI dan BKPM", updated_by=user, message="; ".join(summary["errors"]))
            self.stdout.write(self.style.WARNING("Peringatan per file:"))
            for error in summary["errors"]:
                self.stdout.write(self.style.WARNING(f"  - {error}"))
        else:
            record_update_success(
                "Dataset BI dan BKPM",
                updated_by=user,
                observation_count=count,
                message="Ingest dataset lokal berhasil.",
            )
            self.stdout.write(self.style.SUCCESS("Semua dataset berhasil diproses tanpa error."))
