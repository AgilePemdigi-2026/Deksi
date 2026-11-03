import re
from decimal import Decimal, localcontext
from io import BytesIO
from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from indicators import bps
from indicators.models import Indicator, Observation
from indicators.provenance import matching_raw, public_source_url, source_trace_parameters
from indicators.storage import verified_raw_bytes
from indicators.updates import latest_attempt, latest_successful_update, serialize_update_log

FRONTEND_INDICATOR_CODES = ["pdb", "inflasi", "fiskal", "investasi", "birate", "tpt"]


def json_success(payload):
    response = JsonResponse(payload, safe=False)
    response["Cache-Control"] = "no-store"
    return response


def json_error(message, status=404):
    response = JsonResponse({"error": message}, status=status)
    response["Cache-Control"] = "no-store"
    return response


def get_indicator(code: str) -> Indicator | None:
    return Indicator.objects.filter(code=code).first()


def published_observations(indicator: Indicator):
    return (
        Observation.objects.filter(
            indicator=indicator,
            validation_status=Observation.Status.PUBLISHED,
            reviewed_by__isnull=False,
            reviewed_at__isnull=False,
        )
        .order_by("observation_date", "id")
        .select_related("indicator", "source", "raw_file")
    )


def latest_published(indicator: Indicator) -> Observation | None:
    observations = published_observations(indicator)
    return observations.last() if observations.exists() else None


def previous_published(latest: Observation) -> Observation | None:
    return (
        comparable_observations(latest)
        .filter(observation_date__lt=latest.observation_date)
        .order_by("-observation_date")
        .first()
    )


def comparable_observations(observation: Observation):
    return published_observations(observation.indicator).filter(
        source_id=observation.source_id, unit=observation.unit,
        frequency=observation.frequency, data_type=observation.data_type,
    )


def format_decimal(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value)


def delta_summary(latest: Observation, previous: Observation | None) -> dict:
    result = {"delta": None, "deltaDirection": None, "deltaPositive": False,
              "previousPeriod": previous.period_label if previous else None,
              "changePercentage": None, "changeValue": None, "changeUnit": None}
    if previous is None:
        return result
    rate = latest.unit.strip().casefold() in {"%", "persen", "percent"}
    if not rate and previous.value == 0:
        return result
    with localcontext() as context:
        context.prec = 60
        difference = latest.value - previous.value
        change = difference if rate else difference / abs(previous.value) * Decimal("100")
        change = change.quantize(Decimal("0.01"))
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    value = format_decimal(change)
    label = " poin persentase" if rate else "%"
    result.update(delta=f"{'+' if change > 0 else ''}{value}{label} vs {previous.period_label}",
                  deltaDirection=direction, deltaPositive=change > 0,
                  changePercentage=None if rate else float(change), changeValue=value,
                  changeUnit="percentage_point" if rate else "percent")
    return result


def serialize_summary_card(indicator: Indicator) -> dict:
    latest = latest_published(indicator)
    current_year = timezone.localdate().year
    if latest is None:
        return {
            "id": indicator.code,
            "available": False,
            "name": indicator.name,
            "category": indicator.category,
            "value": None,
            "unit": indicator.unit,
            "period": None,
            "latestPeriod": None,
            "latestYear": None,
            "hasCurrentYearData": False,
            "note": "Data belum tersedia dari sumber resmi yang terintegrasi. DEKSI tidak menampilkan angka pengganti.",
            "dataAvailabilityNote": "Data terbaru belum tersedia.",
        }
    sparkline_rows = list(
        comparable_observations(latest)
        .order_by("-observation_date")
        .values_list("value", flat=True)[:7]
    )
    sparkline = [float(value) for value in reversed(sparkline_rows)]
    delta = delta_summary(latest, previous_published(latest))
    source = latest.source
    raw = matching_raw(latest)
    has_current = latest.observation_date.year >= current_year
    return {
        "id": indicator.code,
        "available": True,
        "name": indicator.name,
        "category": indicator.category,
        "value": format_decimal(latest.value),
        "unit": latest.unit or indicator.unit,
        "period": latest.period_label,
        "latestPeriod": latest.period_label,
        "latestYear": latest.observation_date.year,
        "latestObservationDate": latest.observation_date.isoformat(),
        "hasCurrentYearData": has_current,
        "observationDate": latest.observation_date.isoformat(),
        "frequency": latest.frequency,
        "dataType": latest.data_type,
        "publicationDate": latest.publication_date.isoformat() if latest.publication_date else None,
        "source": source.institution,
        "sourceId": source.source_id,
        "retrievedAt": raw.retrieved_at.isoformat() if raw and raw.retrieved_at else None,
        "delta": delta["delta"],
        "deltaDirection": delta["deltaDirection"],
        "deltaPositive": delta["deltaPositive"],
        "changePercentage": delta.get("changePercentage"),
        "changeValue": delta["changeValue"],
        "changeUnit": delta["changeUnit"],
        "previousPeriod": delta.get("previousPeriod"),
        "sparkline": sparkline,
        "note": "Nilai dipublikasi dengan metadata sumber; publikasi bukan verifikasi independen angka.",
        "dataAvailabilityNote": (
            "Data terbaru tersedia sampai " + latest.period_label
            if not has_current
            else "Data tahun berjalan tersedia sampai " + latest.period_label
        ),
    }


@require_GET
def indicator_summary(request):
    indicators = []
    codes = request.GET.getlist("code") or FRONTEND_INDICATOR_CODES
    for code in codes:
        indicator = Indicator.objects.filter(code=code).first()
        if indicator is None:
            indicators.append({
                "id": code,
                "available": False,
                "name": code,
                "category": "",
                "value": None,
                "unit": "",
                "period": None,
                "note": "Indikator belum terdefinisi di database.",
            })
            continue
        indicators.append(serialize_summary_card(indicator))
    update = serialize_update_log(latest_successful_update())
    return json_success(
        {
            "updatedAt": update["updatedAt"] if update else None,
            "updatedAtFormatted": update["formatted"] if update else None,
            "lastUpdate": update,
            "indicators": indicators,
        }
    )


@require_GET
def latest_periods(request):
    rows = []
    for code in FRONTEND_INDICATOR_CODES:
        indicator = Indicator.objects.filter(code=code).first()
        if indicator is None:
            rows.append({"id": code, "available": False, "latestPeriod": None, "latestYear": None})
            continue
        latest = latest_published(indicator)
        rows.append(
            {
                "id": code,
                "available": latest is not None,
                "latestPeriod": latest.period_label if latest else None,
                "latestYear": latest.observation_date.year if latest else None,
                "latestObservationDate": latest.observation_date.isoformat() if latest else None,
                "hasCurrentYearData": bool(latest and latest.observation_date.year >= timezone.localdate().year),
            }
        )
    return json_success({"indicators": rows})


@require_GET
def update_status(request):
    return json_success(
        {
            "lastSuccessful": serialize_update_log(latest_successful_update()),
            "lastAttempt": serialize_update_log(latest_attempt()),
        }
    )


@require_GET
def bps_status(request):
    return json_success(bps.test_connection())


@require_GET
def system_status(request):
    return json_success(
        {
            "lastSuccessful": serialize_update_log(latest_successful_update()),
            "lastAttempt": serialize_update_log(latest_attempt()),
            "bps": bps.test_connection(),
        }
    )


GRANULARITY_LABELS = {
    "daily": "Harian",
    "monthly": "Bulanan",
    "quarterly": "Kuartalan",
    "semiannual": "Semesteran",
    "adhoc": "Peristiwa",
    "annual": "Tahunan",
}

NATIVE_NOTE = {
    "daily": "Ket: Data harian mengikuti JISDOR resmi; grafik menampilkan frekuensi sumber.",
    "monthly": "Ket: Data bulanan mengikuti publikasi resmi tanpa perubahan frekuensi.",
    "quarterly": "Ket: Data triwulanan sesuai frekuensi sumber asli BI/BKPM/BPS, tidak dipaksa menjadi bulanan.",
    "semiannual": "Ket: Data semesteran BPS (Februari/Agustus) dipertahankan sesuai publikasi sumber.",
    "adhoc": "Ket: BI-7Day-RR diumum di Rapat Diskusi Kebijakan BI; grafik menampilkan hari pengumuman.",
    "annual": "Ket: Data tahunan sesuai publikasi sumber.",
}


def year_aggregation_note(indicator: Indicator) -> str:
    if indicator.aggregation_kind == "sum":
        return "Ket: Agregasi tahunan dihitung sebagai jumlah nilai asal sejak sumber mentah (deterministik)."
    if indicator.aggregation_kind == "end":
        return "Ket: Agregasi tahunan menggunakan nilai terakhir pada tahun tersebut."
    return "Ket: Agregasi tahunan dihitung sebagai rata-rata nilai dengan frekuensi asal."


def trend_points(observs) -> list[dict]:
    return [
        {
            "label": observation.period_label,
            "value": float(observation.value),
            "exactValue": format_decimal(observation.value),
            "unit": observation.unit,
            "year": observation.observation_date.year,
            "observationDate": observation.observation_date.isoformat(),
            "frequency": observation.frequency,
            "dataType": observation.data_type,
            "sourceId": observation.source.source_id,
        }
        for observation in observs
    ]


def aggregate_trend(observations, term: str, indicator: Indicator) -> list[dict]:
    if term not in ("Tahunan", "Bulanan"):
        return trend_points(observations)
    signatures = {(o.source_id, o.unit, o.frequency, o.data_type) for o in observations}
    if len(signatures) != 1:
        raise ValueError("Agregasi ditolak: sumber, satuan, frekuensi atau jenis data tidak sebanding.")
    kind = indicator.aggregation_kind if term == "Tahunan" else "avg"
    if kind not in {"sum", "avg", "end"} or (kind == "sum" and observations[0].data_type == "cumulative_ytd"):
        raise ValueError("Metode agregasi tidak sesuai dengan jenis data.")
    buckets = {}
    for observation in observations:
        day = observation.observation_date
        key = (day.year,) if term == "Tahunan" else (day.year, day.month)
        buckets.setdefault(key, []).append(observation)
    result = []
    for key, rows in sorted(buckets.items()):
        with localcontext() as context:
            context.prec = 60
            total = sum((row.value for row in rows), Decimal(0))
            value = rows[-1].value if kind == "end" else total if kind == "sum" else total / len(rows)
            value = value.quantize(Decimal("0.01"))
        result.append({"label": str(key[0]) if len(key) == 1 else f"{key[0]}-{key[1]:02d}",
                       "value": float(value), "exactValue": format_decimal(value),
                       "year": key[0], "unit": rows[0].unit, "sourceId": rows[0].source.source_id,
                       "frequency": "annual" if term == "Tahunan" else "monthly",
                       "dataType": rows[0].data_type, "aggregationKind": kind})
    return result


@require_GET
def indicator_trend(request, code: str):
    indicator = get_indicator(code)
    if indicator is None:
        return json_error(f"Indikator '{code}' tidak ditemukan", status=404)
    observations = list(published_observations(indicator))
    if not observations:
        return json_success(
            {
                "id": indicator.code,
                "available": False,
                "granularities": [],
                "points": [],
                "latestAvailable": None,
                "dataAvailableUntil": None,
                "hasCurrentYearData": False,
                "note": "Data historis yang tervalidasi dan dipublikasi belum tersedia untuk indikator ini.",
            }
        )
    native_frequency = observations[-1].frequency
    requested = request.GET.get("granularity")
    options = [GRANULARITY_LABELS.get(native_frequency, native_frequency), "Tahunan"]
    if native_frequency == "daily":
        options.insert(1, "Bulanan")
    if requested is None:
        term = GRANULARITY_LABELS.get(native_frequency, native_frequency)
    elif requested not in options:
        return json_error(
            f"Granularitas '{requested}' tidak didukung indikator ini; pilih salah satu dari {options}",
            status=400,
        )
    else:
        term = requested
    if term == GRANULARITY_LABELS.get(native_frequency):
        points = trend_points(observations)
        note = NATIVE_NOTE.get(native_frequency, "")
    else:
        try:
            points = aggregate_trend(observations, term, indicator)
        except ValueError as exc:
            return json_error(str(exc), status=400)
        note = year_aggregation_note(indicator) if term == "Tahunan" else "Agregasi bulanan: rata-rata nilai harian."
    first = observations[0]
    latest = observations[-1]
    has_current = latest.observation_date.year >= timezone.localdate().year
    compatible = len({(o.source_id, o.unit, o.frequency, o.data_type) for o in observations}) == 1
    historical_average = None
    if compatible:
        with localcontext() as context:
            context.prec = 60
            total = sum((o.value for o in observations), Decimal(0))
            historical_average = (total / len(observations)).quantize(Decimal("0.01"))
    availability_note = (
        f"Data terbaru tersedia sampai {latest.period_label}."
        if not has_current
        else f"Data tahun berjalan tersedia sampai {latest.period_label}."
    )
    return json_success(
        {
            "id": indicator.code,
            "available": True,
            "granularities": options,
            "granularity": term,
            "unit": latest.unit or indicator.unit,
            "frequency": native_frequency,
            "dataType": latest.data_type,
            "points": points,
            "periodStart": first.observation_date.isoformat(),
            "periodEnd": latest.observation_date.isoformat(),
            "latestAvailable": latest.period_label,
            "latestYear": latest.observation_date.year,
            "hasCurrentYearData": has_current,
            "dataAvailableUntil": latest.period_label,
            "dataAvailabilityNote": availability_note,
            "historicalAverage": float(historical_average) if historical_average is not None else None,
            "historicalAverageExact": format_decimal(historical_average) if historical_average is not None else None,
            "observationCount": len(observations),
            "note": note,
        }
    )


def serialize_trace(observation: Observation) -> dict:
    raw_file = matching_raw(observation)
    trace = {
        "observationId": observation.pk,
        "available": True,
        "definition": observation.indicator.description or None,
        "revisionId": None,
        "immutableSnapshot": False,
        "officialVerification": "unassessed",
        "valueKind": "derived" if observation.data_type == Observation.DataType.DERIVED_SUM else "unclassified",
        "calculation": {"available": False, "formula": None, "inputs": None,
                        "reason": "Formula berversi dan input terikat tidak tersimpan pada observasi ini."},
        "indicatorCode": observation.indicator.code,
        "indicatorName": observation.indicator.name,
        "value": format_decimal(observation.value),
        "unit": observation.unit or observation.indicator.unit,
        "period": observation.period_label,
        "observationDate": observation.observation_date.isoformat(),
        "frequency": observation.frequency,
        "dataType": observation.data_type,
        "publicationDate": observation.publication_date.isoformat() if observation.publication_date else None,
        "validationStatus": observation.validation_status,
        "reviewedAt": observation.reviewed_at.isoformat() if observation.reviewed_at else None,
        "source": {
            "sourceId": observation.source.source_id,
            "sourceName": observation.source.source_name,
            "institution": observation.source.institution,
            "primaryUrl": public_source_url(observation.source.primary_url),
        },
    }
    if raw_file is not None:
        trace["rawFile"] = {
            "documentName": raw_file.document_name,
            "sourceUrl": public_source_url(raw_file.source_url),
            "checksumSha256": raw_file.checksum_sha256,
            "retrievedAt": raw_file.retrieved_at.isoformat() if raw_file.retrieved_at else None,
            "periodLabel": raw_file.period_label,
            "fileSizeBytes": raw_file.file_size_bytes,
            "downloadUrl": f"/api/indicators/{observation.indicator.code}/raw-file/{raw_file.id}/",
        }
    else:
        trace["rawFile"] = None
    return trace


def serialize_trace_history(indicator: Indicator, limit=100, offset=0) -> list[dict]:
    observations = (
        published_observations(indicator)
        .order_by("-observation_date", "-id")
        .select_related("source", "raw_file")
    )
    return [serialize_trace(row) for row in observations[offset:offset + limit]]


@require_GET
def indicator_source_trace(request, code: str):
    indicator = get_indicator(code)
    if indicator is None:
        return json_error(f"Indikator '{code}' tidak ditemukan", status=404)
    try:
        selector, limit, offset = source_trace_parameters(request.GET)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    rows = published_observations(indicator)
    if selector:
        matches = list(rows.filter(**selector)[:2])
        if not matches:
            return json_error("Konteks observasi tidak ditemukan; tidak dialihkan ke nilai terbaru.", status=404)
        if len(matches) != 1:
            return json_error("Konteks observasi ambigu.", status=409)
        latest = matches[0]
    else:
        latest = rows.last()
    if latest is None:
        return json_success(
            {
                "indicatorCode": code,
                "available": False,
                "note": "Observasi tervalidasi dan dipublikasi belum tersedia untuk Source Trace.",
            }
        )
    trace = serialize_trace(latest)
    trace["note"] = "Metadata publikasi bukan verifikasi kebenaran angka; checksum memeriksa integritas berkas saja."
    trace["history"] = serialize_trace_history(indicator, limit, offset)
    total = rows.count()
    trace["pagination"] = {"offset": offset, "limit": limit, "total": total, "hasMore": offset + limit < total}
    return json_success(trace)


@require_GET
def raw_file_download(request, code: str, raw_file_id: int):
    indicator = get_indicator(code)
    if indicator is None:
        raise Http404("Indikator tidak ditemukan")
    raw_file = (
        published_observations(indicator).filter(
            raw_file_id=raw_file_id,
        )
        .select_related("raw_file")
        .first()
    )
    if raw_file is None:
        raise Http404("RAW file tidak terkait data yang dipublikasi")
    if matching_raw(raw_file) is None:
        raise Http404("RAW file tidak cocok dengan sumber observasi")
    try:
        content = verified_raw_bytes(raw_file.raw_file)
    except OSError:
        raise Http404("Berkas RAW tidak tersedia") from None
    except ValueError:
        return json_error("Integritas berkas RAW tidak cocok dengan checksum SHA-256", status=503)
    name = Path(raw_file.raw_file.document_name.replace("\\", "/")).name
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip(".")[:150] or "raw"
    # Stream exactly the bounded bytes whose digest was checked, not a reopened mutable path.
    response = FileResponse(BytesIO(content), as_attachment=True, filename=filename,
                            content_type="application/octet-stream")
    response["X-Checksum-SHA256"] = raw_file.raw_file.checksum_sha256
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store"
    return response
