"""Public provenance boundary helpers; source URLs are metadata, never fetched."""
import re
from datetime import date
from urllib.parse import urlsplit

from indicators.models import Observation


def public_source_url(value):
    if not value or value != value.strip() or "\\" in value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            return None
        if url.port is not None and not 0 < url.port < 65536:
            return None
    except ValueError:
        return None
    return value


def matching_raw(observation):
    raw = observation.raw_file
    return raw if raw is not None and raw.source_id == observation.source_id else None


def source_trace_parameters(query):
    names = {"observationDate", "frequency", "dataType", "sourceId"}
    if set(query) - names - {"limit", "offset"} or any(len(values) != 1 for _, values in query.lists()):
        raise ValueError("Parameter Source Trace tidak didukung atau berulang.")
    limit_text, offset_text = query.get("limit", "100"), query.get("offset", "0")
    if not re.fullmatch(r"[1-9][0-9]{0,2}", limit_text) or not re.fullmatch(r"0|[1-9][0-9]{0,5}", offset_text):
        raise ValueError("Batas atau offset histori tidak valid.")
    limit, offset = int(limit_text), int(offset_text)
    if limit > 100:
        raise ValueError("Batas histori maksimum 100 observasi per halaman.")
    selector = None
    if names & set(query):
        if not names <= set(query):
            raise ValueError("Selector harus memuat tanggal, frekuensi, jenis data dan ID sumber.")
        day = query["observationDate"]
        try:
            valid_day = date.fromisoformat(day).isoformat() == day
        except ValueError:
            valid_day = False
        if (not valid_day or query["frequency"] not in Observation.Frequency.values
                or query["dataType"] not in Observation.DataType.values
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", query["sourceId"])):
            raise ValueError("Konteks observasi tidak valid.")
        selector = {"observation_date": day, "frequency": query["frequency"],
                    "data_type": query["dataType"], "source__source_id": query["sourceId"]}
    return selector, limit, offset
