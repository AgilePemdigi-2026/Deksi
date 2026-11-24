"""Stage online observations under the existing job, source and review contracts."""
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext

from django.core.exceptions import ValidationError
from django.db import transaction

from . import bi_online
from .ingest import get_or_create_indicator
from .lifecycle import stage_observation
from .models import Indicator, RawFile, Source, source_config_snapshot
from .online_http import AcquisitionError, OfficialHTTP
from .resync_methods import resync_method
from .storage import save_raw

INDICATORS = {
    'birate': ('BI-Rate', 'Kebijakan Moneter', '%', 'avg', 5),
    'jisdor': ('Kurs Referensi (JISDOR)', 'Kebijakan Moneter', 'Rp/USD', 'avg', 6),
    'cad_devisa': ('Cadangan Devisa', 'Kebijakan Moneter', 'USD Miliar', 'end', 7),
    'investasi': ('Realisasi Investasi', 'Rencana Modal', 'Rp Triliun', 'sum', 4),
    'pendapatan_negara': ('Pendapatan Negara (Realisasi Kumulatif)', 'Fiskal & Keuangan Negara', 'Rp Triliun', 'end', 3),
    'belanja_negara': ('Belanja Negara (Realisasi Kumulatif)', 'Fiskal & Keuangan Negara', 'Rp Triliun', 'end', 4),
    'defisit_apbn': ('Defisit APBN (Nominal)', 'Fiskal & Keuangan Negara', 'Rp Triliun', 'end', 5),
    'fiskal': ('Defisit APBN', 'Fiskal & Keuangan Negara', '% PDB', 'end', 5),
}


class OnlineConfigChangedError(ValueError):
    pass


def _check_source(source, expected):
    if (source.status != Source.SourceStatus.ACTIVE or source_config_snapshot(source) != expected
            or not resync_method(source)):
        raise OnlineConfigChangedError('Konfigurasi atau status sumber berubah.')


def _stage_document(source, expected, document, guard):
    codes = sorted({point['code'] for point in document['points']})
    allowed = {
        'BKPM': {'investasi'},
        'BIS': {'birate'},
        'BI': {'birate', 'jisdor', 'cad_devisa'},
        'KEMENKEU': {'pendapatan_negara', 'belanja_negara', 'defisit_apbn', 'fiskal'},
    }.get(source.source_id, set())
    if not codes or not set(codes) <= allowed:
        raise AcquisitionError('Dokumen tidak sesuai identitas sumber.')
    with transaction.atomic():
        # Same master order as candidate staging/review. Claiming a job locks source before job.
        # Therefore acquire indicator -> source -> job, never job -> source here.
        indicators = {}
        for code in codes:
            indicators[code] = get_or_create_indicator(code, *INDICATORS[code])
            Indicator.objects.select_for_update().get(pk=indicators[code].pk)
        locked = Source.objects.select_for_update().get(pk=source.pk)
        _check_source(locked, expected)
        with guard():
            raw, _ = save_raw(locked, document['content'], document['document_name'],
                source_url=document['source_url'], period_label=document['period_label'])
            for point in document['points']:
                values = {key: value for key, value in point.items() if key != 'code'}
                stage_observation(indicator_id=indicators[point['code']].pk,
                    source_id=locked.pk, raw_file_id=raw.pk, **values)
            raw.parse_status = RawFile.ParseStatus.PARSED
            raw.save(update_fields=['parse_status'])
    return len(document['points'])


def sync_source(source, *, write_guard: Callable[[], AbstractContextManager] = nullcontext):
    expected = source_config_snapshot(source)
    _check_source(source, expected)
    count, errors = 0, []
    if source.source_id == 'BI':
        readers = [(code, lambda get, code=code: bi_online.fetch_document(code, get)) for code in bi_online.SERIES]
    elif source.source_id == 'BKPM':
        from .bkpm_online import fetch_latest
        readers = [('investasi', fetch_latest)]
    elif source.source_id == 'BIS':
        from .bis_online import fetch_document
        readers = [('birate', fetch_document)]
    elif source.source_id == 'KEMENKEU':
        from .kemenkeu_online import fetch_document
        readers = [('apbn_kita', fetch_document)]
    else:
        raise AcquisitionError('Sumber online belum didukung.')
    max_bytes = {'KEMENKEU': 16 * 1024 * 1024, 'BKPM': 8 * 1024 * 1024}.get(
        source.source_id, 2 * 1024 * 1024)
    with OfficialHTTP(max_bytes=max_bytes) as http:
        for code, read_document in readers:
            # Check claim before provider access; no network in the transaction.
            with write_guard():
                _check_source(Source.objects.get(pk=source.pk), expected)
            try:
                document = read_document(http.get_bytes)
                count += _stage_document(source, expected, document, write_guard)
            except OnlineConfigChangedError:
                raise
            except (AcquisitionError, ValidationError, OSError, RuntimeError, ValueError):
                errors.append(code)
    return {'observations': count, 'errors': errors}
