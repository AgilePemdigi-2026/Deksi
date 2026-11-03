from decimal import Decimal
from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from indicators import bps
from indicators.models import Indicator, Observation, Source
from indicators.storage import compute_checksum
from indicators.updates import latest_attempt, latest_successful_update, serialize_update_log


FRONTEND_INDICATOR_CODES = ["pdb", "inflasi", "fiskal", "investasi", "birate", "tpt"]


def json_success(payload):
    response = JsonResponse(payload, safe=False)
    return response


def json_error(message, status=404):
    return JsonResponse({"error": message}, status=status)


def get_indicator(code: str) -> Indicator | None:
    return Indicator.objects.filter(code=code).first()


def published_observations(indicator: Indicator):
    return (
        Observation.objects.filter(
            indicator=indicator,
            validation_status=Observation.Status.PUBLISHED,
        )
        .order_by("observation_date")
        .select_related("source", "raw_file")
    )


def latest_published(indicator: Indicator) -> Observation | None:
    observations = published_observations(indicator)
    return observations.last() if observations.exists() else None


def previous_published(latest: Observation) -> Observation | None:
    return (
        Observation.objects.filter(
            indicator=latest.indicator,
            validation_status=Observation.Status.PUBLISHED,
            observation_date__lt=latest.observation_date,
        )
        .order_by("-observation_date")
        .first()
    )


def format_decimal(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        normalized = value.normalize()
        return f"{normalized:f}"
    return str(value)


def delta_summary(latest: Observation, previous: Observation | None) -> dict:
    if previous is None:
        return {"delta": None, "deltaDirection": None, "deltaPositive": False, "previousPeriod": None}
    denominator = abs(previous.value)
    if denominator == 0:
        change_percentage = None
    else:
        change_percentage = float(((latest.value - previous.value) / denominator * Decimal("100")).quantize(Decimal("0.01")))
    if change_percentage is None:
        delta_text = f"vs {previous.period_label}"
        direction = "flat"
        positive = False
    elif change_percentage > 0:
        delta_text = f"+{change_percentage}% vs {previous.period_label}"
        direction = "up"
        positive = True
    elif change_percentage < 0:
        delta_text = f"{change_percentage}% vs {previous.period_label}"
        direction = "down"
        positive = False
    else:
        delta_text = f"0,00% (Tetap) vs {previous.period_label}"
        direction = "flat"
        positive = False
    return {
        "delta": delta_text,
        "deltaDirection": direction,
        "deltaPositive": positive,
        "changePercentage": change_percentage,
        "previousPeriod": previous.period_label,
    }


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
        published_observations(indicator)
        .order_by("-observation_date")
        .values_list("value", flat=True)[:7]
    )
    sparkline = [float(value) for value in reversed(sparkline_rows)]
    delta = delta_summary(latest, previous_published(latest))
    source = latest.source
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
        "retrievedAt": latest.raw_file.retrieved_at.isoformat() if latest.raw_file and latest.raw_file.retrieved_at else None,
        "delta": delta["delta"],
        "deltaDirection": delta["deltaDirection"],
        "deltaPositive": delta["deltaPositive"],
        "changePercentage": delta.get("changePercentage"),
        "previousPeriod": delta.get("previousPeriod"),
        "sparkline": sparkline,
        "note": "Nilai resmi berasal dari sumber terintegrasi; daftar sumber tersedia pada Source Trace.",
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
            "unit": observation.unit,
            "year": observation.observation_date.year,
            "observationDate": observation.observation_date.isoformat(),
            "frequency": observation.frequency,
            "dataType": observation.data_type,
        }
        for observation in observs
    ]


def aggregate_trend(observations, term: str, indicator: Indicator) -> list[dict]:
    if term not in ("Tahunan", "Bulanan"):
        return trend_points(observations)
    points = trend_points(observations)
    if term == "Tahunan":
        buckets: dict[int, list[dict]] = {}
        for point in points:
            buckets.setdefault(point["year"], []).append(point)
        aggregate = []
        for year in sorted(buckets):
            entries = sorted(buckets[year], key=lambda p: p["observationDate"])
            if indicator.aggregation_kind == "sum":
                value = sum(entry["value"] for entry in entries)
            elif indicator.aggregation_kind == "end":
                value = entries[-1]["value"]
            else:
                value = sum(entry["value"] for entry in entries) / len(entries)
            aggregate.append(
                {
                    "label": str(year),
                    "value": round(value, 2),
                    "year": year,
                    "unit": entries[0]["unit"],
                }
            )
        return aggregate
    buckets: dict[tuple[int, int], list[float]] = {}
    labels = {}
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
        7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
    }
    for observation in observations:
        day = observation.observation_date
        key = (day.year, day.month)
        buckets.setdefault(key, []).append(float(observation.value))
        labels.setdefault(key, f"{month_names[key[1]]} {key[0]}")
    return [
        {
            "label": labels[key],
            "value": round(sum(values) / len(values), 2),
            "year": key[0],
            "unit": observations[0].unit,
        }
        for key in sorted(buckets)
    ]


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
    elif term == "Tahunan":
        points = aggregate_trend(observations, "Tahunan", indicator)
        note = year_aggregation_note(indicator)
    else:
        points = aggregate_trend(observations, "Bulanan", indicator)
        note = "Ket: Agregasi bulanan dihitung sebagai rata-rata nilai harian (deterministik)."
    first = observations[0]
    latest = observations[-1]
    has_current = latest.observation_date.year >= timezone.localdate().year
    historical_average = round(sum(float(observation.value) for observation in observations) / len(observations), 2)
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
            "historicalAverage": historical_average,
            "observationCount": len(observations),
            "note": note,
        }
    )


# ---------------------------------------------------------------------------
# Fitur 9: Daftar Sumber Data / Source Trace (UC-04)
# Klasifikasi nilai mengikuti data_type observasi yang tersimpan di DB.
# Hanya data_type "derived_sum" yang diperlakukan sebagai DEKSI-Derived Metric;
# sisanya (level, yoy, cumulative_ytd, event) adalah Official Source Value.
# Tidak ada formula buatan: formula hanya diisi untuk indikator derived yang
# mekanismenya terdokumentasi di pipeline ingest (BKPM realisasi investasi).
# ---------------------------------------------------------------------------

DERIVED_DATA_TYPES = {"derived_sum"}

DERIVED_FORMULAS = {
    "investasi": (
        "Total = SUM(investasi_rp_juta per baris CSV dalam ZIP triwulan) / 1.000.000 "
        "→ Rp Triliun (agregat nasional PMA + PMDN per triwulan)"
    ),
}

SOURCE_ORDER = ["BPS", "BI", "KEMENKEU", "BKPM"]


def value_type_for(observation: Observation) -> str:
    if observation.data_type in DERIVED_DATA_TYPES:
        return "DEKSI-Derived Metric"
    return "Official Source Value"


def serialize_derived(observation: Observation) -> dict | None:
    if observation.data_type not in DERIVED_DATA_TYPES:
        return None
    previous = (
        Observation.objects.filter(
            indicator=observation.indicator,
            validation_status=Observation.Status.PUBLISHED,
            observation_date__lt=observation.observation_date,
        )
        .order_by("-observation_date")
        .select_related("raw_file")
        .first()
    )
    return {
        "formula": DERIVED_FORMULAS.get(
            observation.indicator.code,
            "Agregat deterministik dari berkas RAW sumber (lihat checksum).",
        ),
        "comparisonPeriod": previous.period_label if previous else None,
        "comparisonObservationDate": previous.observation_date.isoformat() if previous else None,
        "inputValue": format_decimal(previous.value) if previous else None,
        "inputUnit": (previous.unit or previous.indicator.unit) if previous else None,
        "inputSource": previous.source.institution if previous else None,
    }


def serialize_trace(observation: Observation) -> dict:
    raw_file = observation.raw_file
    value_type = value_type_for(observation)
    publication_url = None
    if raw_file is not None and (raw_file.source_url or "").startswith("http"):
        publication_url = raw_file.source_url
    if not publication_url:
        publication_url = observation.source.primary_url or None
    trace = {
        "indicatorCode": observation.indicator.code,
        "indicatorName": observation.indicator.name,
        "valueType": value_type,
        "value": format_decimal(observation.value),
        "unit": observation.unit or observation.indicator.unit,
        "period": observation.period_label,
        "periodLabel": observation.period_label,
        "observationDate": observation.observation_date.isoformat(),
        "frequency": observation.frequency,
        "dataType": observation.data_type,
        "institution": observation.source.institution,
        "publicationName": observation.source.source_name,
        "publicationDate": observation.publication_date.isoformat() if observation.publication_date else None,
        "publicationUrl": publication_url,
        "retrievedAt": raw_file.retrieved_at.isoformat() if raw_file and raw_file.retrieved_at else None,
        "version": raw_file.checksum_sha256[:12] if raw_file else None,
        "revision": observation.validation_notes or None,
        "validationStatus": observation.validation_status,
        "reviewedAt": observation.reviewed_at.isoformat() if observation.reviewed_at else None,
        "source": {
            "sourceId": observation.source.source_id,
            "sourceName": observation.source.source_name,
            "institution": observation.source.institution,
            "primaryUrl": observation.source.primary_url,
        },
    }
    if raw_file is not None:
        trace["rawFile"] = {
            "documentName": raw_file.document_name,
            "sourceUrl": raw_file.source_url,
            "checksumSha256": raw_file.checksum_sha256,
            "retrievedAt": raw_file.retrieved_at.isoformat() if raw_file.retrieved_at else None,
            "periodLabel": raw_file.period_label,
            "fileSizeBytes": raw_file.file_size_bytes,
            "downloadUrl": f"/api/indicators/{observation.indicator.code}/raw-file/{raw_file.id}/",
        }
    else:
        trace["rawFile"] = None
    trace["derived"] = serialize_derived(observation)
    return trace


def serialize_trace_history(indicator: Indicator) -> list[dict]:
    observations = (
        published_observations(indicator)
        .order_by("-observation_date")
        .select_related("source", "raw_file")
    )
    traces = []
    seen_checksums = set()
    for observation in observations:
        trace = {**serialize_trace(observation)}
        checksum = trace.get("rawFile", {}).get("checksumSha256") if trace.get("rawFile") else None
        if checksum in seen_checksums:
            trace["rawFile"] = None
        elif checksum:
            seen_checksums.add(checksum)
        trace["value"] = format_decimal(observation.value)
        traces.append(trace)
    return traces[:12]


@require_GET
def indicator_source_trace(request, code: str):
    indicator = get_indicator(code)
    if indicator is None:
        return json_error(f"Indikator '{code}' tidak ditemukan", status=404)
    selected: Observation | None = None
    period = (request.GET.get("period") or "").strip()
    obs_date = (request.GET.get("observation_date") or "").strip()
    if period:
        selected = (
            published_observations(indicator)
            .filter(period_label=period)
            .order_by("-observation_date")
            .first()
        )
        if selected is None:
            return json_error(
                f"Periode '{period}' tidak tersedia untuk indikator '{code}'",
                status=404,
            )
    elif obs_date:
        selected = (
            published_observations(indicator)
            .filter(observation_date=obs_date)
            .first()
        )
        if selected is None:
            return json_error(
                f"Tanggal observasi '{obs_date}' tidak tersedia untuk indikator '{code}'",
                status=404,
            )
    else:
        selected = latest_published(indicator)
    if selected is None:
        return json_success(
            {
                "indicatorCode": code,
                "available": False,
                "note": "Observasi tervalidasi dan dipublikasi belum tersedia untuk Source Trace.",
            }
        )
    trace = serialize_trace(selected)
    trace["available"] = True
    trace["note"] = "Nilai berasal dari dokumen resmi institusi; checksum dipakai untuk verifikasi integritas berkas."
    trace["history"] = serialize_trace_history(indicator)
    return json_success(trace)


@require_GET
def raw_file_download(request, code: str, raw_file_id: int):
    indicator = get_indicator(code)
    if indicator is None:
        raise Http404("Indikator tidak ditemukan")
    raw_file = (
        Observation.objects.filter(
            indicator=indicator,
            validation_status=Observation.Status.PUBLISHED,
            raw_file_id=raw_file_id,
        )
        .select_related("raw_file")
        .first()
    )
    if raw_file is None:
        raise Http404("RAW file tidak terkait data yang dipublikasi")
    stored = Path(raw_file.raw_file.stored_path)
    if not stored.exists():
        raise Http404("Berkas RAW tidak tersedia")
    content = stored.read_bytes()
    if compute_checksum(content) != raw_file.raw_file.checksum_sha256:
        return json_error("Integritas berkas RAW tidak cocok dengan checksum SHA-256", status=503)
    response = FileResponse(stored.open("rb"))
    response["Content-Disposition"] = f'attachment; filename="{Path(raw_file.raw_file.document_name).name}"'
    response["X-Checksum-SHA256"] = raw_file.raw_file.checksum_sha256
    return response


def serialize_source_entry(source: Source) -> dict:
    published = Observation.objects.filter(
        source=source,
        validation_status=Observation.Status.PUBLISHED,
    ).select_related("indicator")
    indicator_ids = sorted({o.indicator.code for o in published.only("indicator__code")})
    # Hitung indikator unik + observasi tanpa memuat semua baris nilai.
    indicator_codes = list(
        published.order_by().values_list("indicator__code", flat=True).distinct()
    )
    latest = published.order_by("-observation_date").first()
    return {
        "sourceId": source.source_id,
        "sourceName": source.source_name,
        "institution": source.institution,
        "primaryUrl": source.primary_url,
        "description": source.description or "",
        "indicators": sorted(indicator_codes),
        "indicatorCount": len(indicator_codes),
        "observationCount": published.count(),
        "available": bool(latest),
        "latestPeriod": latest.period_label if latest else None,
        "latestObservationDate": latest.observation_date.isoformat() if latest else None,
        "_legacyIds": indicator_ids,
    }


def ordered_sources():
    sources = list(Source.objects.all())
    rank = {sid: i for i, sid in enumerate(SOURCE_ORDER)}
    return sorted(sources, key=lambda s: (rank.get(s.source_id, 99), s.source_id))


@require_GET
def source_list(request):
    entries = []
    for source in ordered_sources():
        entry = serialize_source_entry(source)
        entry.pop("_legacyIds", None)
        entries.append(entry)
    return json_success({"sources": entries, "count": len(entries)})


def get_source_or_404(source_id: str) -> Source | None:
    return Source.objects.filter(source_id__iexact=source_id).first()


def serialize_source_indicator(indicator: Indicator, source: Source) -> dict:
    latest = (
        Observation.objects.filter(
            indicator=indicator,
            source=source,
            validation_status=Observation.Status.PUBLISHED,
        )
        .order_by("-observation_date")
        .select_related("raw_file")
        .first()
    )
    count = Observation.objects.filter(
        indicator=indicator,
        source=source,
        validation_status=Observation.Status.PUBLISHED,
    ).count()
    if latest is None:
        return {
            "id": indicator.code,
            "code": indicator.code,
            "name": indicator.name,
            "category": indicator.category,
            "unit": indicator.unit,
            "available": False,
            "value": None,
            "period": None,
            "observationDate": None,
            "dataType": None,
            "valueType": None,
            "observationCount": count,
            "note": "Belum ada observasi terpublikasi dari sumber ini.",
        }
    return {
        "id": indicator.code,
        "code": indicator.code,
        "name": indicator.name,
        "category": indicator.category,
        "unit": latest.unit or indicator.unit,
        "available": True,
        "value": format_decimal(latest.value),
        "period": latest.period_label,
        "observationDate": latest.observation_date.isoformat(),
        "publicationDate": latest.publication_date.isoformat() if latest.publication_date else None,
        "retrievedAt": latest.raw_file.retrieved_at.isoformat()
        if latest.raw_file and latest.raw_file.retrieved_at
        else None,
        "dataType": latest.data_type,
        "valueType": value_type_for(latest),
        "observationCount": count,
    }


@require_GET
def source_detail(request, source_id: str):
    source = get_source_or_404(source_id)
    if source is None:
        return json_error(f"Sumber '{source_id}' tidak ditemukan", status=404)
    entry = serialize_source_entry(source)
    entry.pop("_legacyIds", None)
    indicator_codes = entry["indicators"]
    indicators = []
    for code in indicator_codes:
        indicator = Indicator.objects.filter(code=code).first()
        if indicator is None:
            continue
        indicators.append(serialize_source_indicator(indicator, source))
    entry["indicatorDetails"] = indicators
    return json_success(entry)


@require_GET
def source_indicators(request, source_id: str):
    source = get_source_or_404(source_id)
    if source is None:
        return json_error(f"Sumber '{source_id}' tidak ditemukan", status=404)
    codes = list(
        Observation.objects.filter(
            source=source,
            validation_status=Observation.Status.PUBLISHED,
        )
        .order_by()
        .values_list("indicator__code", flat=True)
        .distinct()
    )
    rows = []
    for code in sorted(codes):
        indicator = Indicator.objects.filter(code=code).first()
        if indicator is None:
            continue
        rows.append(serialize_source_indicator(indicator, source))
    return json_success(
        {
            "sourceId": source.source_id,
            "institution": source.institution,
            "indicators": rows,
            "count": len(rows),
        }
    )


# ---------------------------------------------------------------------------
# Fitur 5: Filter Dashboard Ekonomi
# ---------------------------------------------------------------------------

VALID_CATEGORIES = list({ind.category for ind in Indicator.objects.all()} if False else [])

INDICATOR_CATEGORY_MAP = {
    "pdb": "PDB",
    "inflasi": "Inflasi",
    "fiskal": "Fiskal",
    "investasi": "Investasi",
    "birate": "Moneter",
    "tpt": "Tenaga Kerja",
}


@require_GET
def indicator_categories(request):
    """
    GET /api/indicators/categories/

    Mengembalikan daftar kategori beserta daftar kode indikator yang tersedia
    di tiap kategori.  Digunakan front-end untuk mengisi kontrol filter.
    """
    categories: dict[str, list[str]] = {}
    for code in FRONTEND_INDICATOR_CODES:
        cat = INDICATOR_CATEGORY_MAP.get(code, "Lainnya")
        categories.setdefault(cat, []).append(code)
    result = [
        {"category": cat, "codes": codes}
        for cat, codes in categories.items()
    ]
    return json_success({"categories": result})


@require_GET
def indicator_dashboard_filter(request):
    """
    GET /api/indicators/dashboard/

    Query params:
      category (str)  – nama kategori, mis. "PDB" atau "Inflasi"
      year     (int)  – tahun pengamatan, mis. 2024

    Mengembalikan payload yang sama dengan indicator_summary, namun disaring
    berdasarkan parameter yang diberikan.  Jika tidak ada parameter, perilaku
    identik dengan indicator_summary tanpa filter.
    """
    raw_category = request.GET.get("category", "").strip()
    raw_year = request.GET.get("year", "").strip()

    # Validasi tahun
    if raw_year:
        if not raw_year.isdigit():
            return json_error("Parameter 'year' harus berupa angka bulat positif.", status=400)
        filter_year = int(raw_year)
    else:
        filter_year = None

    # Tentukan kode yang akan dikembalikan
    if raw_category:
        codes = [
            code
            for code, cat in INDICATOR_CATEGORY_MAP.items()
            if cat.lower() == raw_category.lower()
        ]
        if not codes:
            return json_error(
                f"Kategori '{raw_category}' tidak dikenal. "
                f"Pilihan yang tersedia: {sorted(set(INDICATOR_CATEGORY_MAP.values()))}",
                status=400,
            )
    else:
        codes = list(request.GET.getlist("code") or FRONTEND_INDICATOR_CODES)

    indicators = []
    for code in codes:
        indicator = Indicator.objects.filter(code=code).first()
        if indicator is None:
            indicators.append({
                "id": code,
                "available": False,
                "name": code,
                "category": INDICATOR_CATEGORY_MAP.get(code, ""),
                "value": None,
                "unit": "",
                "period": None,
                "note": "Indikator belum terdefinisi di database.",
            })
            continue

        card = serialize_summary_card(indicator)

        # Terapkan filter tahun jika diminta
        if filter_year is not None and card.get("latestYear") != filter_year:
            # Cari observasi terakhir pada tahun yang diminta
            obs_in_year = (
                Observation.objects.filter(
                    indicator=indicator,
                    validation_status=Observation.Status.PUBLISHED,
                    observation_date__year=filter_year,
                )
                .order_by("-observation_date")
                .select_related("source", "raw_file")
                .first()
            )
            if obs_in_year is None:
                card = {
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
                    "note": f"Data tahun {filter_year} belum tersedia dari sumber resmi.",
                    "dataAvailabilityNote": f"Tidak ada data dipublikasi untuk tahun {filter_year}.",
                }
            else:
                prev = (
                    Observation.objects.filter(
                        indicator=indicator,
                        validation_status=Observation.Status.PUBLISHED,
                        observation_date__lt=obs_in_year.observation_date,
                    )
                    .order_by("-observation_date")
                    .first()
                )
                delta = delta_summary(obs_in_year, prev)
                card.update({
                    "value": format_decimal(obs_in_year.value),
                    "period": obs_in_year.period_label,
                    "latestPeriod": obs_in_year.period_label,
                    "latestYear": obs_in_year.observation_date.year,
                    "observationDate": obs_in_year.observation_date.isoformat(),
                    "delta": delta["delta"],
                    "deltaDirection": delta["deltaDirection"],
                    "deltaPositive": delta["deltaPositive"],
                })

        indicators.append(card)

    # Metadata filter aktif yang diteruskan ke front-end
    active_filters: dict = {}
    if raw_category:
        active_filters["category"] = raw_category
    if filter_year is not None:
        active_filters["year"] = filter_year

    update = serialize_update_log(latest_successful_update())
    return json_success({
        "updatedAt": update["updatedAt"] if update else None,
        "updatedAtFormatted": update["formatted"] if update else None,
        "lastUpdate": update,
        "activeFilters": active_filters,
        "indicators": indicators,
    })
