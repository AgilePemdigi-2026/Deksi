import base64
import json
import unittest
from datetime import date
from decimal import Decimal

from indicators import bkpm_online

BASE = "https://data.bkpm.go.id"
CATALOGUE = f"{BASE}/dataset"
COLUMNS = [
    "periode", "status_penanaman_modal", "regional", "negara", "sektor_utama",
    "nama_sektor", "deskripsi_kbli_2digit", "provinsi", "kabupaten_kota",
    "jawa_luar_jawa", "pulau", "investasi_rp_juta", "investasi_us_ribu", "tki",
]


def table_page(slug, parent="opaque-id"):
    return f'''<html><a href="/dataset-view/{slug}">Pratinjau</a>
    <input id="dataset_detail_parent_id" value="{parent}"></html>'''.encode()


def catalogue(slug):
    return f'<a href="/dataset-detail/{slug}">BKPM</a>'.encode()


def api_page(period="2026 - Triwulan 3", value="1.234,56", total=1, rows=None, cols=None):
    if rows is None:
        rows = [{"\ufeffperiode": period, "investasi_rp_juta": value}]
    # Full synthetic dimensions, just like the shape observed in the public preview.
    defaults = {key: 'UJI SINTETIS' for key in COLUMNS if key not in ('periode', 'investasi_rp_juta')}
    rows = [{**defaults, **row} for row in rows]
    return json.dumps({"draw": 1, "recordsTotal": total, "recordsFiltered": total,
                       "data": rows, "columns": cols or COLUMNS}, ensure_ascii=False).encode()


def slug(q):
    roman = ("i", "ii", "iii", "iv")[q - 1]
    return f"data-realisasi-investasi-triwulan-{roman}-tahun-2026"


class FakeTransport:
    def __init__(self, responses):
        self.responses: dict = responses
        self.calls = []

    def __call__(self, url, params=None):
        self.calls.append((url, params))
        key = (url, tuple(sorted((params or {}).items())))
        if key in self.responses:
            return self.responses[key]
        if url in self.responses:
            return self.responses[url]
        raise AssertionError(f"Unexpected request URL: {url}")


def successful_transport():
    current = slug(3)
    responses = {
        CATALOGUE: catalogue(current),
        f"{BASE}/dataset-detail/{current}": table_page(current),
        f"{BASE}/dataset-view/{current}": table_page(current),
        f"{BASE}/data": api_page(),
    }
    return FakeTransport(responses)


class BkpmOnlineTests(unittest.TestCase):
    def test_adapter_is_present_and_callable(self):
        self.assertTrue(callable(getattr(bkpm_online, "fetch_latest", None)))

    def test_fetches_latest_completed_quarter_and_converts_units(self):
        transport = successful_transport()
        document = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(document["document_name"], "data-realisasi-investasi-triwulan-iii-tahun-2026-preview.json")
        self.assertEqual(document["period_label"], "Triwulan III 2026")
        self.assertEqual(document["points"][0]["code"], "investasi")
        self.assertEqual(document["points"][0]["observation_date"], date(2026, 9, 30))
        self.assertEqual(document["points"][0]["value"], Decimal("0.00"))
        self.assertEqual(document["points"][0]["unit"], "Rp Triliun")
        self.assertEqual(document["points"][0]["data_type"], "derived_sum")

    def test_requests_are_fixed_host_and_page_evidence_is_preserved(self):
        transport = successful_transport()
        document = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertTrue(all(url.startswith(BASE + "/") for url, _ in transport.calls))
        evidence = json.loads(document["content"])
        self.assertEqual(evidence["source_url"], document["source_url"])
        self.assertEqual(evidence["period_label"], document["period_label"])
        self.assertEqual(evidence['kind'], 'bkpm_public_preview_json')
        self.assertEqual(evidence["pages"][0]["raw_base64"], base64.b64encode(api_page()).decode("ascii"))

    def test_missing_zero_and_invalid_investment_are_not_conflated(self):
        for rows, expected in [
            ([{"\ufeffperiode": "2026 - Triwulan 3", "investasi_rp_juta": "0"}], Decimal("0.00")),
            ([{"\ufeffperiode": "2026 - Triwulan 3", "investasi_rp_juta": ""}], None),
        ]:
            with self.subTest(rows=rows):
                transport = successful_transport()
                transport.responses[f"{BASE}/data"] = api_page(rows=rows)
                try:
                    result = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
                except bkpm_online.BKPMError:
                    if expected is not None:
                        self.fail("valid numeric zero must remain a valid zero")
                else:
                    if expected is None:
                        self.fail("missing investment must not become zero")
                    self.assertEqual(result["points"][0]["value"], expected)
        transport = successful_transport()
        transport.responses[f"{BASE}/data"] = api_page(rows=[{
            "\ufeffperiode": "2026 - Triwulan 3", "investasi_rp_juta": "NaN"}])
        with self.assertRaises(bkpm_online.BKPMError):
            bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))

    def test_hostile_detail_link_is_rejected_before_transport(self):
        transport = FakeTransport({CATALOGUE: b'<a href="https://evil.example/dataset-realisasi-investasi-triwulan-iii-tahun-2026">x</a>'})
        with self.assertRaises(bkpm_online.BKPMError):
            bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(len(transport.calls), 1)

    def test_changed_columns_conflicting_keys_and_period_mismatch_fail_closed(self):
        cases = [
            api_page(cols=COLUMNS[:-1]),
            api_page(rows=[{"\ufeffperiode": "2026 - Triwulan 3", "periode": "2026 - Triwulan 2",
                "investasi_rp_juta": "1"}]),
            api_page(period="2026 - Triwulan 2"),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                transport = successful_transport()
                transport.responses[f"{BASE}/data"] = payload
                with self.assertRaises(bkpm_online.BKPMError):
                    bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))

    def test_fetches_all_pages_and_rejects_replayed_page_content(self):
        row = {"\ufeffperiode": "2026 - Triwulan 3", "investasi_rp_juta": "0"}
        row.update({key: 'UJI SINTETIS' for key in COLUMNS if key not in ('periode', 'investasi_rp_juta')})
        full_rows = [dict(row, provinsi=str(i)) for i in range(1000)]
        transport = successful_transport()
        transport.responses[f"{BASE}/data"] = api_page(total=1001, rows=full_rows)
        second = {"draw": 2, "recordsTotal": 1001, "recordsFiltered": 1001,
                  "columns": COLUMNS, "data": [dict(row, provinsi="last")]}
        transport.responses[(f"{BASE}/data", tuple(sorted({
            "dataset_detail_parent_id": "opaque-id", "start": 1000,
            "length": 1000, "draw": 2,
        }.items())))] = json.dumps(second).encode()
        result = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(result["points"][0]["value"], Decimal("0.00"))
        data_calls = [(url, params) for url, params in transport.calls if url == f"{BASE}/data"]
        self.assertEqual([call[1]["start"] for call in data_calls], [0, 1000])

        replay = successful_transport()
        replay.responses[f"{BASE}/data"] = api_page(total=1500, rows=full_rows)
        replay.responses[(f"{BASE}/data", tuple(sorted({
            "dataset_detail_parent_id": "opaque-id", "start": 1000,
            "length": 1000, "draw": 2,
        }.items())))] = json.dumps({
            "draw": 2, "recordsTotal": 1500, "recordsFiltered": 1500,
            "columns": COLUMNS, "data": full_rows,
        }).encode()
        with self.assertRaises(bkpm_online.BKPMError):
            bkpm_online.fetch_latest(replay, today=date(2026, 11, 21))

    def test_catalogue_pagination_uses_only_bounded_same_host_links(self):
        transport = successful_transport()
        old_slug = "data-realisasi-investasi-triwulan-iii-tahun-2026"
        transport.responses[CATALOGUE] = b'<a href="/dataset?page=2">2</a>'
        transport.responses[f"{CATALOGUE}?page=2"] = catalogue(old_slug)
        result = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(result["period_label"], "Triwulan III 2026")
        self.assertIn((f"{CATALOGUE}?page=2", None), transport.calls)

    def test_negative_and_boolean_investment_values_are_rejected(self):
        for value in ("-1", True):
            with self.subTest(value=value):
                transport = successful_transport()
                transport.responses[f"{BASE}/data"] = api_page(rows=[{
                    "\ufeffperiode": "2026 - Triwulan 3", "investasi_rp_juta": value,
                }])
                with self.assertRaises(bkpm_online.BKPMError):
                    bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))

    def test_ambiguous_latest_quarter_fails(self):
        primary = slug(3)
        transport = successful_transport()
        transport.responses[CATALOGUE] = (
            f'<a href="/dataset/{primary}">a</a><a href="/dataset-view/{primary}">b</a>'
        ).encode()
        with self.assertRaises(bkpm_online.BKPMError):
            bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))

    def test_adapter_does_not_make_own_network_requests(self):
        # The only transport is injected; a failed lookup must not fall back to networking.
        transport = FakeTransport({CATALOGUE: catalogue(slug(3)),
            f"{BASE}/dataset-detail/{slug(3)}": table_page(slug(3)),
            f"{BASE}/dataset-view/{slug(3)}": table_page(slug(3))})
        with self.assertRaises(bkpm_online.BKPMError):
            bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual([url for url, _ in transport.calls][-1], f"{BASE}/data")

    def test_page_one_alias_is_not_fetched_again(self):
        transport = successful_transport()
        transport.responses[CATALOGUE] += b'<a href="/dataset?page=1">1</a>'
        bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertNotIn((f'{CATALOGUE}?page=1', None), transport.calls)

    def test_catalogue_status_filter_is_not_mistaken_for_pagination(self):
        transport = successful_transport()
        transport.responses[CATALOGUE] += b'<a href="/dataset?status=publik">Terbuka</a>'
        document = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(document['period_label'], 'Triwulan III 2026')
        self.assertNotIn((f'{CATALOGUE}?status=publik', None), transport.calls)

    def test_rounding_matches_the_existing_local_importer(self):
        transport = successful_transport()
        transport.responses[f'{BASE}/data'] = api_page(value='1005000')
        document = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(document['points'][0]['value'], (Decimal('1005000') / 1000000).quantize(Decimal('.01')))

    def test_identifier_is_read_from_preview_not_assumed_on_detail_page(self):
        transport = successful_transport()
        current = slug(3)
        transport.responses[f'{BASE}/dataset-detail/{current}'] = (
            f'<a href="/dataset-view/{current}">Pratinjau</a>').encode()
        transport.responses[f'{BASE}/dataset-view/{current}'] = table_page(current)
        document = bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))
        self.assertEqual(document['period_label'], 'Triwulan III 2026')
        self.assertIn((f'{BASE}/dataset-view/{current}', None), transport.calls)

    def test_missing_dimension_or_conflicting_normalized_column_is_rejected(self):
        transport = successful_transport()
        page = json.loads(api_page())
        del page['data'][0]['provinsi']
        transport.responses[f'{BASE}/data'] = json.dumps(page).encode()
        with self.assertRaises(bkpm_online.BKPMError):
            bkpm_online.fetch_latest(transport, today=date(2026, 11, 21))


if __name__ == "__main__":
    unittest.main()
