import { API_BASE } from '../../api'
import { canBind, candidates, contextGuard, decimalPattern } from './data'
import type { DetailData, HistoryPoint, Selector, SourceReading, SummaryReading } from './types'

type ObjectData = Record<string, unknown>
function object(value: unknown): ObjectData {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('Format objek API tidak sesuai')
  return value as ObjectData
}
function text(value: unknown): string | null {
  if (value == null || value === '') return null
  if (typeof value !== 'string') throw new Error('Format teks API tidak sesuai')
  return value
}
function decimal(value: unknown): string | null {
  const result = text(value)
  if (result !== null && (result.length > 80 || !decimalPattern.test(result))) throw new Error('Format angka API tidak sesuai')
  return result
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error('Format daftar API tidak sesuai')
  return value
}
function parseSummary(raw: unknown, code: string): SummaryReading | null {
  const matches = array(object(raw).indicators).map(object).filter(row => row.id === code)
  if (matches.length > 1) throw new Error('Ringkasan indikator ambigu')
  if (!matches.length) return null
  const row = matches[0]
  if (typeof row.available !== 'boolean') throw new Error('Status ketersediaan tidak sesuai')
  return { id: code, available: row.available, name: text(row.name), category: text(row.category),
    value: decimal(row.value), unit: text(row.unit), period: text(row.period), observationDate: text(row.observationDate),
    frequency: text(row.frequency), dataType: text(row.dataType), sourceId: text(row.sourceId), source: text(row.source),
    publicationDate: text(row.publicationDate), retrievedAt: text(row.retrievedAt), delta: text(row.delta), note: text(row.note) }
}
function parseReading(raw: unknown, code: string): SourceReading {
  const row = object(raw)
  if (row.indicatorCode !== code) throw new Error('Identitas indikator Source Trace tidak cocok')
  const source = row.source == null ? null : object(row.source), file = row.rawFile == null ? null : object(row.rawFile)
  const size = file?.fileSizeBytes
  if (size != null && (typeof size !== 'number' || !Number.isSafeInteger(size) || size < 0)) throw new Error('Ukuran RAW tidak sesuai')
  return { indicatorCode: code, indicatorName: text(row.indicatorName), value: decimal(row.value), unit: text(row.unit),
    period: text(row.period), observationDate: text(row.observationDate), frequency: text(row.frequency), dataType: text(row.dataType),
    publicationDate: text(row.publicationDate), validationStatus: text(row.validationStatus), reviewedAt: text(row.reviewedAt),
    source: source ? { sourceId: text(source.sourceId), sourceName: text(source.sourceName), institution: text(source.institution), primaryUrl: text(source.primaryUrl) } : null,
    rawFile: file ? { documentName: text(file.documentName), sourceUrl: text(file.sourceUrl), checksumSha256: text(file.checksumSha256),
      retrievedAt: text(file.retrievedAt), periodLabel: text(file.periodLabel), fileSizeBytes: typeof size === 'number' ? size : null, downloadUrl: text(file.downloadUrl) } : null }
}
function parseTrace(raw: unknown, code: string): SourceReading[] {
  const payload = object(raw)
  if (payload.indicatorCode !== code) throw new Error('Kode Source Trace tidak cocok')
  if (payload.available === false) return []
  const records = [parseReading(payload, code), ...array(payload.history ?? []).map(row => parseReading(row, code))]
  return [...new Map(records.map(row => [JSON.stringify(row), row])).values()]
}
function parseTrend(raw: unknown, code: string): HistoryPoint[] {
  const payload = object(raw)
  if (payload.id !== code) throw new Error('Kode histori tidak cocok')
  if (payload.available === false) return []
  return array(payload.points).map(value => {
    const row = object(value), numeric = row.value
    if (numeric != null && (typeof numeric !== 'number' || !Number.isFinite(numeric))) throw new Error('Angka histori tidak sesuai')
    const period = text(row.label), unit = text(row.unit) ?? text(payload.unit)
    if (!period || !unit) throw new Error('Periode atau satuan histori tidak tersedia')
    return { period, unit, value: numeric == null ? null : String(numeric), observationDate: text(row.observationDate) ?? undefined }
  })
}
export function summaryMatches(summary: SummaryReading | null, reading: SourceReading | null): boolean {
  return !!summary?.available && !!reading && summary.id === reading.indicatorCode &&
    summary.value === reading.value && summary.unit === reading.unit && summary.period === reading.period &&
    summary.observationDate === reading.observationDate && summary.frequency === reading.frequency &&
    summary.dataType === reading.dataType && summary.sourceId === reading.source?.sourceId &&
    summary.source === reading.source?.institution && summary.publicationDate === reading.publicationDate &&
    summary.retrievedAt === (reading.rawFile?.retrievedAt ?? null)
}
export async function fetchDetail(code: string, selector: Selector | null, signal?: AbortSignal, fetcher: typeof fetch = fetch): Promise<DetailData> {
  if (!/^[a-z][a-z0-9_-]{0,31}$/.test(code)) throw new Error('Kode indikator tidak valid')
  async function get(path: string): Promise<unknown> {
    const response = await fetcher(API_BASE + path, { method: 'GET', signal, credentials: 'omit', cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return response.json()
  }
  const encoded = encodeURIComponent(code)
  const responses = await Promise.allSettled([
    get(`/indicators/?code=${encoded}`).then(raw => parseSummary(raw, code)),
    get(`/indicators/${encoded}/trend/`).then(raw => parseTrend(raw, code)),
    get(`/indicators/${encoded}/source-trace/`).then(raw => parseTrace(raw, code)),
  ] as const)
  if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError')
  const warnings = responses.flatMap((result, i) => result.status === 'rejected' ? [`${['Ringkasan', 'Histori', 'Metadata sumber'][i]} belum tersedia (${String(result.reason instanceof Error ? result.reason.message : 'request gagal')}).`] : [])
  const summary = responses[0].status === 'fulfilled' ? responses[0].value : null
  const history = responses[1].status === 'fulfilled' ? responses[1].value : []
  const records = responses[2].status === 'fulfilled' ? responses[2].value : []
  const keyFor = (reading: SourceReading): Selector => ({date: reading.observationDate ?? '', dataType: reading.dataType ?? '', frequency: reading.frequency ?? '', sourceId: reading.source?.sourceId ?? '', guard: ''})
  const options = await Promise.all(records.filter(reading => canBind(reading) && candidates(records, keyFor(reading)).length === 1).map(async reading => ({ reading, guard: await contextGuard(reading) })))
  let selected: SourceReading | null = records[0] ?? null
  let contextError: string | null = null
  if (selector) {
    const matches = candidates(records, selector)
    selected = matches.length === 1 ? matches[0] : null
    if (!selected) contextError = 'Konteks observasi tidak tersedia atau ambigu. Tidak dialihkan ke angka terbaru.'
    else if (await contextGuard(selected) !== selector.guard) {
      selected = null
      contextError = 'Konteks nilai atau sumber telah berubah. Tidak dialihkan ke revisi atau angka terbaru.'
    }
  } else if (selected && ((canBind(selected) && candidates(records, keyFor(selected)).length !== 1) || (summary && !summaryMatches(summary, selected)))) {
    selected = null
    contextError = 'Ringkasan dan metadata sumber tidak cocok atau konteks berubah. Muat ulang sebelum menggabungkan data.'
  }
  return { summary, selected, options, history, warnings, contextError }
}
