import type { Gdp } from './economicEngineClient'

const API_BASE = '/api'

export type PublicEngineAIStatus = 'queued' | 'running' | 'ready' | 'failed' | 'unknown' | 'approved' | 'rejected' | 'stale'
export type PublicEngineAIRequest = { requestKey: string; status: PublicEngineAIStatus; period: string; resultDigest?: string; metricsBinding?: unknown; narrative?: unknown }
export type PublicEngineAIReview = { id: number; period: string; resultDigest: string; contentDigest: string; snapshot: unknown; narrative: unknown }
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const digestPattern = /^[a-f0-9]{64}$/
const statuses = new Set<PublicEngineAIStatus>(['queued', 'running', 'ready', 'failed', 'unknown', 'approved', 'rejected', 'stale'])
const object = (value: unknown): Record<string, unknown> | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null

export function matchesMetricBindings(value: unknown, data: Gdp): boolean {
  const bindings = object(value)
  const available = Object.entries(data.metrics).filter(([, metric]) => metric.available)
  if (!bindings || available.length === 0 || Object.keys(bindings).length !== available.length) return false
  return available.every(([id, metric]) => {
    const binding = object(bindings[id])
    return binding?.inputDigest === metric.inputDigest && binding?.resultDigest === metric.resultDigest
  })
}

function parseRequest(value: unknown, metadataOnly = false): PublicEngineAIRequest {
  const row = object(value)
  if (!row || typeof row.requestKey !== 'string' || !uuidPattern.test(row.requestKey) || typeof row.status !== 'string' ||
    !statuses.has(row.status as PublicEngineAIStatus) || typeof row.period !== 'string' || !row.period.trim()) throw new Error('Respons Economic Engine AI tidak valid.')
  if (row.resultDigest !== undefined && (typeof row.resultDigest !== 'string' || !digestPattern.test(row.resultDigest))) throw new Error('Identitas hasil Economic Engine AI tidak valid.')
  if (!metadataOnly && row.status === 'approved' && (typeof row.narrative !== 'string' && !object(row.narrative))) throw new Error('Narasi yang disetujui tidak valid.')
  return row as PublicEngineAIRequest
}

async function csrf(fetcher: typeof fetch): Promise<string> {
  const response = await fetcher(`${API_BASE}/auth/csrf/`, { method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'error' })
  if (!response.ok) throw new Error('Token keamanan tidak tersedia. Coba lagi.')
  const body = object(await response.json().catch(() => null))
  if (typeof body?.csrfToken !== 'string' || !body.csrfToken) throw new Error('Token keamanan tidak valid.')
  return body.csrfToken
}

export async function createPublicEngineAIRequest(quarter: string, fetcher: typeof fetch = fetch,
  getCsrf: (fetcher: typeof fetch) => Promise<string> = csrf, makeKey: () => string = () => crypto.randomUUID(), existingKey?: string): Promise<PublicEngineAIRequest> {
  if (!/^[0-9]{4}-(03-31|06-30|09-30|12-31)$/.test(quarter) || Number.isNaN(Date.parse(`${quarter}T00:00:00Z`))) throw new Error('Periode triwulan tidak valid.')
  const requestKey = existingKey ?? makeKey()
  if (!uuidPattern.test(requestKey)) throw new Error('Identitas permintaan tidak valid.')
  const token = await getCsrf(fetcher)
  const response = await fetcher(`${API_BASE}/public-engine-ai/requests/`, {
    method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token }, body: JSON.stringify({ requestKey, quarter }),
  })
  const body = object(await response.json().catch(() => null))
  if (!response.ok) throw new Error(response.status === 409 ? 'Data atau permintaan berubah. Muat ulang perhitungan sebelum mencoba kembali.'
    : response.status === 429 ? 'Batas permintaan harian tercapai. Coba lagi nanti.'
    : response.status === 403 ? 'Permintaan ditolak oleh pemeriksaan keamanan.' : `Permintaan narasi belum dapat diproses (HTTP ${response.status}).`)
  const row = parseRequest(body?.request, true)
  if (row.period !== quarterLabel(quarter)) throw new Error('Respons permintaan tidak cocok dengan periode yang dipilih.')
  return row
}

export function quarterLabel(date: string): string {
  const match = /^([0-9]{4})-(03|06|09|12)-[0-9]{2}$/.exec(date)
  return match ? `Q${Number(match[2]) / 3} ${match[1]}` : date
}

export async function getPublicEngineAIRequest(key: string, fetcher: typeof fetch = fetch): Promise<PublicEngineAIRequest> {
  if (!uuidPattern.test(key)) throw new Error('Identitas permintaan tidak valid.')
  const response = await fetcher(`${API_BASE}/public-engine-ai/requests/${encodeURIComponent(key)}/`, { method: 'GET', credentials: 'omit', cache: 'no-store', redirect: 'error' })
  if (!response.ok) throw new Error(response.status === 404 ? 'Permintaan tidak ditemukan.' : `Status narasi belum dapat diperiksa (HTTP ${response.status}).`)
  const body = object(await response.json().catch(() => null)), row = parseRequest(body?.request)
  if (row.requestKey !== key) throw new Error('Status permintaan tidak cocok.')
  return row
}

export async function fetchPublicEngineAIReviews(fetcher: typeof fetch = fetch): Promise<PublicEngineAIReview[]> {
  const response = await fetcher(`${API_BASE}/admin/public-engine-ai/`, { method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'error' })
  if (!response.ok) throw new Error(response.status === 401 ? 'Sesi Admin berakhir. Masuk kembali.' : response.status === 403 ? 'Akun tidak memiliki izin review Economic Engine AI.' : 'Daftar review tidak dapat dimuat.')
  const body = object(await response.json().catch(() => null))
  if (!Array.isArray(body?.items)) throw new Error('Respons daftar review tidak valid.')
  return body.items.map(value => {
    const row = object(value)
    if (!row || !Number.isSafeInteger(row.id) || typeof row.period !== 'string' || typeof row.resultDigest !== 'string' || !digestPattern.test(row.resultDigest) ||
      typeof row.contentDigest !== 'string' || !digestPattern.test(row.contentDigest) || row.narrative == null) throw new Error('Item review tidak valid.')
    return row as PublicEngineAIReview
  })
}

export async function submitPublicEngineAIReview(item: PublicEngineAIReview, decision: 'approved' | 'rejected', notes: string,
  fetcher: typeof fetch = fetch, getCsrf: (fetcher: typeof fetch) => Promise<string> = csrf): Promise<void> {
  if (!Number.isSafeInteger(item.id) || !digestPattern.test(item.contentDigest) || !['approved', 'rejected'].includes(decision) || notes.length > 500) throw new Error('Keputusan atau catatan review tidak valid.')
  const token = await getCsrf(fetcher)
  const response = await fetcher(`${API_BASE}/admin/public-engine-ai/${item.id}/review/`, {
    method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token }, body: JSON.stringify({ contentDigest: item.contentDigest, decision, notes }),
  })
  const body = object(await response.json().catch(() => null))
  if (!response.ok) throw new Error(response.status === 409 ? 'Snapshot berubah. Muat ulang daftar sebelum memutuskan.' : response.status === 403 ? 'Review ditolak: periksa sesi, izin, atau token keamanan.' : `Keputusan review belum tersimpan (HTTP ${response.status}).`)
  if (body?.id !== item.id || body.status !== decision || (decision === 'approved' && body.contentDigest !== item.contentDigest) || (decision === 'rejected' && body.contentDigest !== '')) throw new Error('Respons review tidak cocok. Muat ulang daftar untuk memastikan status.')
}
