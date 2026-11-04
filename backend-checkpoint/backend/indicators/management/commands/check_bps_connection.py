from django.core.management.base import BaseCommand

from indicators import bps


class Command(BaseCommand):
    help = "Uji koneksi ke WebAPI BPS memakai BPS_API_KEY dari backend/.env."

    def handle(self, *args, **options):
        result = bps.test_connection()
        if result["connected"]:
            self.stdout.write(self.style.SUCCESS(result["message"]))
            self.stdout.write(f"Domain provinsi terbaca: {result.get('domains')}")
            self.stdout.write(f"Latensi: {result.get('latencyMs')} ms")
            return
        self.stderr.write(self.style.ERROR(result["message"]))
        raise SystemExit(2)
