"""Reviewed candidate writes; importers never replace the public observation."""
import hashlib
import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from indicators.models import Indicator, Observation, ObservationCandidate, RawFile, Source
from indicators.updates import record_update_success
from indicators.validate import validate_one

FACT_FIELDS = ("indicator_id", "source_id", "observation_date", "period_label", "frequency", "data_type",
               "value", "unit", "publication_date", "raw_file_id")
SOURCE_FIELDS = ("id", "source_id", "source_name", "institution", "primary_url", "description")
INDICATOR_FIELDS = ("id", "code", "name", "category", "unit", "description", "footnote",
                    "aggregation_kind", "sort_order")
RAW_FIELDS = ("id", "source_id", "document_name", "source_url", "period_label", "retrieved_at",
              "checksum_sha256", "file_size_bytes")


def _json_value(value):
    if isinstance(value, Decimal):
        return format(value.quantize(Decimal("0.000001")), "f")
    return value.isoformat() if hasattr(value, "isoformat") else value


def _facts(row):
    return {key: _json_value(getattr(row, key)) for key in FACT_FIELDS}


def _digest(payload, base):
    text = json.dumps({"payload": payload, "base": base}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def _raw_snapshot(pk):
    row = RawFile.objects.filter(pk=pk).values(*RAW_FIELDS).first() if pk else None
    return {key: _json_value(value) for key, value in row.items()} if row else None


def _state(payload):
    indicator = Indicator.objects.select_for_update().values(*INDICATOR_FIELDS).get(pk=payload["indicator_id"])
    source = Source.objects.select_for_update().values(*SOURCE_FIELDS).get(pk=payload["source_id"])
    row = Observation.objects.select_for_update().filter(
        indicator_id=payload["indicator_id"], source_id=payload["source_id"],
        observation_date=payload["observation_date"], data_type=payload["data_type"],
    ).first()
    current = None if row is None else {**_facts(row), "id": row.pk,
        "validation_status": row.validation_status, "reviewed_by_id": row.reviewed_by_id,
        "reviewed_at": _json_value(row.reviewed_at), "validation_notes": row.validation_notes}
    return {"observation": current, "indicator": indicator, "source": source,
            "candidate_raw": _raw_snapshot(payload["raw_file_id"]),
            "previous_raw": _raw_snapshot(row.raw_file_id if row else None)}


def _validated_row(payload):
    if set(payload) != set(FACT_FIELDS):
        raise ValidationError("Struktur kandidat tidak sesuai kontrak.")
    fields = dict(payload)
    for key in ["observation_date", "publication_date"]:
        if isinstance(fields[key], str):
            fields[key] = date.fromisoformat(fields[key])
    row = Observation(**fields)
    row.full_clean(validate_unique=False, validate_constraints=False)
    if row.raw_file_id and row.raw_file.source_id != row.source_id:
        raise ValidationError("RAW kandidat tidak berasal dari sumber yang sama.")
    return row


@transaction.atomic
def stage_observation(*, indicator_id, source_id, observation_date, period_label, frequency, value, unit,
                      data_type="level", publication_date=None, raw_file_id=None):
    payload = {"indicator_id": indicator_id, "source_id": source_id, "observation_date": observation_date,
        "period_label": period_label, "frequency": frequency, "data_type": data_type, "value": value, "unit": unit,
        "publication_date": publication_date, "raw_file_id": raw_file_id}
    payload = _facts(_validated_row(payload))
    base = _state(payload)
    previous = base["observation"]
    if (previous and previous["validation_status"] == Observation.Status.PUBLISHED
            and previous["reviewed_by_id"] is not None and previous["reviewed_at"] is not None
            and {key: previous[key] for key in FACT_FIELDS} == payload):
        return None
    candidate, _ = ObservationCandidate.objects.get_or_create(fingerprint=_digest(payload, base),
        defaults={"indicator_id": indicator_id, "source_id": source_id,
                  "payload": payload, "base_snapshot": base})
    return candidate


class CandidateConflictError(ValidationError):
    pass


@transaction.atomic
def ensure_import_master(model, *, defaults, **lookup):
    obj, created = model.objects.get_or_create(defaults=defaults, **lookup)
    if created:
        obj.full_clean()
    elif any(getattr(obj, key) != value for key, value in defaults.items()):
        raise CandidateConflictError(f"Metadata {model.__name__} berbeda; review konfigurasi Admin diperlukan.")
    return obj


def require_reviewer(user, permission="indicators.change_observationcandidate"):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "pk", None):
        raise PermissionDenied("Review memerlukan Admin.")
    # Re-read authorization rather than trusting a previously cached permission or active flag.
    user = get_user_model().objects.get(pk=user.pk)
    if not user.is_active or not user.is_staff or not user.has_perm(permission):
        raise PermissionDenied("Admin tidak memiliki izin review ini.")
    return user


@transaction.atomic
def review_candidate(candidate_id, user, *, publish=True, notes=""):
    user = require_reviewer(user)
    candidate = ObservationCandidate.objects.select_for_update().get(pk=candidate_id)
    payload, base = candidate.payload, candidate.base_snapshot
    if (candidate.fingerprint != _digest(payload, base) or candidate.indicator_id != payload.get("indicator_id")
            or candidate.source_id != payload.get("source_id")):
        raise CandidateConflictError("Fakta kandidat berubah; impor ulang untuk review baru.")
    if candidate.status != ObservationCandidate.Status.PENDING:
        raise CandidateConflictError("Kandidat telah diproses.")
    row = None
    if publish:
        row = _validated_row(payload)
        problem = validate_one(row)
        if problem:
            raise ValidationError(problem)
        if _state(payload) != base:
            raise CandidateConflictError("Basis kandidat telah berubah; impor ulang sebelum review.")
    now = timezone.now()
    claimed = ObservationCandidate.objects.filter(pk=candidate.pk, status="pending",
        fingerprint=candidate.fingerprint).update(status="published" if publish else "rejected",
            reviewed_by=user, reviewed_at=now, review_notes=notes)
    if claimed != 1:
        raise CandidateConflictError("Kandidat diproses oleh review lain.")
    if not publish:
        return None
    new_fields = {**payload, "validation_status": Observation.Status.PUBLISHED,
                  "reviewed_by_id": user.pk, "reviewed_at": now, "validation_notes": ""}
    previous = base["observation"]
    if previous:
        from datetime import datetime as _datetime

        # Filter konkuren hanya pada kunci + field kontrol kelayakan
        # publikasi. Field fakta tidak ikut: kesetaraannya sudah diverifikasi
        # di atas dalam transaksi yang sama (baris terkunci select_for_update),
        # dan representasi desimal JSON ("4.940000") vs SQLite TEXT ("4.94")
        # membuat filter tekstual gagal walau nilainya sama.
        expected = {
            "pk": previous["id"],
            "validation_status": previous["validation_status"],
            "reviewed_by_id": previous["reviewed_by_id"],
            "validation_notes": previous["validation_notes"],
        }
        if previous.get("reviewed_at") is None:
            expected["reviewed_at__isnull"] = True
        elif isinstance(previous["reviewed_at"], str):
            expected["reviewed_at"] = _datetime.fromisoformat(previous["reviewed_at"])
        else:
            expected["reviewed_at"] = previous["reviewed_at"]
        if Observation.objects.filter(**expected).update(**new_fields) != 1:
            raise CandidateConflictError("Observasi berubah saat publikasi; tidak ada data yang diganti.")
        row = Observation.objects.get(pk=previous["id"])
    else:
        row.validation_status, row.reviewed_by, row.reviewed_at = Observation.Status.PUBLISHED, user, now
        try:
            with transaction.atomic():
                row.save(force_insert=True)
        except IntegrityError as exc:
            raise CandidateConflictError("Observasi sudah dibuat oleh review lain.") from exc
    record_update_success(row.source.institution, updated_by=user, observation_count=1,
                          message=f"Publikasi kandidat {candidate.pk} melalui review Admin.")
    return row
