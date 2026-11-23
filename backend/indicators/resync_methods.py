"""One source/method contract shared by API, worker and advertised capability."""
ONLINE_SOURCES = {
    'web_kemenkeu': ('KEMENKEU', 'https://anggaran.kemenkeu.go.id/api/posts', 'pdf'),
    'api_bis': ('BIS', 'https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.ID', 'xml'),
    'web_bi': ('BI', 'https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx', 'html'),
    'web_bkpm': ('BKPM', 'https://data.bkpm.go.id/dataset', 'json'),
}
RESYNCABLE_METHODS = frozenset({'api_bps', *ONLINE_SOURCES})


def resync_method(source):
    method = (source.acquisition_method or '').strip()
    if not method and source.source_id == 'BPS':
        method = 'api_bps'
    if method == 'api_bps':
        return method if source.source_id == 'BPS' else ''
    if method in ONLINE_SOURCES:
        expected_id, endpoint, data_format = ONLINE_SOURCES[method]
        if (source.source_id, source.endpoint_url, source.data_format) == (expected_id, endpoint, data_format):
            return method
    return ''
