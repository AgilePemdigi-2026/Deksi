"""Official BI table reader. No XML field mapping or release dates are guessed."""
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from . import parsing
from .online_http import AcquisitionError

SERIES = {
    'birate': 'https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx',
    'jisdor': 'https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/Default.aspx',
    'cad_devisa': 'https://www.bi.go.id/id/statistik/indikator/indikator-moneter.aspx',
}


class BIError(AcquisitionError):
    pass


def _day(text):
    parsed = parsing.parse_indonesian_date(text) or parsing.parse_mdy_date(text)
    if parsed:
        return parsed
    # The monetary table also uses English three-letter month labels.
    match = re.fullmatch(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', text, re.I)
    if match:
        day, month, year = match.groups()
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        month = months.index(month.lower()) + 1
        try:
            return date(int(year), month, int(day))
        except ValueError:
            return None
    return None


def _grid(table):
    rows, spans = [], {}
    for tr in table.find_all('tr'):
        if tr.find_parent('table') != table:
            continue
        row, column, next_spans = [], 0, {}
        def fill_spans(spans=spans, row=row, next_spans=next_spans):
            nonlocal column
            while column in spans:
                value, remaining = spans[column]
                row.append(value)
                if remaining > 1:
                    next_spans[column] = (value, remaining - 1)
                column += 1
        for cell in tr.find_all(['td', 'th'], recursive=False):
            fill_spans()
            text = parsing.normalize_text(cell.get_text(' ', strip=True))
            try:
                width, height = int(cell.get('colspan', 1)), int(cell.get('rowspan', 1))
            except (ValueError, TypeError) as exc:
                raise BIError('Struktur tabel BI tidak dikenali.') from exc
            if not 1 <= width <= 32 or not 1 <= height <= 100 or column + width > 64:
                raise BIError('Struktur tabel BI melewati batas.')
            for _ in range(width):
                if column in spans:
                    raise BIError('Kolom tabel BI bertumpang tindih.')
                row.append(text)
                if height > 1:
                    next_spans[column] = (text, height - 1)
                column += 1
        fill_spans()
        if row:
            rows.append(row)
        spans = next_spans
        if len(rows) > 10000:
            raise BIError('Jumlah baris BI melewati batas.')
    return rows


def _id_value(text, *, rate=False):
    text = parsing.normalize_text(text)
    if rate:
        if not re.fullmatch(r'\d+(?:[,.]\d+)?\s*%', text):
            raise BIError('Nilai BI-Rate tidak valid.')
        normalized = text.replace('%', '').strip().replace(',', '.')
    else:
        text = re.sub(r'^Rp\s*', '', text)
        if not re.fullmatch(r'\d+(?:\.\d{3})*(?:,\d+)?', text):
            raise BIError('Nilai statistik BI tidak valid.')
        normalized = text.replace('.', '').replace(',', '.')
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise BIError('Nilai statistik BI tidak valid.') from exc
    if not value.is_finite() or value < 0 or (rate and value > 50):
        raise BIError('Nilai statistik BI di luar batas.')
    return value


def parse_document(code, content, *, today=None):
    if code not in SERIES:
        raise BIError('Seri BI tidak dikenal.')
    today = today or date.today()
    soup = BeautifulSoup(content, 'html.parser')
    matches = []
    for table in soup.find_all('table'):
        rows = _grid(table)
        if code == 'cad_devisa':
            if any('cadangan devisa' in ' '.join(row).lower() for row in rows):
                matches.append(rows)
        else:
            for i, row in enumerate(rows):
                lowered = [x.casefold() for x in row]
                key = 'bi-rate' if code == 'birate' else 'kurs'
                keys = [j for j, value in enumerate(lowered)
                    if value == key or (code == 'birate' and value == 'bi-7day-rr')]
                if 'tanggal' in lowered and len(keys) == 1:
                    matches.append((rows, i, lowered.index('tanggal'), keys[0]))
    if len(matches) != 1:
        raise BIError('Tabel BI tidak tersedia, berubah, atau ambigu.')
    points = []
    if code == 'cad_devisa':
        rows = matches[0]
        target = [row for row in rows if 'cadangan devisa' in ' '.join(row).lower()]
        headers = [[(i, _day(value)) for i, value in enumerate(row) if _day(value)] for row in rows]
        headers = [header for header in headers if header]
        if len(target) != 1 or len(headers) != 1:
            raise BIError('Periode atau baris cadangan devisa tidak jelas.')
        unit_text = ' '.join(target[0]).lower()
        if re.search(r'juta\s+usd', unit_text):
            divisor = Decimal('1000')
        elif re.search(r'(miliar\s+usd|usd\s+miliar)', unit_text):
            divisor = Decimal('1')
        else:
            raise BIError('Satuan cadangan devisa belum terverifikasi.')
        for column, day in headers[0]:
            if day is None:
                raise BIError('Tanggal cadangan devisa tidak jelas.')
            if column >= len(target[0]):
                raise BIError('Kolom cadangan devisa tidak lengkap.')
            points.append({'observation_date': day, 'value': _id_value(target[0][column]) / divisor,
                'unit': 'USD Miliar', 'frequency': 'monthly', 'data_type': 'level',
                'period_label': day.isoformat()})
    else:
        rows, start, date_col, value_col = matches[0]
        for row in rows[start + 1:]:
            if not any(row):
                continue
            if len(row) <= max(date_col, value_col):
                raise BIError('Baris statistik BI tidak lengkap.')
            day = _day(row[date_col])
            if day is None:
                raise BIError('Tanggal statistik BI tidak dikenali.')
            value = _id_value(row[value_col], rate=code == 'birate')
            if code == 'jisdor' and (value <= 0 or value > 1000000):
                raise BIError('Kurs JISDOR di luar batas.')
            points.append({'observation_date': day, 'value': value,
                'unit': '%' if code == 'birate' else 'Rp/USD',
                'frequency': 'adhoc' if code == 'birate' else 'daily',
                'data_type': 'event' if code == 'birate' else 'level',
                'period_label': row[date_col] if code == 'birate' else day.isoformat()})
    if not points or any(point['observation_date'] > today for point in points):
        raise BIError('Data BI kosong atau memuat periode masa depan.')
    dates = [point['observation_date'] for point in points]
    if len(set(dates)) != len(dates):
        raise BIError('Periode BI duplikat atau ambigu.')
    if code == 'cad_devisa' and len({(d.year, d.month) for d in dates}) != len(dates):
        raise BIError('Periode bulanan cadangan devisa ambigu.')
    for point in points:
        point['code'] = code
    # Only visible table cells are retained: no scripts, tokens or mutable DOM attributes.
    evidence = json.dumps({'kind': 'bi_selected_table_excerpt', 'source_url': SERIES[code],
        'code': code, 'table_cells': rows}, sort_keys=True, ensure_ascii=True).encode()
    return {'document_name': f'bi-{code}-table-excerpt.json', 'source_url': SERIES[code],
        'period_label': f'{min(dates).isoformat()} - {max(dates).isoformat()}',
        'content': evidence, 'points': points}


def fetch_document(code, get_bytes, *, today=None):
    if code not in SERIES:
        raise BIError('Seri BI tidak dikenal.')
    return parse_document(code, get_bytes(SERIES[code]), today=today)
