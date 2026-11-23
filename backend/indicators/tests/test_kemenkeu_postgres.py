"""PostgreSQL fencing races for Kemenkeu using offline provider fixtures."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from indicators.kemenkeu import KitaMetric, KitaResult
from indicators.models import Source
from indicators.tests.test_kemenkeu_online import ARCHIVE, MEDIA, archive_body
from indicators.tests.test_online_postgres import OnlinePostgresTests


class KemenkeuPostgresTests(OnlinePostgresTests):
    def setUp(self):
        super().setUp()
        self.source, _ = Source.objects.get_or_create(source_id='KEMENKEU', defaults={
            'source_name': 'APBN KiTa UJI SINTETIS', 'institution': 'INSTANSI UJI',
            'primary_url': 'https://anggaran.kemenkeu.go.id/',
        })
        self.source.acquisition_method = 'web_kemenkeu'
        self.source.endpoint_url = ARCHIVE
        self.source.data_format = 'pdf'
        self.source.save()
        self.job.source = self.source
        self.job.save(update_fields=['source'])

    def race_after_fetch(self, update):
        def response(url):
            if url == ARCHIVE:
                return archive_body()
            if url == MEDIA:
                return b'%PDF-' + b'x' * 1200
            raise AssertionError('unexpected URL')
        metrics = {key: KitaMetric(key, Decimal(value), 'Rp Triliun', 'synthetic') for key, value in [
            ('pendapatan_negara', '100'), ('belanja_negara', '120'), ('defisit_apbn', '20')]}
        metrics['defisit_pdb'] = KitaMetric('defisit_pdb', Decimal('1.24'), '% PDB', 'synthetic')
        parsed = KitaResult(MEDIA, date(2026, 9, 30), 'Kumulatif s.d. 30 September 2026', None, metrics)
        with patch('indicators.tests.test_online_postgres.bi_response', side_effect=response), \
             patch('indicators.kemenkeu.pdf_to_text', return_value='synthetic'), \
             patch('indicators.kemenkeu.parse_kita_text', return_value=parsed):
            return super().race_after_fetch(update)
