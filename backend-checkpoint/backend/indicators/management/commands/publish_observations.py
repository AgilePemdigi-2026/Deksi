from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from indicators.lifecycle import require_reviewer, review_candidate
from indicators.models import ObservationCandidate


class Command(BaseCommand):
    help = "Review dan publikasikan hanya ID kandidat terpilih menggunakan Admin existing."

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--username", required=True, help="Username Admin existing yang melakukan review")
        parser.add_argument("--candidate-id", dest="candidate_ids", type=int, action="append", required=True,
                            help="ID kandidat; ulangi opsi untuk memilih beberapa kandidat secara eksplisit")

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        selected = options["candidate_ids"]
        if not selected or len(set(selected)) != len(selected):
            raise CommandError("Pilih ID kandidat yang unik secara eksplisit.")
        try:
            user = require_reviewer(user)
            for pk in selected:
                review_candidate(pk, user)
        except (PermissionDenied, ValidationError, ObservationCandidate.DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Review Admin: {len(selected)} kandidat dipublikasikan.")
