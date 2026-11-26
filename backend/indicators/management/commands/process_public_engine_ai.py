from django.core.management.base import BaseCommand, CommandError

from indicators.public_engine_ai import run_once


class Command(BaseCommand):
    help = 'Process at most one explicitly queued public engine AI request.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', required=True)

    def handle(self, *args, **options):
        if not options['once']:
            raise CommandError('Only one-shot processing is supported; do not automatically retry unknown outcomes.')
        row = run_once()
        if row is None:
            self.stdout.write('No request claimed (worker may be disabled or queue empty).')
        else:
            self.stdout.write(f'Request {row.pk}: {row.status}; result digest {row.result_digest}.')
