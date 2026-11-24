"""Strict synthetic table contracts; real BI connectivity remains a separate gate."""
import unittest
from datetime import date
from decimal import Decimal


class BITableTests(unittest.TestCase):
    def test_rate_table_is_parsed_with_evidence_and_unknown_release_date(self):
        try:
            from indicators.bi_online import parse_document
        except ImportError:
            self.fail('Online BI table parser has not been implemented')
        html = (b'<table><tr><th>No</th><th>Tanggal</th><th>BI-Rate</th></tr>'
            b'<tr><td>1</td><td>21 Oktober 2026</td><td>5,75 %</td></tr></table>')
        doc = parse_document('birate', html, today=date(2026, 11, 21))
        point = doc['points'][0]
        self.assertEqual(point['value'], Decimal('5.75'))
        self.assertEqual(point['observation_date'], date(2026, 10, 21))
        self.assertEqual(point['data_type'], 'event')
        self.assertNotIn('publication_date', point)
        self.assertIn(b'bi_selected_table_excerpt', doc['content'])

    def test_incomplete_data_row_rejects_the_whole_table(self):
        from indicators.bi_online import BIError, parse_document
        html = (b'<table><tr><th>No</th><th>Tanggal</th><th>BI-Rate</th></tr>'
            b'<tr><td>1</td><td>21 Oktober 2026</td><td>5,75 %</td></tr>'
            b'<tr><td>2</td><td>23 September 2026</td></tr></table>')
        with self.assertRaises(BIError):
            parse_document('birate', html)

    def test_jisdor_indonesian_grouping_and_date_are_preserved(self):
        from indicators.bi_online import parse_document
        html = (b'<table><tr><th>Tanggal</th><th>Kurs</th></tr>'
            b'<tr><td>19 November 2026</td><td>Rp 14.235,00</td></tr></table>')
        point = parse_document('jisdor', html, today=date(2026, 11, 21))['points'][0]
        self.assertEqual(point['value'], Decimal('14235.00'))
        self.assertEqual(point['frequency'], 'daily')

    def test_reserve_unit_conversion_requires_explicit_source_unit(self):
        from indicators.bi_online import BIError, parse_document
        html = (b'<table><tr><th colspan="2">Items</th><th>30 Sep 2026</th><th>30 Oct 2026</th></tr>'
            b'<tr><td>4</td><td>Cadangan Devisa dalam juta USD</td><td>146.320</td><td>146.765</td></tr></table>')
        points = parse_document('cad_devisa', html)['points']
        self.assertEqual([point['value'] for point in points], [Decimal('146.320'), Decimal('146.765')])
        with self.assertRaises(BIError):
            parse_document('cad_devisa', html.replace(b'juta USD', b'unknown unit'))

    def test_empty_duplicate_future_negative_and_changed_tables_fail_closed(self):
        from indicators.bi_online import BIError, parse_document
        header = '<tr><th>No</th><th>Tanggal</th><th>BI-Rate</th></tr>'
        row = '<tr><td>1</td><td>21 Oktober 2026</td><td>5,75 %</td></tr>'
        for body in [header, header + row + row, header + row.replace('2026', '2099'),
                     header + row.replace('5,75', '-5,75'), '<tr><td>captcha</td></tr>']:
            with self.subTest(body=body), self.assertRaises(BIError):
                parse_document('birate', ('<table>' + body + '</table>').encode(), today=date(2026, 11, 21))

    def test_scripts_and_attributes_are_not_saved_as_raw_evidence(self):
        from indicators.bi_online import parse_document
        html = (b'<table secret="sensitive-marker"><tr><th>No</th><th>Tanggal</th><th>BI-Rate</th></tr>'
            b'<tr><td>1</td><td>21 Oktober 2026</td><td>5,75 %'
            b'<script>sensitive-marker</script></td></tr></table>')
        self.assertNotIn(b'sensitive-marker', parse_document('birate', html)['content'])
