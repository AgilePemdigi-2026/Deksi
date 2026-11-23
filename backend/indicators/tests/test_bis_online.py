from datetime import date
from decimal import Decimal
from unittest import TestCase

from indicators.bis_online import parse_document
from indicators.online_http import AcquisitionError
from indicators.tests.test_bis_sync import XML


class BISParserTests(TestCase):
    def test_latest_actual_observation_and_missing_not_zero(self):
        doc = parse_document(XML, today=date(2026, 11, 22))
        self.assertEqual(doc['points'][0]['observation_date'], date(2026, 11, 16))
        self.assertEqual(doc['points'][0]['value'], Decimal('5.75'))
        self.assertNotIn('publication_date', doc['points'][0])
        self.assertEqual(doc['content'], XML)

    def test_invalid_and_ambiguous_inputs_are_rejected(self):
        cases = [
            XML.replace(b'REF_AREA="ID"', b'REF_AREA="US"'),
            XML.replace(b'FREQ="D"', b'FREQ="M"'),
            XML.replace(b'SOURCE_REF="Bank Indonesia"', b'SOURCE_REF="Other"'),
            XML.replace(b'2026-11-16', b'2026-11-13'),
            XML.replace(b'2026-11-16', b'2027-11-16'),
            XML.replace(b'OBS_VALUE="5.75"', b'OBS_VALUE="NaN"'),
            XML.replace(b'OBS_STATUS="A"', b'OBS_STATUS="P"'),
            b'<!DOCTYPE x [<!ENTITY x "oops">]><x>&x;</x>',
            b'\xff\xfe<\x00x\x00/\x00>\x00',
            b'<bad',
        ]
        for payload in cases:
            with self.subTest(payload=payload[:100]), self.assertRaises(AcquisitionError):
                self.assertNotEqual(payload, XML)
                parse_document(payload, today=date(2026, 11, 22))
