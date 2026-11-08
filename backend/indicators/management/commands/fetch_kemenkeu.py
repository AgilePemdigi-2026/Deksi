from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from indicators import fiscal, kemenkeu
from indicators.updates import record_update_failure


class Command(BaseCommand):
    help = (
        "Ambil PDF resmi APBN KiTa Kemenkeu, ekstraksi dengan pdftotext, simpan RAW + metadata, "
        "lalu simpan observasi kumulatif pendapatan/belanja/defisit ke database."
    )

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--url",
            action="append",
            default=None,
            dest="urls",
            help="URL PDF APBN KiTa. Dapat diulang untuk beberapa periode. Default: URL publikasi resmi terbaru.",
        )
        parser.add_argument("--username", default="admin", help="Username admin yang dicatat pada log pembaruan.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Unduh dan parse saja tanpa menulis ke database.",
        )
        parser.add_argument(
            "--scrap-dir",
            default=None,
            help="Folder arsip PDF (default: DEKSI_SCRAPING_DIR / Folder Scrapping).",
        )
        parser.add_argument(
            "--no-scrap-copy",
            action="store_true",
            help="Jangan salin PDF ke folder arsip.",
        )

    def handle(self, *args, **options):
        urls = options["urls"] or kemenkeu.DEFAULT_KITA_URLS
        if options["dry_run"]:
            self._dry_run(urls)
            return
        user_model = get_user_model()
        user = user_model.objects.filter(username=options["username"]).first()
        ok, failed = 0, 0
        for url in urls:
            self.stdout.write(f"Mengambil PDF APBN KiTa: {url}")
            try:
                summary = fiscal.ingest_kita_pdf_url(
                    url, scrap_dir=options["scrap_dir"],
                    no_scrap_copy=options["no_scrap_copy"],
                )
            except (kemenkeu.KitaError, ValidationError) as exc:
                record_update_failure("APBN KiTa Kemenkeu", updated_by=user, message=f"{url}: {exc}")
                self.stderr.write(self.style.ERROR(f"Ekstraksi dibatalkan: {exc}"))
                failed += 1
                continue
            self.stdout.write("Perubahan menunggu review Admin; data publik belum diganti.")
            self.stdout.write(self.style.SUCCESS(f"Dokumen      : {summary['document_name']}"))
            self.stdout.write(self.style.SUCCESS(f"Periode      : {summary['period_label']}"))
            self.stdout.write(self.style.SUCCESS(f"Rilis data   : {summary['publication_date']}"))
            self.stdout.write(self.style.SUCCESS(f"SHA-256      : {summary['checksum']}"))
            for metric in summary["metrics"]:
                self.stdout.write(self.style.SUCCESS(f"Metrik       : {metric}"))
            if summary.get("scrap_copy"):
                self.stdout.write(self.style.SUCCESS(f"Arsip        : {summary['scrap_copy']['pdf']}"))
            ok += 1
        self.stdout.write(f"Selesai: {ok} berhasil, {failed} gagal dari {len(urls)} URL.")
        self.stdout.write("Langkah berikut: review kandidat, lalu publikasi oleh Admin.")
        if failed:
            raise SystemExit(2)

    def _dry_run(self, urls: list[str]):
        for url in urls:
            self.stdout.write(f"[dry-run] Mengunduh: {url}")
            try:
                pdf_bytes = kemenkeu.fetch_kita_pdf(url)
                text = kemenkeu.pdf_to_text(pdf_bytes)
                parsed = kemenkeu.parse_kita_text(text, source_url=url)
            except kemenkeu.KitaError as exc:
                self.stderr.write(self.style.ERROR(f"[dry-run] Gagal: {exc}"))
                raise SystemExit(2)
            self.stdout.write(f"[dry-run] Ukuran PDF : {len(pdf_bytes)} bytes")
            self.stdout.write(f"[dry-run] Periode    : {parsed.period_label}")
            self.stdout.write(f"[dry-run] Kumulatif  : {parsed.cumulative_until}")
            for identifier, metric in parsed.metrics.items():
                self.stdout.write(f"[dry-run] Metrik     : {identifier}={metric.value} {metric.unit}")
            if parsed.cumulative_until is None:
                self.stderr.write(self.style.ERROR("[dry-run] Periode tidak teridentifikasi."))
                raise SystemExit(2)
            if not parsed.metrics:
                self.stderr.write(self.style.ERROR("[dry-run] Tidak ada metrik terparse."))
                raise SystemExit(2)
            self.stdout.write(self.style.SUCCESS("[dry-run] OK, tidak ada data ditulis."))
