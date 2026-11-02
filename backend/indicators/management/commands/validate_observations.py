from django.core.management.base import BaseCommand

from indicators.models import Observation
from indicators.validate import validate_one


def validate_all() -> dict:
    validated = 0
    rejected = 0
    inspected = 0
    for observation in Observation.objects.filter(
        validation_status=Observation.Status.PENDING
    ).select_related("indicator"):
        inspected += 1
        problem = validate_one(observation)
        if problem is None:
            observation.validation_status = Observation.Status.VALIDATED
            observation.validation_notes = ""
            validated += 1
        else:
            observation.validation_status = Observation.Status.REJECTED
            observation.validation_notes = problem
            rejected += 1
        observation.save(update_fields=["validation_status", "validation_notes"])
    return {"inspected": inspected, "validated": validated, "rejected": rejected}


class Command(BaseCommand):
    help = "Validasi seluruh observasi pending: rentang nilai, satuan, dan periode."

    def handle(self, *args, **options):
        summary = validate_all()
        self.stdout.write(
            f"Periksa {summary['inspected']} observasi: {summary['validated']} tervalidasi, "
            f"{summary['rejected']} ditolak."
        )
