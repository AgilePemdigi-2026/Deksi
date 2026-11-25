"""Deterministic BPS GDP ratios, qualified against selected source excerpts."""
import hashlib
import json
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext

from indicators.bps import MONTHS_ID
from indicators.models import Observation
from indicators.provenance import matching_raw
from indicators.storage import verified_raw_bytes

METRICS = {
    "pmtb_share": ("pmtb_nominal", "Porsi PMTB terhadap PDB"),
    "household_consumption_share": ("konsumsi_rumah_tangga", "Porsi konsumsi rumah tangga terhadap PDB"),
}
GDP_COMPONENTS = {"pdb_nominal": 800, "pmtb_nominal": 400, "konsumsi_rumah_tangga": 100}
SCHEMA_VERSION = "deksi.economic-engine.v1"
METHOD_VERSION = "bps-gdp-shares.v3"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate source field")
        result[key] = value
    return result


def _bound_excerpt(row, content):
    """Match the importer's excerpt; integrity alone does not qualify a calculation."""
    try:
        if len(content) > 128 * 1024:
            return False
        data = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_pairs)
        fields = {"kind", "var_id", "vervar", "turvar", "th_id", "year", "turth_id", "datacontent"}
        if type(data) is not dict or set(data) != fields:
            return False
        if any(type(data[key]) is not int for key in fields - {"kind", "datacontent"}):
            return False
        if (data["kind"] != "bps_selected_datacontent_excerpt" or data["var_id"] != 1955
                or data["vervar"] != GDP_COMPONENTS[row.indicator.code] or data["turvar"] != 0
                or data["year"] != row.observation_date.year or data["th_id"] < 0
                or data["turth_id"] != {3: 31, 6: 32, 9: 33, 12: 34}[row.observation_date.month]):
            return False
        key = f"{data['vervar']}{data['var_id']}{data['turvar']}{data['th_id']}{data['turth_id']}"
        if type(data["datacontent"]) is not dict or set(data["datacontent"]) != {key}:
            return False
        text = data["datacontent"][key]
        if not isinstance(text, str) or len(text) > 100:
            return False
        value = Decimal(text)
        return value.is_finite() and value == row.value
    except (KeyError, TypeError, ValueError, UnicodeError, InvalidOperation, RecursionError):
        return False


def calculate_gdp_shares(period_end: date) -> dict:
    """Calculate for a specific quarter; never mix dates or expose pending rows."""
    if (not isinstance(period_end, date) or period_end.month not in (3, 6, 9, 12)
            or period_end.day != monthrange(period_end.year, period_end.month)[1]):
        raise ValueError("Periode harus tanggal akhir triwulan.")
    period = f"Q{period_end.month // 3} {period_end.year}"
    codes = ["pdb_nominal", *(metric[0] for metric in METRICS.values())]
    rows = Observation.objects.filter(
        indicator__code__in=codes, source__source_id="BPS", observation_date=period_end,
        validation_status=Observation.Status.PUBLISHED, reviewed_by__isnull=False, reviewed_at__isnull=False,
    ).select_related("indicator", "source", "raw_file").order_by("id")
    by_code = {}
    for row in rows:
        by_code.setdefault(row.indicator.code, []).append(row)
    results = {}
    for metric_id, (numerator_code, title) in METRICS.items():
        result = {"id": metric_id, "name": title, "available": False, "value": None, "unit": "%",
                  "period": period, "observationDate": period_end.isoformat(),
                  "classification": "DEKSI-derived", "formula": f"{numerator_code} / pdb_nominal * 100",
                  "formulaVersion": "2", "schemaVersion": SCHEMA_VERSION, "methodVersion": METHOD_VERSION,
                  "roundingMode": "ROUND_HALF_EVEN", "decimalPlaces": 2,
                  "officialVerification": "unassessed", "snapshotPersistence": "response_only",
                  "revisionStatus": "unknown",
                  "revisionNote": "Status revisi belum diketahui; angka dapat direvisi.",
                  "priceBasis": None, "inputs": {}, "reason": None, "reasonCode": "unqualified_input",
                  "note": ("Perhitungan DEKSI dari data BPS. Pemetaan seri mengasumsikan harga berlaku; "
                           "dasar harga pada tiap observasi belum tersedia untuk diverifikasi.")}
        groups = {code: by_code.get(code, []) for code in (numerator_code, "pdb_nominal")}
        if any(not group for group in groups.values()):
            result["reason"] = "Data dipublikasi dan direview untuk periode ini belum lengkap."
        elif any(len(group) != 1 for group in groups.values()):
            result["reason"] = "Input memiliki lebih dari satu observasi untuk periode ini."
        else:
            inputs = {code: group[0] for code, group in groups.items()}
            _calculate_result(result, inputs, numerator_code, period)
        if result["available"]:
            result["reasonCode"] = None
        candidate_identity = {code: [{"id": row.pk, "value": str(row.value), "unit": row.unit,
            "period": row.period_label, "date": row.observation_date.isoformat(), "frequency": row.frequency,
            "dataType": row.data_type, "source": row.source.source_id, "rawFileId": row.raw_file_id,
            "reviewedAt": row.reviewed_at.isoformat()} for row in group] for code, group in groups.items()}
        result["inputDigest"] = _digest({"method": METHOD_VERSION, "period": period,
            "candidates": candidate_identity, "inputs": result["inputs"]})
        result["resultDigest"] = _digest(result)
        results[metric_id] = result
    return results


def _calculate_result(result, inputs, numerator_code, period):
    from indicators.views import serialize_trace

    if any(not row.value.is_finite() for row in inputs.values()):
        result["reason"] = "Nilai input bukan angka hingga yang dapat dihitung."
    elif any(row.frequency != "quarterly" or row.data_type != "level" or row.unit != "Rp miliar"
           or row.period_label != period for row in inputs.values()):
        result["reason"] = "Satuan, tipe data, frekuensi, atau label periode input tidak cocok."
    elif inputs["pdb_nominal"].value <= 0:
        result["reason"] = "PDB nominal harus lebih besar dari nol."
    elif inputs[numerator_code].value < 0:
        result["reason"] = "Nilai komponen nominal tidak boleh negatif."
    else:
        for code, row in inputs.items():
            raw = matching_raw(row)
            evidence = "missing"
            binding = "unavailable"
            if raw is not None:
                try:
                    content = verified_raw_bytes(raw)
                    evidence = "integrity_ok"
                    binding = "matched" if _bound_excerpt(row, content) else "mismatch"
                except (OSError, ValueError):
                    evidence = "unavailable_or_invalid"
            result["inputs"][code] = {"observationId": row.pk, "value": str(row.value), "unit": row.unit,
                                      "sourceId": row.source.source_id, "period": row.period_label,
                                      "observationDate": row.observation_date.isoformat(),
                                      "frequency": row.frequency, "dataType": row.data_type,
                                      "evidenceStatus": evidence, "bindingStatus": binding,
                                      "evidenceChecksumSha256": raw.checksum_sha256 if raw is not None else None,
                                      "trace": serialize_trace(row),
                                      "publicationDate": (row.publication_date.isoformat()
                                                          if row.publication_date else None)}
        if any(value["bindingStatus"] != "matched" for value in result["inputs"].values()):
            result["reasonCode"] = "input_evidence_unqualified"
            result["reason"] = "RAW belum cocok dengan identitas, periode dan nilai input yang dipilih."
            return
        result["priceBasis"] = "current_prices"
        result["note"] = ("Perhitungan DEKSI memakai pemetaan PDB pengeluaran harga berlaku BPS. "
                          "Excerpt terpilih dan checksum bukan bukti verifikasi independen atau respons HTTP lengkap.")
        with localcontext() as context:
            context.prec = 60
            context.rounding = ROUND_HALF_EVEN
            result["value"] = str((inputs[numerator_code].value / inputs["pdb_nominal"].value * 100)
                                  .quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
        result["available"] = True


def calculate_goods_trade(period_end: date) -> dict:
    """Provisional comparison only; source-method compatibility still needs review."""
    if not isinstance(period_end, date) or period_end.day != monthrange(period_end.year, period_end.month)[1]:
        raise ValueError("Periode harus tanggal akhir bulan.")
    period = f"{MONTHS_ID[period_end.month]} {period_end.year}"
    codes = ("ekspor_barang", "impor_barang")
    rows = Observation.objects.filter(
        indicator__code__in=codes, source__source_id="BPS", observation_date=period_end,
        validation_status=Observation.Status.PUBLISHED, reviewed_by__isnull=False, reviewed_at__isnull=False,
    ).select_related("indicator", "source")
    groups = {code: [] for code in codes}
    for row in rows:
        groups[row.indicator.code].append(row)
    definitions = {
        "goods_trade_balance": ("Selisih ekspor dan impor barang", "ekspor_barang - impor_barang", "US$ juta"),
        "goods_export_import_ratio": ("Rasio ekspor terhadap impor barang", "ekspor_barang / impor_barang * 100", "%"),
    }
    results = {}
    for key, (name, formula, unit) in definitions.items():
        result = {"id": key, "name": name, "available": False, "value": None, "unit": unit,
                  "period": period, "observationDate": period_end.isoformat(), "classification": "DEKSI-derived",
                  "formula": formula, "formulaVersion": "1", "inputs": {}, "reason": None,
                  "note": "Pratinjau saja: cakupan dan basis penilaian seri ekspor/impor belum dipastikan sebanding."}
        if any(len(group) == 0 for group in groups.values()):
            result["reason"] = "Data dipublikasi dan direview untuk periode ini belum lengkap."
        elif any(len(group) != 1 for group in groups.values()):
            result["reason"] = "Input memiliki lebih dari satu observasi untuk periode ini."
        else:
            inputs = {code: group[0] for code, group in groups.items()}
            if any(row.frequency != "monthly" or row.data_type != "level" or row.unit != "US$ juta"
                   or row.period_label != period or row.value < 0 for row in inputs.values()):
                result["reason"] = "Satuan, tipe data, periode, atau nilai input tidak sesuai."
            elif key == "goods_export_import_ratio" and inputs["impor_barang"].value == 0:
                result["reason"] = "Nilai impor nol, rasio tidak dapat dihitung."
            else:
                for code, row in inputs.items():
                    result["inputs"][code] = {"observationId": row.pk, "value": str(row.value), "unit": row.unit,
                                              "sourceId": row.source.source_id, "period": row.period_label,
                                              "observationDate": row.observation_date.isoformat(),
                                              "publicationDate": (row.publication_date.isoformat()
                                                                  if row.publication_date else None)}
                with localcontext() as context:
                    context.prec = 60
                    export, imported = inputs["ekspor_barang"].value, inputs["impor_barang"].value
                    value = export - imported if key == "goods_trade_balance" else export / imported * Decimal(100)
                    result["value"] = str(value.quantize(Decimal("0.01")))
                result["available"] = True
        results[key] = result
    return results
