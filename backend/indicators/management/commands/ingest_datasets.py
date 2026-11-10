from argparse import ArgumentParser
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from indicators.ingest import ingest_local_datasets
from indicators.updates import record_update_failure


class Command(BaseCommand):
    help = ("Ingest dataset lokal BI/BKPM ke RAW dan kandidat; "
            "perubahan memerlukan review Admin sebelum publikasi.")

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

        self.stdout.write(f"Folder dataset : {summary['scraping_dir']}")
        self.stdout.write(f"Baris BI       : {summary['bi_rows']}")
        self.stdout.write(f"Triwulan BKPM  : {summary['bkpm_quarters']}")
        for source_id in summary.get("skipped_inactive", []):
            self.stdout.write(self.style.WARNING(f"Sumber {source_id} nonaktif; impor dilewati."))
        if summary["errors"]:
            record_update_failure("Dataset BI dan BKPM", updated_by=user, message="; ".join(summary["errors"]))
            self.stdout.write(self.style.WARNING("Peringatan per file:"))
            for error in summary["errors"]:
                self.stdout.write(self.style.WARNING(f"  - {error}"))
        else:
            self.stdout.write(self.style.SUCCESS("Pemrosesan selesai; perubahan menunggu review, bukan publikasi."))
