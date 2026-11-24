import time

from django.core.management.base import BaseCommand

from indicators.resync_worker import process_one


class Command(BaseCommand):
    help = "Proses antrean sinkronisasi ulang; pekerjaan yang terhenti tidak diulang otomatis."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Proses satu pekerjaan lalu keluar.")

    def handle(self, *args, **options):
        while True:
            job = process_one()
            if options["once"]:
                return
            if job is None:
                time.sleep(5)
