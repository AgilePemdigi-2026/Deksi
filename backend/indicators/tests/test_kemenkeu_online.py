"""Offline checks for the Kemenkeu collection and PDF boundary."""
import json
from datetime import date
from unittest import TestCase
from unittest.mock import patch

from indicators.online_http import AcquisitionError

ARCHIVE = 'https://anggaran.kemenkeu.go.id/api/posts'
MEDIA = 'https://anggaran.kemenkeu.go.id/api/Medias/245556ad-28fb-4835-9ab9-1e9b60398c05'


def archive_body(extra=''):
    html = ('<a href="/api/Medias/245556ad-28fb-4835-9ab9-1e9b60398c05">'
            'Paparan Konpers APBN KiTa Bulan Oktober 2026</a>' + extra)
    return json.dumps({'TotalData': 1, 'Data': [{'Title': 'Konpers APBN KiTa', 'State': '1',
        'Content': html, 'PublishedDate': '2026-10-19T02:40:48.597'}]}).encode()


class KemenkeuOnlineTests(TestCase):
    def test_explicit_kemenkeu_online_configuration_is_supported(self):
        from indicators.models import Source
        from indicators.resync_methods import resync_method
        source = Source(source_id='KEMENKEU', acquisition_method='web_kemenkeu',
                        endpoint_url=ARCHIVE, data_format='pdf')
        self.assertEqual(resync_method(source), 'web_kemenkeu')

    def test_latest_in_collection_is_selected_not_collection_publication_date(self):
        from indicators.kemenkeu_online import select_document
        result = select_document(archive_body(), today=date(2026, 11, 22))
        self.assertEqual(result, (MEDIA, 2026, 10))

    def test_ambiguous_latest_or_unexpected_collection_fails_closed(self):
        from indicators.kemenkeu_online import select_document
        extra = ('<a href="/api/Medias/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa">'
                 'Paparan Konpers APBN KiTa Bulan Oktober 2026</a>')
        with self.assertRaises(AcquisitionError):
            select_document(archive_body(extra), today=date(2026, 11, 22))
        body = json.loads(archive_body())
        body['TotalData'] = 2
        with self.assertRaises(AcquisitionError):
            select_document(json.dumps(body).encode(), today=date(2026, 11, 22))

    def test_unrecognised_edition_label_fails_instead_of_selecting_stale_edition(self):
        from indicators.kemenkeu_online import select_document
        extra = ('<a href="/api/Medias/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa">'
                 'Paparan Konpers APBN KiTa Bulan November 2026 (baru)</a>')
        with self.assertRaises(AcquisitionError):
            select_document(archive_body(extra), today=date(2026, 11, 22))

    def test_untrusted_media_url_rejected(self):
        from indicators.kemenkeu_online import select_document
        body = archive_body().replace(b'/api/Medias/', b'https://evil.test/api/Medias/')
        with self.assertRaises(AcquisitionError):
            select_document(body, today=date(2026, 11, 22))

    def test_document_parses_to_pending_shape_without_invented_release_date(self):
        from indicators.kemenkeu import KitaMetric, KitaResult
        from indicators.kemenkeu_online import fetch_document
        from decimal import Decimal
        pdf = b'%PDF-' + b'x' * 1200
        metrics = {key: KitaMetric(key, Decimal(value), 'Rp Triliun', 'synthetic') for key, value in [
            ('pendapatan_negara', '100'), ('belanja_negara', '120'), ('defisit_apbn', '20')]}
        metrics['defisit_pdb'] = KitaMetric('defisit_pdb', Decimal('1.24'), '% PDB', 'synthetic')
        parsed = KitaResult(MEDIA, date(2026, 9, 30), 'Kumulatif s.d. 30 September 2026', None, metrics)
        def get(url, params=None):
            if url == ARCHIVE:
                return archive_body()
            if url == MEDIA:
                return pdf
            raise AssertionError(url)
        with patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=parsed):
            result = fetch_document(get, today=date(2026, 11, 22))
        self.assertEqual(result['content'], pdf)
        self.assertEqual(result['source_url'], MEDIA)
        self.assertEqual(len(result['points']), 4)
        self.assertTrue(all(point['publication_date'] is None for point in result['points']))
