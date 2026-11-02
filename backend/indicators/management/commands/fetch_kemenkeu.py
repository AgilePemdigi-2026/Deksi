from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from indicators import fiscal
from indicators import kemenkeu
from indicators.updates import record_update_failure, record_update_success


class Command(BaseCommand):
    help = (
        "Ambil PDF resmi APBN KiTa Kemenkeu, ekstraksi dengan pdftotext, simpan RAW + metadata, "
        "lalu simpan observasi kumulatif pendapatan/belanja/defisit ke database."
    )

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--url",
            default=None,
            help="URL PDF APBN KiTa untuk diterima. Default: URL publikasi resmi terbaru.",
        )
        parser.add_argument("--username", default="admin", help="Username admin yang dicatat pada log pembaruan.")

    def handle(self, *args, **options):
        url = options["url"] or kemenkeu.DEFAULT_KITA_URLS[0]
        user_model = get_user_model()
        user = user_model.objects.filter(username=options["username"]).first()
        self.stdout.write(f"Mengambil PDF APBN KiTa: {url}")
        try:
            summary = fiscal.ingest_kita_pdf_url(url)
        except kemenkeu.KitaError as exc:
            record_update_failure("APBN KiTa Kemenkeu", updated_by=user, message=str(exc))
            self.stderr.write(self.style.ERROR(f"Ekstraksi dibatalkan: {exc}"))
            raise SystemExit(2)
        record_update_success(
            "APBN KiTa Kemenkeu",
            updated_by=user,
            observation_count=len(summary["metrics"]),
            message=f"Metadata APBN KiTa {summary['period_label']} berhasil diambil.",
        )
        self.stdout.write(self.style.SUCCESS(f"Dokumen      : {summary['document_name']}"))
        self.stdout.write(self.style.SUCCESS(f"Periode      : {summary['period_label']}"))
        self.stdout.write(self.style.SUCCESS(f"Rilis data   : {summary['publication_date']}"))
        self.stdout.write(self.style.SUCCESS(f"SHA-256      : {summary['checksum']}"))
        for metric in summary["metrics"]:
            self.stdout.write(self.style.SUCCESS(f"Metrik       : {metric}"))
