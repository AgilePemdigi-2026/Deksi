import { adminFetch, withCandidateDeadline } from '../../api'
import type {
  NarrativeCapabilities, NarrativeDecision, NarrativeDraft, NarrativeDraftEnvelope,
  NarrativeObservation, NarrativePage, NarrativeRequest,
} from './types'

const path = '/admin/ai-narratives'
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const generationStatuses = ['queued', 'running', 'ready', 'failed', 'unknown']
const reviewStatuses = ['pending', 'approved', 'needs_revision', 'rejected']
const decisions = ['approved', 'needs_revision', 'rejected']

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function validFact(value: unknown): boolean {
  if (!record(value) || typeof value.observationId !== 'number' || !Number.isSafeInteger(value.observationId) || value.observationId <= 0 ||
      value.indicatorCode !== 'pdb' || typeof value.indicatorName !== 'string' || typeof value.value !== 'string' ||
      value.unit !== '%' || typeof value.period !== 'string' || typeof value.observationDate !== 'string' ||
      value.frequency !== 'quarterly' || value.dataType !== 'yoy' ||
      !(value.publicationDate === null || typeof value.publicationDate === 'string') || !record(value.source) ||
      value.source.sourceId !== 'BPS' || typeof value.source.sourceName !== 'string' ||
      typeof value.source.institution !== 'string' || !(value.source.primaryUrl === null || typeof value.source.primaryUrl === 'string') ||
      value.publicationStatus !== 'reviewed_published' || value.officialVerification !== 'unassessed' || !record(value.evidence) ||
      typeof value.evidence.status !== 'string' ||
      !(value.evidence.rawFileId === null || (typeof value.evidence.rawFileId === 'number' && Number.isSafeInteger(value.evidence.rawFileId))) ||
      !(value.evidence.checksumSha256 === null || typeof value.evidence.checksumSha256 === 'string') ||
      !(value.evidence.fileSizeBytes === null || (typeof value.evidence.fileSizeBytes === 'number' && Number.isSafeInteger(value.evidence.fileSizeBytes))) ||
      !(value.evidence.retrievedAt === null || typeof value.evidence.retrievedAt === 'string') || typeof value.sourceTracePath !== 'string') return false
  return true
}

function validDraft(value: unknown): value is NarrativeDraft {
  if (!record(value) || typeof value.id !== 'number' || !Number.isSafeInteger(value.id) || value.id <= 0 ||
      typeof value.requestKey !== 'string' || !UUID.test(value.requestKey) ||
      !generationStatuses.includes(String(value.generationStatus)) || !reviewStatuses.includes(String(value.reviewStatus)) ||
      !record(value.factPackage) || value.factPackage.schemaVersion !== 'deksi.ai-facts.v1' ||
      value.factPackage.methodVersion !== 'pdb-yoy-facts.v1' || value.factPackage.inputDigest !== value.inputDigest ||
      !Array.isArray(value.factPackage.derivedMetrics) || value.factPackage.derivedMetrics.length !== 0 ||
      !record(value.factPackage.facts) ||
      !validFact(value.factPackage.facts.current) ||
      !(value.factPackage.facts.comparison === null || validFact(value.factPackage.facts.comparison)) ||
      !Array.isArray(value.factPackage.comparisons) || value.factPackage.comparisons.some(item => !record(item) || typeof item.value !== 'string' || item.unit !== 'percentage_point') ||
      !Array.isArray(value.factPackage.missingData) || !value.factPackage.missingData.every(item => typeof item === 'string') ||
      !Array.isArray(value.factPackage.limitations) || !value.factPackage.limitations.every(item => typeof item === 'string') || typeof value.inputDigest !== 'string' ||
      !(value.contentDigest === null || typeof value.contentDigest === 'string') ||
      typeof value.requestedModel !== 'string' || !(value.reportedModel === null || typeof value.reportedModel === 'string') ||
      typeof value.promptVersion !== 'string' || typeof value.validatorVersion !== 'string' ||
      !(value.narrative === null || (record(value.narrative) && typeof value.narrative.summary === 'string' &&
        typeof value.narrative.meaning === 'string' && (value.narrative.comparison === null || typeof value.narrative.comparison === 'string') &&
        typeof value.narrative.limitations === 'string' && Array.isArray(value.narrative.factRefs) && value.narrative.factRefs.every(ref => typeof ref === 'string'))) ||
      !(value.errorCode === null || typeof value.errorCode === 'string') || !(value.errorMessage === null || typeof value.errorMessage === 'string') ||
      typeof value.createdAt !== 'string' || !(value.startedAt === null || typeof value.startedAt === 'string') ||
      !(value.finishedAt === null || typeof value.finishedAt === 'string') ||
      !(value.parentId === null || (typeof value.parentId === 'number' && Number.isSafeInteger(value.parentId) && value.parentId > 0)) || typeof value.active !== 'boolean' ||
      !(value.reconciledAt === null || typeof value.reconciledAt === 'string') ||
      !(value.review === null || (record(value.review) && decisions.includes(String(value.review.decision)) &&
        typeof value.review.notes === 'string' && typeof value.review.reviewedAt === 'string' && typeof value.review.contentDigest === 'string'))) return false
  return true
}

function validObservation(value: unknown): value is NarrativeObservation {
  return record(value) && typeof value.id === 'number' && Number.isSafeInteger(value.id) && value.id > 0 && typeof value.value === 'string' &&
    value.unit === '%' && typeof value.period === 'string' && typeof value.observationDate === 'string' &&
    (value.publicationDate === null || typeof value.publicationDate === 'string')
}

function validPage<T>(value: unknown, page: number, validItem: (item: unknown) => item is T): value is NarrativePage<T> {
  return record(value) && Array.isArray(value.items) && value.items.every(validItem) && value.page === page &&
    value.pageSize === 20 && typeof value.total === 'number' && Number.isSafeInteger(value.total) && value.total >= 0 && typeof value.hasNext === 'boolean'
}

export class NarrativeApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

function safeError(status: number): NarrativeApiError {
  const messages: Record<number, string> = {
    401: 'Sesi Admin tidak tersedia. Masuk kembali sebelum melanjutkan.',
    403: 'Akses narasi AI ditolak. Periksa izin Admin.',
    409: 'Terjadi konflik versi atau status. Muat ulang detail sebelum mengambil tindakan baru.',
    400: 'Permintaan tidak valid. Periksa pilihan observasi dan catatan.',
    503: 'Layanan narasi belum tersedia atau belum dikonfigurasi.',
  }
  return new NarrativeApiError(status, messages[status] ?? 'Permintaan narasi tidak dapat dipastikan. Periksa status sebelum mencoba lagi.')
}

async function readJson(response: Response): Promise<unknown> {
  try { return await response.json() } catch { throw new Error('Respons layanan narasi tidak valid.') }
}

async function get<T>(route: string, validate: (value: unknown) => value is T, options?: { timeoutMs?: number }): Promise<T> {
  return withCandidateDeadline(async signal => {
    const response = await adminFetch(`${path}${route}`, { signal })
    if (!response.ok) throw safeError(response.status)
    const body = await readJson(response)
    if (!validate(body)) throw new Error('Respons layanan narasi tidak valid.')
    return body
  }, options?.timeoutMs)
}

function envelope(value: unknown): value is NarrativeDraftEnvelope {
  return record(value) && validDraft(value.draft)
}

export function fetchNarrativeCapabilities(options?: { timeoutMs?: number }): Promise<NarrativeCapabilities> {
  return get('/capabilities/', (value): value is NarrativeCapabilities => record(value) &&
    typeof value.canRead === 'boolean' && typeof value.canGenerate === 'boolean' &&
    typeof value.canReview === 'boolean' && typeof value.generationConfigured === 'boolean', options)
}

export function fetchNarrativeObservations(page: number, options?: { timeoutMs?: number }): Promise<NarrativePage<NarrativeObservation>> {
  if (!Number.isSafeInteger(page) || page < 1) return Promise.reject(new Error('Halaman observasi tidak valid.'))
  return get(`/observations/?page=${page}`, (value): value is NarrativePage<NarrativeObservation> => validPage(value, page, validObservation), options)
}

export function fetchNarrativeDrafts(page: number, options?: { timeoutMs?: number }): Promise<NarrativePage<NarrativeDraft>> {
  if (!Number.isSafeInteger(page) || page < 1) return Promise.reject(new Error('Halaman draft tidak valid.'))
  return get(`/?page=${page}`, (value): value is NarrativePage<NarrativeDraft> => validPage(value, page, validDraft), options)
}

export function fetchNarrativeDraft(id: number, options?: { timeoutMs?: number }): Promise<NarrativeDraftEnvelope> {
  if (!Number.isSafeInteger(id) || id < 1) return Promise.reject(new Error('Identitas draft tidak valid.'))
  return get(`/${id}/`, (value): value is NarrativeDraftEnvelope => envelope(value) && value.draft.id === id, options)
}

export function lookupNarrativeRequest(requestKey: string, options?: { timeoutMs?: number }): Promise<{ draft: NarrativeDraft | null }> {
  if (!UUID.test(requestKey)) return Promise.reject(new Error('Identitas permintaan tidak valid.'))
  return get(`/lookup/?requestKey=${encodeURIComponent(requestKey)}`,
    (value): value is { draft: NarrativeDraft | null } => record(value) && (value.draft === null || validDraft(value.draft)), options)
}

export function requestNarrativeDraft(request: NarrativeRequest, options?: { timeoutMs?: number }): Promise<NarrativeDraftEnvelope> {
  if (!UUID.test(request.requestKey) || !Number.isSafeInteger(request.observationId) || request.observationId < 1 ||
      !(request.comparisonId === null || (Number.isSafeInteger(request.comparisonId) && request.comparisonId > 0)) ||
      !(request.parentId === null || (Number.isSafeInteger(request.parentId) && request.parentId > 0))) {
    return Promise.reject(new Error('Pilihan fakta atau identitas permintaan tidak valid.'))
  }
  return withCandidateDeadline(async signal => {
    const response = await adminFetch(`${path}/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request), signal,
    })
    if (response.status !== 200 && response.status !== 202) throw safeError(response.status)
    const body = await readJson(response)
    if (!envelope(body) || body.draft.requestKey !== request.requestKey) throw new Error('Respons antrean tidak sesuai. Periksa status dengan kunci permintaan yang sama.')
    return body
  }, options?.timeoutMs)
}

export function reviewNarrativeDraft(id: number, payload: { contentDigest: string; decision: NarrativeDecision; notes: string }, options?: { timeoutMs?: number }): Promise<NarrativeDraftEnvelope> {
  if (!Number.isSafeInteger(id) || id < 1 || !payload.contentDigest.trim() || !decisions.includes(payload.decision) ||
      (payload.decision !== 'approved' && !payload.notes.trim())) return Promise.reject(new Error('Digest dan catatan untuk keputusan non-persetujuan wajib diisi.'))
  return withCandidateDeadline(async signal => {
    const response = await adminFetch(`${path}/${id}/review/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal,
    })
    if (!response.ok) throw safeError(response.status)
    const body = await readJson(response)
    if (!envelope(body) || body.draft.id !== id || body.draft.review?.decision !== payload.decision ||
        body.draft.review.contentDigest !== payload.contentDigest || body.draft.contentDigest !== payload.contentDigest) {
      throw new Error('Keputusan belum dapat dipastikan. Periksa detail draft dan digest sebelum tindakan lain.')
    }
    return body
  }, options?.timeoutMs)
}

export function reconcileNarrativeDraft(id: number, payload: { acknowledged: true; notes: string }, options?: { timeoutMs?: number }): Promise<NarrativeDraftEnvelope> {
  if (!Number.isSafeInteger(id) || id < 1 || payload.acknowledged !== true || !payload.notes.trim()) return Promise.reject(new Error('Konfirmasi dan catatan rekonsiliasi wajib diisi.'))
  return withCandidateDeadline(async signal => {
    const response = await adminFetch(`${path}/${id}/reconcile/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal,
    })
    if (!response.ok) throw safeError(response.status)
    const body = await readJson(response)
    if (!envelope(body) || body.draft.id !== id || body.draft.generationStatus !== 'unknown' || !body.draft.reconciledAt) {
      throw new Error('Rekonsiliasi belum dapat dipastikan. Periksa detail draft sebelum tindakan lain.')
    }
    return body
  }, options?.timeoutMs)
}
