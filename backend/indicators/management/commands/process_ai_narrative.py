"""Explicit one-shot narrative operator; never a scheduler or implicit provider probe."""
from django.core.management.base import BaseCommand, CommandError

from indicators.ai_narrative import run_once
from indicators.ai_narrative_policy import NarrativeError


class Command(BaseCommand):
    help = 'Proses maksimal satu draft narasi. Memerlukan konfigurasi dan izin operasi terpisah.'

    def create_parser(self, *args, **kwargs):
        kwargs['allow_abbrev'] = False
        return super().create_parser(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', required=True)

    def handle(self, *args, **options):
        try:
            draft = run_once()
        except NarrativeError as error:
            raise CommandError(str(error)) from None
        if draft is None:
            self.stdout.write('Tidak ada draft antre yang diproses.')
        else:
            self.stdout.write(f'Draft {draft.pk}: {draft.generation_status}. Belum dipublikasikan.')
            if draft.generation_status != 'ready':
                raise CommandError('Draft belum siap ditinjau. Periksa status tanpa mengulang otomatis.')
