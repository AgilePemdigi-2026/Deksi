"""Discover only the latest labelled PDF within the named Kemenkeu collection."""
import json
import re
from datetime import date

from bs4 import BeautifulSoup

from . import kemenkeu
from .online_http import AcquisitionError

ARCHIVE_URL = 'https://anggaran.kemenkeu.go.id/api/posts'
MEDIA_BASE = 'https://anggaran.kemenkeu.go.id'
LABEL = re.compile(r'^Paparan Konpers APBN KiTa Bulan ([A-Za-z]+) (20\d{2})$', re.I)
MEDIA = re.compile(r'^/api/Medias/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$')


def select_document(content, *, today=None):
    today = today or date.today()
    try:
        data = json.loads(content)
        rows = data['Data']
        if data['TotalData'] != 1 or not isinstance(rows, list) or len(rows) != 1:
            raise ValueError('collection not unique')
        row = rows[0]
        if row['Title'] != 'Konpers APBN KiTa' or str(row['State']) != '1':
            raise ValueError('collection identity')
        html = row['Content']
        if not isinstance(html, str):
            raise ValueError('collection content')
        choices = {}
        for link in BeautifulSoup(html, 'html.parser').find_all('a', href=True):
            label = ' '.join(link.get_text(' ', strip=True).split())
            match = LABEL.fullmatch(label)
            if not match:
                if label.casefold().startswith('paparan konpers apbn kita bulan'):
                    raise ValueError('unknown edition label')
                continue
            month = kemenkeu.INDONESIAN_MONTHS.get(match.group(1).lower())
            year = int(match.group(2))
            href = str(link['href']).strip()
            if not month or not MEDIA.fullmatch(href) or (year, month) > (today.year, today.month):
                raise ValueError('invalid document identity')
            key = (year, month)
            if key in choices and choices[key] != href:
                raise ValueError('ambiguous edition')
            choices[key] = href
        if not choices:
            raise ValueError('no labelled editions')
        year, month = max(choices)
        return MEDIA_BASE + choices[(year, month)], year, month
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise AcquisitionError('Arsip Kemenkeu tidak dapat diidentifikasi dengan aman.') from exc


def fetch_document(get, *, today=None):
    archive = get(ARCHIVE_URL, params={'search': 'Konpers APBN KiTa', 'offset': 0, 'limit': 20})
    url, year, month = select_document(archive, today=today)
    pdf = get(url)
    if not pdf.startswith(kemenkeu.PDF_MAGIC) or len(pdf) < 1024:
        raise AcquisitionError('Dokumen Kemenkeu bukan PDF yang valid.')
    try:
        parsed = kemenkeu.parse_kita_text(kemenkeu.pdf_to_text(pdf), source_url=url)
    except (kemenkeu.KitaError, OSError, ValueError) as exc:
        raise AcquisitionError('PDF Kemenkeu tidak dapat diproses.') from exc
    period = parsed.cumulative_until
    allowed_periods = {(year, month), (year - (month == 1), (month - 2) % 12 + 1)}
    if not period or (period.year, period.month) not in allowed_periods:
        raise AcquisitionError('Periode PDF tidak sesuai edisi arsip.')
    required = {'pendapatan_negara', 'belanja_negara', 'defisit_apbn', 'defisit_pdb'}
    if not required.issubset(parsed.metrics):
        raise AcquisitionError('Ringkasan fiskal dalam PDF tidak lengkap.')
    points = []
    for key in sorted(required):
        metric = parsed.metrics[key]
        expected_unit = '% PDB' if key == 'defisit_pdb' else 'Rp Triliun'
        if metric.unit != expected_unit or not metric.value.is_finite():
            raise AcquisitionError('Satuan atau nilai fiskal tidak valid.')
        points.append({'code': 'fiskal' if key == 'defisit_pdb' else key,
            'observation_date': period, 'data_type': 'cumulative_ytd',
            'period_label': parsed.period_label, 'frequency': 'monthly',
            'value': metric.value, 'unit': metric.unit, 'publication_date': None})
    return {'content': pdf, 'source_url': url, 'document_name': kemenkeu.suggested_document_name(parsed),
            'period_label': parsed.period_label, 'points': points}
