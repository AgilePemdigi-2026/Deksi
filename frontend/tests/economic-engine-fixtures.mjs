// Synthetic QA only. These numbers and metadata are not official BPS observations.
const schemaVersion = 'deksi.economic-engine.v1', methodVersion = 'bps-gdp-shares.v3'
function input(code, value, fingerprint) {
  const checksum = fingerprint.repeat(64)
  const trace = { indicatorCode: code, indicatorName: 'SYNTHETIC QA ONLY', value,
    unit: 'Rp miliar', period: 'Q1 2025', observationDate: '2025-03-31', frequency: 'quarterly', dataType: 'level',
    publicationDate: null, validationStatus: 'published', reviewedAt: '2025-04-01T00:00:00+00:00',
    source: { sourceId: 'BPS', sourceName: 'SYNTHETIC ONLY', institution: 'SYNTHETIC ONLY', primaryUrl: 'https://example.test' },
    rawFile: { documentName: 'synthetic.json', sourceUrl: null, checksumSha256: checksum, retrievedAt: '2025-04-01T00:00:00+00:00',
      periodLabel: null, fileSizeBytes: 1, downloadUrl: `/api/indicators/${code}/raw-file/1/` } }
  return { value, unit: trace.unit, sourceId: 'BPS', period: trace.period, observationDate: trace.observationDate,
    frequency: trace.frequency, dataType: trace.dataType, publicationDate: null, evidenceStatus: 'integrity_ok',
    bindingStatus: 'matched', evidenceChecksumSha256: checksum, trace }
}
export function engineFixture() {
  const metric = (id, numerator, name, value, share, fingerprint) => ({
    schemaVersion, methodVersion, id, name, available: true, value: share, unit: '%', period: 'Q1 2025',
    observationDate: '2025-03-31', classification: 'DEKSI-derived', formula: `${numerator} / pdb_nominal * 100`,
    formulaVersion: '2', roundingMode: 'ROUND_HALF_EVEN', decimalPlaces: 2, officialVerification: 'unassessed',
    snapshotPersistence: 'response_only', priceBasis: 'current_prices', reason: null, reasonCode: null,
    revisionStatus: 'unknown', revisionNote: 'Status revisi belum diketahui; angka dapat direvisi.',
    note: 'SYNTHETIC QA ONLY, not independent verification', inputDigest: fingerprint.repeat(64), resultDigest: fingerprint.repeat(64),
    inputs: { [numerator]: input(numerator, value, fingerprint), pdb_nominal: input('pdb_nominal', '1000', 'c') } })
  return { schemaVersion, methodVersion, metrics: {
    pmtb_share: metric('pmtb_share', 'pmtb_nominal', 'Porsi PMTB terhadap PDB', '300', '30.00', 'a'),
    household_consumption_share: metric('household_consumption_share', 'konsumsi_rumah_tangga', 'Porsi konsumsi rumah tangga terhadap PDB', '550', '55.00', 'b') } }
}
