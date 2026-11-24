"""BIS SDMX policy-rate reader; observation dates are not release dates."""
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from .online_http import AcquisitionError

ENDPOINT = 'https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.ID'


def parse_document(content, *, today=None):
    today = today or date.today()
    if not isinstance(content, bytes) or len(content) > 2 * 1024 * 1024:
        raise AcquisitionError('Respons BIS tidak valid.')
    # Reject NUL/UTF-16 and declarations before stdlib XML parsing; no entities are accepted.
    if b'\x00' in content or b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        raise AcquisitionError('Deklarasi XML BIS tidak diizinkan.')
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise AcquisitionError('XML BIS tidak valid.') from exc
    series = [node for node in root.iter() if node.tag.rsplit('}', 1)[-1] == 'Series']
    if (len(series) != 1 or series[0].get('FREQ') != 'D' or series[0].get('REF_AREA') != 'ID'
            or series[0].get('SOURCE_REF') != 'Bank Indonesia'):
        raise AcquisitionError('Identitas seri BIS tidak sesuai.')
    values = []
    seen = set()
    for node in series[0]:
        if node.tag.rsplit('}', 1)[-1] != 'Obs':
            continue
        try:
            day = date.fromisoformat(node.attrib['TIME_PERIOD'])
        except (ValueError, KeyError) as exc:
            raise AcquisitionError('Tanggal observasi BIS tidak valid.') from exc
        if day in seen or day > today:
            raise AcquisitionError('Tanggal observasi BIS duplikat atau di masa depan.')
        seen.add(day)
        status, raw = node.get('OBS_STATUS'), node.get('OBS_VALUE')
        if status == 'M' and raw in (None, 'NaN'):
            continue
        if status != 'A' or not raw:
            raise AcquisitionError('Status observasi BIS belum didukung.')
        try:
            value = Decimal(raw)
        except InvalidOperation as exc:
            raise AcquisitionError('Nilai observasi BIS tidak valid.') from exc
        if not value.is_finite() or not 0 < value <= 50:
            raise AcquisitionError('Nilai observasi BIS di luar batas.')
        values.append((day, value))
    if not values:
        raise AcquisitionError('Observasi BIS tidak tersedia.')
    day, value = max(values)
    return {'document_name': 'bis-indonesia-policy-rate.xml', 'source_url': ENDPOINT,
        'period_label': day.isoformat(), 'content': content,
        'points': [{'code': 'birate', 'observation_date': day, 'period_label': day.isoformat(),
                    'frequency': 'daily', 'data_type': 'level', 'value': value, 'unit': '%'}]}


def fetch_document(get_bytes):
    return parse_document(get_bytes(ENDPOINT, params={'lastNObservations': 30}))
