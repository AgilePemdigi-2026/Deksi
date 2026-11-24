from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from indicators import fiscal, kemenkeu
from indicators.kemenkeu_discovery import DEFAULT_ARCHIVE_URLS, discover_kita_urls
from indicators.models import Source
from indicators.source_status import InactiveSourceError, require_active_source
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
        parser.add_argument(
            "--discover",
            action="store_true",
            help="Temukan PDF KiTa via BeautifulSoup dari halaman arsip resmi, lalu ingest semuanya.",
        )
        parser.add_argument(
            "--years",
            type=int,
            default=10,
            choices=[5, 10],
            help="Rentang arsip saat --discover: 5 atau 10 tahun kebelakang (default 10).",
        )
        parser.add_argument(
            "--max-items",
            type=int,
            default=120,
            help="Batas jumlah PDF saat --discover (default 120).",
        )
        parser.add_argument(
            "--base-url",
            action="append",
            default=None,
            dest="base_urls",
            help="Halaman arsip resmi untuk discovery fallback. Dapat diulang. Default: DJPPR + kemenkeu.go.id.",
        )
        parser.add_argument(
            "--keyword",
            default="kita",
            help="Kata kunci pencarian arsip anggaran (default: kita).",
        )
        parser.add_argument(
            "--from-dir",
            default=None,
            help="Ingest PDF KiTa lokal dari folder (mis. Folder Scrapping) tanpa mengunduh.",
        )

    def handle(self, *args, **options):
        source = Source.objects.filter(source_id="KEMENKEU").first()
        if source is not None:
            try:
                require_active_source(source)
            except InactiveSourceError as exc:
                self.stdout.write(self.style.WARNING(str(exc)))
                return
        urls = options["urls"] or kemenkeu.DEFAULT_KITA_URLS
        if options.get("discover"):
            bases = options.get("base_urls") or DEFAULT_ARCHIVE_URLS
            from indicators.kemenkeu_discovery import discover_via_anggaran_search

            found = discover_via_anggaran_search(
                keyword=options.get("keyword") or "kita",
                years_back=options.get("years") or 10,
                max_items=options.get("max_items") or 120,
            )
            if not found:
                found = discover_kita_urls(
                    base_urls=bases,
                    years_back=options.get("years") or 10,
                    max_items=options.get("max_items") or 120,
                )
            urls = [d["url"] for d in found]
            self.stdout.write(
                f"Discovery: {len(urls)} PDF KiTa dari {len(bases)} halaman arsip "
                f"({options.get('years') or 10} tahun kebelakang)."
            )
            for item in found[:20]:
                label = f"{item.get('year') or '?'} - {item.get('title')[:80]}"
                self.stdout.write(f"  - {label}\n    {item['url']}")
            if len(found) > 20:
                self.stdout.write(f"  ... dan {len(found) - 20} lainnya.")
            if not urls:
                self.stderr.write(self.style.ERROR("Discovery tidak menemukan PDF KiTa."))
                raise SystemExit(2)
        if options.get("from_dir"):
            self._ingest_local_dir(
                options["from_dir"],
                dry_run=bool(options["dry_run"]),
                username=options["username"],
                scrap_dir=options["scrap_dir"],
                no_scrap_copy=options["no_scrap_copy"],
            )
            return
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
            except InactiveSourceError as exc:
                self.stdout.write(self.style.WARNING(str(exc)))
                break
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

    def _ingest_local_dir(self, directory: str, *, dry_run: bool, username: str,
                           scrap_dir=None, no_scrap_copy: bool = False):
        from pathlib import Path

        target = Path(directory)
        pdfs = sorted(target.glob("kita-apbn-*.pdf")) or sorted(target.glob("*.pdf"))
        if not pdfs:
            self.stderr.write(self.style.ERROR(f"Tidak ada PDF KiTa di: {target}"))
            raise SystemExit(2)
        user_model = get_user_model()
        user = user_model.objects.filter(username=username).first()
        ok, failed = 0, 0
        for path in pdfs:
            label = f"[dry-run] {path.name}" if dry_run else str(path)
            self.stdout.write(label)
            try:
                pdf_bytes = path.read_bytes()
                if dry_run:
                    text = kemenkeu.pdf_to_text(pdf_bytes)
                    parsed = kemenkeu.parse_kita_text(text, source_url=path.name)
                else:
                    summary = fiscal.ingest_kita_pdf_bytes(
                        pdf_bytes, path.name,
                        scrap_dir=scrap_dir, no_scrap_copy=True,
                    )
                    parsed = None
            except InactiveSourceError as exc:
                self.stdout.write(self.style.WARNING(str(exc)))
                break
            except (kemenkeu.KitaError, ValidationError) as exc:
                self.stderr.write(self.style.ERROR(f"Gagal: {exc}"))
                if not dry_run:
                    record_update_failure("APBN KiTa Kemenkeu", updated_by=user,
                                          message=f"{path.name}: {exc}")
                failed += 1
                continue
            if dry_run:
                self.stdout.write(f"[dry-run] Periode    : {parsed.period_label}")
                for identifier, metric in parsed.metrics.items():
                    self.stdout.write(f"[dry-run] Metrik     : {identifier}={metric.value} {metric.unit}")
                if parsed.cumulative_until is None or not parsed.metrics:
                    self.stderr.write(self.style.ERROR("[dry-run] Tidak lengkap, dilewati."))
                    failed += 1
                    continue
                ok += 1
                continue
            self.stdout.write("Perubahan menunggu review Admin; data publik belum diganti.")
            for metric in summary["metrics"]:
                self.stdout.write(self.style.SUCCESS(f"Metrik       : {metric}"))
            ok += 1
        self.stdout.write(f"Selesai: {ok} berhasil, {failed} gagal dari {len(pdfs)} berkas.")
        if failed:
            raise SystemExit(2)

    def _dry_run(self, urls: list[str]):
        ok, failed = 0, 0
        for url in urls:
            self.stdout.write(f"[dry-run] Mengunduh: {url}")
            try:
                pdf_bytes = kemenkeu.fetch_kita_pdf(url)
                text = kemenkeu.pdf_to_text(pdf_bytes)
                parsed = kemenkeu.parse_kita_text(text, source_url=url)
            except kemenkeu.KitaError as exc:
                self.stderr.write(self.style.ERROR(f"[dry-run] Gagal: {exc}"))
                failed += 1
                continue
            self.stdout.write(f"[dry-run] Ukuran PDF : {len(pdf_bytes)} bytes")
            self.stdout.write(f"[dry-run] Periode    : {parsed.period_label}")
            self.stdout.write(f"[dry-run] Kumulatif  : {parsed.cumulative_until}")
            for identifier, metric in parsed.metrics.items():
                self.stdout.write(f"[dry-run] Metrik     : {identifier}={metric.value} {metric.unit}")
            if parsed.cumulative_until is None:
                self.stderr.write(self.style.ERROR("[dry-run] Periode tidak teridentifikasi."))
                failed += 1
                continue
            if not parsed.metrics:
                self.stderr.write(self.style.ERROR("[dry-run] Tidak ada metrik terparse."))
                failed += 1
                continue
            self.stdout.write(self.style.SUCCESS("[dry-run] OK, tidak ada data ditulis."))
            ok += 1
        self.stdout.write(f"[dry-run] Selesai: {ok} berhasil, {failed} gagal dari {len(urls)} URL.")
        if failed:
            raise SystemExit(2)
