import type { HistoryPoint, Route, Selector, SourceReading } from './types'

export const INDICATORS = [
  ['pdb', 'PDB'], ['inflasi', 'Inflasi'], ['fiskal', 'Fiskal'],
  ['investasi', 'Investasi'], ['birate', 'BI-Rate'], ['tpt', 'Pengangguran'],
] as const
export const decimalPattern = /^-?\d+(?:\.\d+)?$/
const frequencies = new Set(['daily', 'monthly', 'quarterly', 'semiannual', 'annual', 'adhoc'])
const dataTypes = new Set(['level', 'yoy', 'cumulative_ytd', 'derived_sum', 'event'])
export function validDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value
}
export function parseRoute(pathname: string, search = ''): Route {
  if (pathname === '/') return { kind: 'dashboard' }
  const path = /^\/indikator\/([a-z][a-z0-9_-]{0,31})(\/sumber)?\/?$/.exec(pathname)
  if (!path) return { kind: 'not-found' }
  const query = new URLSearchParams(search)
  const keys = ['tanggal', 'tipe', 'frekuensi', 'sumber', 'konteks']
  if ([...query.keys()].some(key => !keys.includes(key) || query.getAll(key).length !== 1)) return { kind: 'not-found' }
  let selector: Selector | null = null
  if (query.size) {
    const date = query.get('tanggal') ?? '', dataType = query.get('tipe') ?? ''
    const frequency = query.get('frekuensi') ?? '', sourceId = query.get('sumber') ?? '', guard = query.get('konteks') ?? ''
    if (query.size !== keys.length || !validDate(date) || !dataTypes.has(dataType) || !frequencies.has(frequency) || !/^[A-Za-z0-9_-]{1,64}$/.test(sourceId) || !/^[a-f0-9]{64}$/.test(guard)) return { kind: 'not-found' }
    selector = { date, dataType, frequency, sourceId, guard }
  }
  return { kind: path[2] ? 'source' : 'detail', code: path[1], selector }
}

// Ported from the fixture checkpoint: display formatting only, never economic calculation.
export function formatDecimal(value: string | null | undefined): string {
  if (value == null || !decimalPattern.test(value)) return 'Belum tersedia'
  const [integer, fraction] = value.split('.')
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (fraction === undefined ? '' : `,${fraction}`)
}
export function safeExternalUrl(raw: string | null | undefined): string | null {
  if (!raw || raw !== raw.trim() || raw.includes('\\') || Array.from(raw).some(c => c.charCodeAt(0) <= 32 || c.charCodeAt(0) === 127)) return null
  try {
    const url = new URL(raw)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}
export function canBind(reading: SourceReading): boolean {
  return reading.observationDate !== null && validDate(reading.observationDate) && !!reading.period && !!reading.unit &&
    frequencies.has(reading.frequency ?? '') && dataTypes.has(reading.dataType ?? '') && /^[A-Za-z0-9_-]{1,64}$/.test(reading.source?.sourceId ?? '')
}
export async function contextGuard(reading: SourceReading): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(reading)))
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('')
}
export function contextHref(reading: SourceReading, guard: string, source = false): string {
  if (!canBind(reading) || !/^[a-f0-9]{64}$/.test(guard)) throw new Error('Konteks observasi belum lengkap')
  return `/indikator/${encodeURIComponent(reading.indicatorCode)}${source ? '/sumber' : ''}?${new URLSearchParams({
    tanggal: reading.observationDate!, tipe: reading.dataType!, frekuensi: reading.frequency!, sumber: reading.source!.sourceId!, konteks: guard,
  })}`
}
export function candidates(readings: SourceReading[], selector: Selector): SourceReading[] {
  return readings.filter(row => row.observationDate === selector.date && row.dataType === selector.dataType && row.frequency === selector.frequency && row.source?.sourceId === selector.sourceId)
}
export function chartGeometry(history: HistoryPoint[], unit: string) {
  if (history.some(p => p.unit !== unit)) return null
  const values = history.map(p => p.value === null ? null : Number(p.value))
  const valid = values.filter((v): v is number => v !== null && Number.isFinite(v))
  if (valid.length === 0) return { segments: [] as string[], points: [] as { x: number; y: number; period: string; value: string }[] }
  const min = Math.min(...valid), max = Math.max(...valid), span = max - min || 1
  const points = values.map((v, i) => v === null || !Number.isFinite(v) ? null : {
    x: history.length === 1 ? 380 : 44 + i * 672 / (history.length - 1),
    y: max === min ? 110 : 28 + (max - v) / span * 164,
    period: history[i].period, value: history[i].value!,
  })
  const segments: string[] = []; let current: string[] = []
  for (const point of points) {
    if (point) current.push(`${point.x},${point.y}`)
    else if (current.length) { segments.push(current.join(' ')); current = [] }
  }
  if (current.length) segments.push(current.join(' '))
  return { segments, points: points.filter(p => p !== null) }
}
