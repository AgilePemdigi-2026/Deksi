import { API_BASE } from '../../api'
import { parseReading } from '../indicators/api'
import { decimalPattern, validDate } from '../indicators/data'
import type { SourceReading } from '../indicators/types'

const schemaVersion = 'deksi.economic-engine.v1'
const methodVersion = 'bps-gdp-shares.v3'
const numerators = { pmtb_share: 'pmtb_nominal', household_consumption_share: 'konsumsi_rumah_tangga' } as const
const digestPattern = /^[a-f0-9]{64}$/
export type Input = { value: string; unit: string; sourceId: string; period: string; observationDate: string;
  frequency: string; dataType: string; publicationDate: string | null; evidenceStatus: string;
  bindingStatus: string; evidenceChecksumSha256: string | null; trace: SourceReading }
export type Metric = { id: string; name: string; available: boolean; value: string | null; unit: string;
  period: string; formula: string; note: string; reason: string | null; priceBasis: string | null;
  methodVersion: string; revisionStatus: 'unknown'; revisionNote: string;
  inputDigest: string; resultDigest: string; inputs: Record<string, Input> }
export type Gdp = { metrics: Record<string, Metric>; reason?: string }

function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('Format perhitungan tidak sesuai')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string' || !value.trim() || value.length > 4096) throw new Error('Teks perhitungan tidak sesuai')
  return value
}
function decimal(value: unknown): string {
  const result = text(value)
  if (result.length > 80 || !decimalPattern.test(result)) throw new Error('Angka perhitungan tidak sesuai')
  return result
}
function digest(value: unknown): string {
  const result = text(value)
  if (!digestPattern.test(result)) throw new Error('Identitas perhitungan tidak sesuai')
  return result
}
function negativeNonzero(value: string): boolean { return value.startsWith('-') && /[1-9]/.test(value) }

export function matchesInput(code: string, input: Input, reading: SourceReading): boolean {
  const canonical = (value: string | null) => value?.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '')
  return reading.indicatorCode === code && canonical(reading.value) === canonical(input.value) &&
    reading.unit === input.unit && reading.period === input.period && reading.observationDate === input.observationDate &&
    reading.frequency === input.frequency && reading.dataType === input.dataType &&
    reading.source?.sourceId === input.sourceId && reading.publicationDate === input.publicationDate &&
    (reading.rawFile?.checksumSha256 ?? null) === input.evidenceChecksumSha256
}

function parseInput(value: unknown, code: string, period: string, observationDate: string): Input {
  const row = object(value)
  if (row.unit !== 'Rp miliar' || row.sourceId !== 'BPS' || row.frequency !== 'quarterly' || row.dataType !== 'level' ||
    row.period !== period || row.observationDate !== observationDate ||
    (row.publicationDate !== null && (typeof row.publicationDate !== 'string' || !validDate(row.publicationDate))) ||
    !['integrity_ok', 'missing', 'unavailable_or_invalid'].includes(String(row.evidenceStatus)) ||
    !['matched', 'mismatch', 'unavailable'].includes(String(row.bindingStatus))) throw new Error('Konteks input tidak sesuai')
  const checksum = row.evidenceChecksumSha256 === null ? null : digest(row.evidenceChecksumSha256)
  if (row.bindingStatus === 'matched' && (row.evidenceStatus !== 'integrity_ok' || checksum === null)) throw new Error('Bukti input tidak konsisten')
  const input: Input = { value: decimal(row.value), unit: row.unit, sourceId: row.sourceId, frequency: row.frequency,
    dataType: row.dataType, period, observationDate, publicationDate: row.publicationDate as string | null,
    evidenceStatus: text(row.evidenceStatus), bindingStatus: text(row.bindingStatus), evidenceChecksumSha256: checksum,
    trace: parseReading(row.trace, code) }
  if (!matchesInput(code, input, input.trace) || input.trace.validationStatus !== 'published' || !input.trace.reviewedAt) {
    throw new Error('Source Trace tidak cocok dengan input perhitungan')
  }
  return input
}

export function parseGdp(raw: unknown): Gdp {
  const payload = object(raw), rows = object(payload.metrics)
  if (payload.schemaVersion !== schemaVersion || payload.methodVersion !== methodVersion) throw new Error('Versi perhitungan tidak didukung')
  if (Object.keys(rows).length === 0) return { metrics: {}, reason: text(payload.reason) }
  if (Object.keys(rows).length !== 2 || Object.keys(rows).some(id => !(id in numerators))) throw new Error('Identitas metrik tidak sesuai')
  const metrics: Record<string, Metric> = {}
  let selectedDate: string | null = null
  for (const [id, numerator] of Object.entries(numerators)) {
    const row = object(rows[id]), date = text(row.observationDate), period = text(row.period)
    if (!validDate(date) || !/^\d{4}-(03-31|06-30|09-30|12-31)$/.test(date) ||
      period !== `Q${Number(date.slice(5, 7)) / 3} ${Number(date.slice(0, 4))}` ||
      (selectedDate !== null && date !== selectedDate)) throw new Error('Periode perhitungan tidak sesuai')
    selectedDate = date
    if (row.id !== id || row.schemaVersion !== schemaVersion || row.methodVersion !== methodVersion ||
      row.formula !== `${numerator} / pdb_nominal * 100` || row.formulaVersion !== '2' ||
      row.classification !== 'DEKSI-derived' || row.officialVerification !== 'unassessed' ||
      row.snapshotPersistence !== 'response_only' || row.roundingMode !== 'ROUND_HALF_EVEN' || row.decimalPlaces !== 2 ||
      row.revisionStatus !== 'unknown' ||
      row.unit !== '%' || typeof row.available !== 'boolean' ||
      (row.priceBasis !== null && row.priceBasis !== 'current_prices')) throw new Error('Metodologi perhitungan tidak sesuai')
    const inputRows = object(row.inputs), inputs: Record<string, Input> = {}
    if (Object.keys(inputRows).length !== 0 && (Object.keys(inputRows).length !== 2 ||
      Object.keys(inputRows).some(code => code !== numerator && code !== 'pdb_nominal'))) throw new Error('Input perhitungan tidak sesuai')
    for (const [code, value] of Object.entries(inputRows)) inputs[code] = parseInput(value, code, period, date)
    const numeric = row.value === null ? null : decimal(row.value)
    if (row.available) {
      if (numeric === null || !/^-?\d+\.\d{2}$/.test(numeric) || negativeNonzero(numeric) || row.reason !== null ||
        row.reasonCode !== null || row.priceBasis !== 'current_prices' || Object.keys(inputs).length !== 2 ||
        Object.values(inputs).some(input => input.bindingStatus !== 'matched' || negativeNonzero(input.value)) ||
        !/[1-9]/.test(inputs.pdb_nominal.value)) throw new Error('Hasil tersedia tidak didukung input yang memenuhi syarat')
    } else if (numeric !== null || typeof row.reason !== 'string' || !row.reason.trim() ||
      typeof row.reasonCode !== 'string' || !row.reasonCode.trim()) throw new Error('Status data hilang tidak konsisten')
    metrics[id] = { id, name: text(row.name), available: row.available, value: numeric, unit: '%', period,
      formula: text(row.formula), note: text(row.note), reason: row.reason === null ? null : text(row.reason),
      priceBasis: row.priceBasis as string | null, methodVersion, revisionStatus: 'unknown',
      revisionNote: text(row.revisionNote), inputDigest: digest(row.inputDigest),
      resultDigest: digest(row.resultDigest), inputs }
  }
  return { metrics }
}

export async function fetchGdp(signal?: AbortSignal, fetcher: typeof fetch = fetch, timeoutMs = 15_000): Promise<Gdp> {
  if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError')
  const controller = new AbortController()
  const cancel = () => controller.abort(new DOMException('Request cancelled', 'AbortError'))
  let rejectAbort: () => void = () => {}
  const aborted = new Promise<never>((_, reject) => {
    rejectAbort = () => reject(controller.signal.reason)
    controller.signal.addEventListener('abort', rejectAbort, { once: true })
  })
  signal?.addEventListener('abort', cancel, { once: true })
  const timer = setTimeout(() => controller.abort(new DOMException('Batas waktu perhitungan terlampaui', 'TimeoutError')), timeoutMs)
  try {
    return await Promise.race([aborted, (async () => {
      const response = await fetcher(`${API_BASE}/economic-engine/gdp/`, {
        method: 'GET', signal: controller.signal, credentials: 'omit', cache: 'no-store' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = parseGdp(await response.json())
      if (controller.signal.aborted) throw controller.signal.reason
      return data
    })()])
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', cancel)
    controller.signal.removeEventListener('abort', rejectAbort)
  }
}
