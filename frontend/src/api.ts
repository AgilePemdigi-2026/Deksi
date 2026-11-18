import { useEffect, useState } from "react";
import type { SyncHistoryQuery, SyncHistoryResult } from "./features/sync-history/types";
import { createAuthClient } from "./features/admin/auth";

export const API_BASE = "/api";

export type Direction = "up" | "down" | "flat";

export interface UpdateLog {
  updatedAt: string | null;
  formatted: string | null;
  updatedBy: string | null;
  source: string;
  status: string;
  observationCount: number;
  message: string;
}

export interface SummaryCard {
  id: string;
  available: boolean;
  name: string;
  category: string;
  value: string | null;
  unit: string;
  period: string | null;
  latestPeriod: string | null;
  latestYear: number | null;
  hasCurrentYearData: boolean;
  note: string;
  dataAvailabilityNote?: string;
  observationDate?: string;
  source: string;
  delta: string | null;
  deltaDirection: Direction;
  deltaPositive: boolean;
  sparkline: number[];
}

export interface SummaryResponse {
  updatedAt: string | null;
  updatedAtFormatted: string | null;
  lastUpdate: UpdateLog | null;
  indicators: SummaryCard[];
}

export interface TrendPoint {
  label: string;
  value: number;
  unit?: string;
  year?: number;
}

export interface TrendResponse {
  id: string;
  available: boolean;
  granularities: string[];
  granularity: string;
  unit: string;
  points: TrendPoint[];
  latestAvailable: string | null;
  hasCurrentYearData: boolean;
  dataAvailableUntil: string | null;
  dataAvailabilityNote: string;
  historicalAverage: number;
  note: string;
}

const FALLBACK_UPDATE: SummaryCard[] = [];

export function useDashboardData() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/indicators/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as SummaryResponse;
        if (!cancelled) {
          setSummary(body);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("Tidak dapat menghubungi backend DEKSI.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { summary, loading, error, cards: summary?.indicators ?? FALLBACK_UPDATE };
}

export function useTrend(code: string) {
  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previousCode, setPreviousCode] = useState(code);
  if (previousCode !== code) {
    setPreviousCode(code);
    setLoading(true);
  }

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/indicators/${code}/trend/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as TrendResponse;
        if (!cancelled) {
          setTrend(body);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("Data historis tidak tersedia.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [code]);

  return { trend, loading, error };
}

// ---------------------------------------------------------------------------
// Fitur 5 – Filter Dashboard
// ---------------------------------------------------------------------------

export interface CategoryEntry {
  category: string;
  codes: string[];
}

export interface FilteredSummaryResponse extends SummaryResponse {
  activeFilters: { category?: string; year?: number };
}

export interface DashboardFilters {
  category: string;
  year: string;
}

export function useDashboardFilter(filters: DashboardFilters) {
  const [summary, setSummary] = useState<FilteredSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const filterKey = JSON.stringify([filters.category, filters.year]);
  const [previousFilter, setPreviousFilter] = useState(filterKey);
  if (previousFilter !== filterKey) {
    setPreviousFilter(filterKey);
    setLoading(true);
  }

  useEffect(() => {
    let cancelled = false;

    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.year)     params.set("year", filters.year);

    const url = `${API_BASE}/indicators/dashboard/${params.toString() ? "?" + params : ""}`;

    const load = async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as FilteredSummaryResponse;
        if (!cancelled) { setSummary(body); setError(null); }
      } catch {
        if (!cancelled) setError("Tidak dapat memuat data dashboard.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [filters.category, filters.year]);

  return { summary, loading, error, cards: summary?.indicators ?? [] };
}

export function useIndicatorCategories() {
  const [categories, setCategories] = useState<CategoryEntry[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/indicators/categories/`)
      .then((r) => r.json())
      .then((body) => { if (body?.categories) setCategories(body.categories); })
      .catch(() => {});
  }, []);

  return categories;
}

// ---------------------------------------------------------------------------
// Fitur 9 – Daftar Sumber Data / Source Trace (UC-04, publik tanpa login)
// ---------------------------------------------------------------------------

export type ValueType = "Official Source Value" | "DEKSI-Derived Metric";

export interface SourceEntry {
  sourceId: string;
  sourceName: string;
  institution: string;
  primaryUrl: string;
  description: string;
  acquisitionMethod?: string;
  dataFormat?: string;
  frequency?: string;
  updateSchedule?: string;
  status?: string;
  indicators: string[];
  indicatorCount: number;
  observationCount: number;
  available: boolean;
  latestPeriod: string | null;
  latestObservationDate: string | null;
}

export interface SourceIndicatorEntry {
  id: string;
  code: string;
  name: string;
  category: string;
  unit: string;
  available: boolean;
  value: string | null;
  period: string | null;
  observationDate: string | null;
  publicationDate: string | null;
  retrievedAt: string | null;
  dataType: string | null;
  valueType: ValueType | null;
  observationCount: number;
  note?: string;
}

export interface SourceDetail extends SourceEntry {
  indicatorDetails: SourceIndicatorEntry[];
}

export interface TraceRawFile {
  documentName: string;
  sourceUrl: string;
  checksumSha256: string;
  retrievedAt: string | null;
  periodLabel: string;
  fileSizeBytes: number;
  downloadUrl: string;
}

export interface TraceDerived {
  formula: string;
  comparisonPeriod: string | null;
  comparisonObservationDate: string | null;
  inputValue: string | null;
  inputUnit: string | null;
  inputSource: string | null;
}

export interface SourceTrace {
  indicatorCode: string;
  indicatorName: string;
  available: boolean;
  valueType?: ValueType;
  value: string | null;
  unit: string;
  period: string | null;
  periodLabel?: string | null;
  observationDate: string | null;
  frequency: string | null;
  dataType: string | null;
  institution?: string | null;
  publicationName?: string | null;
  publicationDate: string | null;
  publicationUrl?: string | null;
  retrievedAt?: string | null;
  version?: string | null;
  revision?: string | null;
  validationStatus?: string;
  reviewedAt?: string | null;
  source?: { sourceId: string; sourceName: string; institution: string; primaryUrl: string };
  rawFile: TraceRawFile | null;
  derived?: TraceDerived | null;
  history?: SourceTrace[];
  note?: string;
}

export const UNAVAILABLE = "Tidak tersedia";

export function displayOrUnavailable(value: string | null | undefined): string {
  if (value === null || value === undefined) return UNAVAILABLE;
  const text = String(value).trim();
  return text === "" ? UNAVAILABLE : text;
}

export async function fetchSources(): Promise<SourceEntry[]> {
  const res = await fetch(`${API_BASE}/sources/`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  return (body?.sources ?? []) as SourceEntry[];
}

export async function fetchSourceDetail(sourceId: string): Promise<SourceDetail> {
  const res = await fetch(`${API_BASE}/sources/${encodeURIComponent(sourceId)}/`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as SourceDetail;
}

export async function fetchSourceTrace(
  code: string,
  // Parameter legacy (period/observation_date) tidak lagi dikirim: backend
  // Source Trace kini hanya menerima selector tanggal/tipe/frekuensi/sumber
  // atau tanpa parameter (observasi terbaru). Panel daftar sumber memakai mode terbaru.
  _params?: { period?: string; observation_date?: string },
): Promise<SourceTrace> {
  const res = await fetch(`${API_BASE}/indicators/${encodeURIComponent(code)}/source-trace/`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as SourceTrace;
}

// ---------------------------------------------------------------------------
// Fitur 10 – Kelola Sumber Data (Admin, session auth, khusus staf)
// ---------------------------------------------------------------------------

export interface AdminSession {
  authenticated: boolean;
  username: string | null;
  isStaff: boolean;
  canReviewCandidates?: boolean;
}

export interface AcquisitionMethod {
  value: string;
  label: string;
  formats: string[];
  handler: string;
  endpointRequired: boolean;
  description: string;
}

export type ResyncStatus = "queued" | "running" | "success" | "failed" | "cancelled" | "unknown";

export interface AdminResyncJob {
  id: string;
  sourceId: string;
  status: ResyncStatus;
  requestedAt: string;
  finishedAt: string | null;
  runId: string | null;
  message: string | null;
}

export interface AdminResyncAccepted { id: string; status: "queued" | "running" }

export interface AdminSourceEntry {
  sourceId: string;
  sourceName: string;
  institution: string;
  primaryUrl: string;
  description: string;
  acquisitionMethod: string;
  acquisitionMethodLabel: string;
  endpointUrl: string;
  dataFormat: string;
  frequency: string;
  updateSchedule: string;
  status: string;
  lastFetch: { retrievedAt: string | null; documentName: string | null; parseStatus: string | null };
}

export interface SourceCreatePayload {
  sourceId: string;
  sourceName: string;
  institution: string;
  primaryUrl: string;
  description?: string;
  acquisitionMethod: string;
  endpointUrl?: string;
  dataFormat: string;
  frequency: string;
  updateSchedule?: string;
  status?: string;
}

async function adminFetch(path: string, init?: RequestInit) {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const bootstrap = await fetch(`${API_BASE}/auth/csrf/`, { credentials: "include", signal: init?.signal });
    if (!bootstrap.ok) throw new Error("Token keamanan tidak tersedia.");
    const body = await bootstrap.json();
    if (typeof body?.csrfToken !== "string" || !body.csrfToken) throw new Error("Token keamanan tidak tersedia.");
    headers.set("X-CSRFToken", body.csrfToken);
  }
  if (init?.signal?.aborted) throw new DOMException("The operation was aborted", "AbortError");
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include", ...init, headers });
  return res;
}

export interface ReviewCandidate {
  id: number; fingerprint: string; indicator: string | null; indicatorName: string | null;
  sourceId: string; sourceName: string | null; sourceUrl: string | null; period: string | null;
  observationDate: string | null; publicationDate: string | null; frequency: string | null;
  dataType: string | null; value: string | null; unit: string | null; rawFileId: number | null;
  previousValue: string | null; previousUnit: string | null; previousPeriod: string | null;
  rawEvidence?: { documentName: string | null; periodLabel: string | null; retrievedAt: string | null; checksumSha256: string | null } | null;
  status: string; createdAt: string; reviewedAt: string | null; reviewedBy: string | null; reviewNotes: string;
  reviewHistory?: { decision: string; notes: string; reviewedAt: string; reviewedBy: string | null; fingerprint: string }[];
}

export type AnalysisDecision = 'publish' | 'needs_revision' | 'reject';

export interface CandidatePage {
  items: ReviewCandidate[]; page: number; pageSize: number; total: number; hasNext: boolean;
}

export class CandidateReviewError extends Error {
  readonly kind: 'conflict' | 'unauthenticated' | 'forbidden';
  constructor(kind: 'conflict' | 'unauthenticated' | 'forbidden', message: string) {
    super(message);
    this.kind = kind;
  }
}

async function withCandidateDeadline<T>(run: (signal: AbortSignal) => Promise<T>, timeoutMs = 15_000): Promise<T> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  const timedOut = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error('Waktu tunggu kandidat habis.'));
    }, timeoutMs);
  });
  try {
    return await Promise.race([run(controller.signal), timedOut]);
  } finally {
    clearTimeout(timer!);
  }
}

export async function fetchReviewCandidates(sourceId: string, page: number, status: 'pending' | 'published' | 'needs_revision' | 'rejected' = 'pending', options?: { timeoutMs?: number }): Promise<CandidatePage> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/candidates/?page=${page}&status=${status}`, { signal });
    if (!res.ok) {
      if (res.status === 401) throw new CandidateReviewError('unauthenticated', 'Sesi Admin tidak tersedia. Masuk kembali sebelum review.');
      if (res.status === 403) throw new CandidateReviewError('forbidden', 'Akses ditolak: periksa izin review kandidat dengan pengelola.');
      throw new Error('Daftar kandidat tidak dapat dimuat.');
    }
    const body = await res.json() as CandidatePage;
    if (!Array.isArray(body.items) || body.page !== page || !Number.isInteger(body.total)) throw new Error('Respons kandidat tidak valid.');
    return body;
  }, options?.timeoutMs);
}

export async function fetchAdminAnalysisResults(page: number, status: 'all' | 'pending' | 'published' | 'needs_revision' | 'rejected', options?: { timeoutMs?: number }): Promise<CandidatePage> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`/admin/analysis-results/?page=${page}&status=${status}`, { signal });
    if (!res.ok) {
      if (res.status === 401) throw new CandidateReviewError('unauthenticated', 'Sesi Admin tidak tersedia. Masuk kembali untuk meninjau hasil analisis.');
      if (res.status === 403) throw new CandidateReviewError('forbidden', 'Akses ditolak: periksa izin review hasil analisis dengan pengelola.');
      throw new Error('Daftar hasil analisis tidak dapat dimuat.');
    }
    const body = await res.json() as CandidatePage;
    if (!Array.isArray(body.items) || body.page !== page || !Number.isInteger(body.total)) throw new Error('Respons hasil analisis tidak valid.');
    return body;
  }, options?.timeoutMs);
}

export async function submitAdminAnalysisDecision(candidate: ReviewCandidate, decision: AnalysisDecision, notes: string, options?: { timeoutMs?: number }): Promise<void> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`/admin/analysis-results/${candidate.id}/decision/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, fingerprint: candidate.fingerprint, notes }),
      signal,
    });
    const body = await res.json().catch(() => ({})) as { id?: number; status?: string; error?: string };
    if (res.status === 409) throw new CandidateReviewError('conflict', body.error ?? 'Versi berubah atau telah diputuskan. Muat ulang.');
    if (res.status === 401) throw new CandidateReviewError('unauthenticated', 'Sesi Admin tidak tersedia. Masuk kembali untuk menetapkan keputusan.');
    if (res.status === 403) throw new CandidateReviewError('forbidden', 'Keputusan ditolak: periksa izin Admin dan token keamanan.');
    const expectedStatus = decision === 'publish' ? 'published' : decision === 'needs_revision' ? 'needs_revision' : 'rejected';
    if (!res.ok) throw new Error(body.error ?? 'Keputusan publikasi tidak dapat disimpan.');
    if (body.id !== candidate.id || body.status !== expectedStatus) {
      throw new Error('Respons keputusan tidak sesuai. Muat ulang hasil untuk memeriksa status terbaru.');
    }
  }, options?.timeoutMs);
}

export async function submitCandidateReview(sourceId: string, candidate: ReviewCandidate, decision: 'publish' | 'reject', notes: string, options?: { timeoutMs?: number }): Promise<void> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/candidates/${candidate.id}/review/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, fingerprint: candidate.fingerprint, notes }),
      signal,
    });
    if (res.status === 409) throw new CandidateReviewError('conflict', 'Kandidat berubah atau sudah direview. Periksa status terbaru.');
    if (res.status === 401) throw new CandidateReviewError('unauthenticated', 'Sesi Admin tidak tersedia. Masuk kembali sebelum review.');
    if (res.status === 403) throw new CandidateReviewError('forbidden', 'Review ditolak: periksa izin Admin dan token keamanan.');
    if (!res.ok) throw new Error('Review belum dapat dipastikan. Periksa status kandidat sebelum mencoba lagi.');
    const result = await res.json() as { id?: number; status?: string };
    if (result.id !== candidate.id || result.status !== (decision === 'publish' ? 'published' : 'rejected')) {
      throw new Error('Hasil review belum dapat dipastikan. Periksa status kandidat sebelum mencoba lagi.');
    }
  }, options?.timeoutMs);
}

export async function fetchReviewCandidate(sourceId: string, id: number, options?: { timeoutMs?: number }): Promise<ReviewCandidate> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/candidates/${id}/`, { signal });
    if (!res.ok) throw new Error('Status kandidat tidak dapat dipastikan.');
    const body = await res.json() as { candidate?: ReviewCandidate };
    if (!body.candidate || body.candidate.id !== id || body.candidate.sourceId !== sourceId) throw new Error('Status kandidat tidak valid.');
    return body.candidate;
  }, options?.timeoutMs);
}

export interface BulkPreview {
  id: string; status: 'preview'; expiresAt: string; total: number; eligible: number; excluded: number;
  items: Array<ReviewCandidate & { eligible: boolean; exclusionReason: string | null }>;
}
export interface BulkReviewResult {
  id: string; status: 'running' | 'completed' | 'unknown';
  resolvedAt?: string | null; resolvedBy?: string | null; resolutionReason?: string | null;
  items: Array<{ id: number; status: 'excluded' | 'pending' | 'published' | 'skipped' | 'unknown'; reason: string | null }>;
  counts: { total: number; eligible: number; excluded: number; published: number; skipped: number; pending: number; unknown: number };
}
const bulkPath = (sourceId: string) => `/admin/sources/${encodeURIComponent(sourceId)}/candidates/`;
function bulkError(status: number): Error {
  if (status === 401) return new CandidateReviewError('unauthenticated', 'Sesi Admin tidak tersedia. Masuk kembali sebelum review.');
  if (status === 403) return new CandidateReviewError('forbidden', 'Izin review atau token keamanan ditolak.');
  if (status === 409) return new CandidateReviewError('conflict', 'Ada konflik pratinjau atau operasi sumber. Periksa status operasi sebelum keputusan baru.');
  return new Error('Operasi kandidat belum dapat dipastikan. Periksa statusnya sebelum mengambil keputusan baru.');
}
const validBulkId = (id: unknown): id is string => typeof id === 'string' && /^[0-9a-f-]{36}$/i.test(id);
function validBulkResult(body: BulkReviewResult, id: string): boolean {
  const counts = body?.counts;
  return body?.id === id && ['running', 'completed', 'unknown'].includes(body.status) &&
    Array.isArray(body.items) && counts != null &&
    (['total', 'eligible', 'excluded', 'published', 'skipped', 'pending', 'unknown'] as const).every(key => Number.isSafeInteger(counts[key]) && counts[key] >= 0) &&
    body.items.every(item => Number.isSafeInteger(item.id) && item.id > 0);
}

export async function createBulkPreview(sourceId: string): Promise<BulkPreview> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`${bulkPath(sourceId)}bulk-preview/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}', signal,
    });
    if (!res.ok) throw bulkError(res.status);
    const body = await res.json() as BulkPreview;
    if (!validBulkId(body?.id) || body.status !== 'preview' || !Array.isArray(body.items) ||
        !Number.isSafeInteger(body.total) || body.total !== body.items.length ||
        !Number.isSafeInteger(body.eligible) || !Number.isSafeInteger(body.excluded) ||
        body.total !== body.eligible + body.excluded ||
        body.items.some(item => item.sourceId !== sourceId || !Number.isSafeInteger(item.id) ||
          typeof item.fingerprint !== 'string' || typeof item.eligible !== 'boolean')) {
      throw new Error('Pratinjau kandidat tidak valid.');
    }
    return body;
  });
}

export async function confirmBulkReview(sourceId: string, id: string): Promise<BulkReviewResult> {
  if (!validBulkId(id)) throw new Error('Identitas operasi tidak valid.');
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`${bulkPath(sourceId)}bulk-review/${id}/confirm/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmed: true }), signal,
    });
    if (!res.ok) throw bulkError(res.status);
    const body = await res.json() as BulkReviewResult;
    if (!validBulkResult(body, id)) throw new Error('Hasil operasi belum dapat dipastikan.');
    return body;
  });
}

export async function reconcileBulkReview(sourceId: string, id: string, reason: string): Promise<BulkReviewResult> {
  if (!validBulkId(id) || !reason.trim() || reason.trim().length > 500) throw new Error('Identitas atau alasan pemeriksaan tidak valid.');
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`${bulkPath(sourceId)}bulk-review/${id}/reconcile/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged: true, reason: reason.trim() }), signal,
    });
    if (!res.ok) throw bulkError(res.status);
    const body = await res.json() as BulkReviewResult;
    if (!validBulkResult(body, id) || !body.resolvedAt || !body.resolvedBy || !body.resolutionReason) {
      throw new Error('Hasil pemeriksaan belum dapat dipastikan. Periksa status operasi.');
    }
    return body;
  });
}

export async function fetchBulkReview(sourceId: string, id: string): Promise<BulkReviewResult> {
  if (!validBulkId(id)) throw new Error('Identitas operasi tidak valid.');
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`${bulkPath(sourceId)}bulk-review/${id}/`, { signal });
    if (!res.ok) throw bulkError(res.status);
    const body = await res.json() as BulkReviewResult;
    if (!validBulkResult(body, id)) throw new Error('Status operasi tidak valid.');
    return body;
  });
}

export async function fetchActiveBulkReview(sourceId: string): Promise<BulkReviewResult | null> {
  return withCandidateDeadline(async signal => {
    const res = await adminFetch(`${bulkPath(sourceId)}bulk-review/active/`, { signal });
    if (!res.ok) throw bulkError(res.status);
    const body = await res.json() as { batch?: BulkReviewResult | null };
    if (body?.batch == null) return null;
    if (!validBulkId(body.batch.id) || !validBulkResult(body.batch, body.batch.id)) throw new Error('Status operasi tidak valid.');
    return body.batch;
  });
}

export async function fetchAdminSession(): Promise<AdminSession> {
  const res = await adminFetch("/admin/session/");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as AdminSession;
}

export async function adminLogin(username: string, password: string): Promise<void> {
  const res = await adminFetch("/admin/login/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  }
}

export async function adminLogout(): Promise<void> {
  await createAuthClient("").logout();
}

export async function fetchAcquisitionMethods(): Promise<{ methods: AcquisitionMethod[]; frequencies: string[] }> {
  const res = await adminFetch("/admin/sources/acquisition-methods/");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as { methods: AcquisitionMethod[]; frequencies: string[] };
}

export async function fetchAdminSources(): Promise<AdminSourceEntry[]> {
  const res = await adminFetch("/admin/sources/");
  if (!res.ok) {
    if (res.status === 401) throw new Error("Sesi admin diperlukan. Silakan login.");
    if (res.status === 403) throw new Error("Akun tidak memiliki hak pengelolaan sumber.");
    throw new Error(`HTTP ${res.status}`);
  }
  const body = await res.json();
  if (!Array.isArray(body?.sources)) throw new Error("Respons daftar sumber tidak valid.");
  return body.sources as AdminSourceEntry[];
}

export async function createAdminSource(payload: SourceCreatePayload): Promise<AdminSourceEntry> {
  const res = await adminFetch("/admin/sources/create/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (res.status === 201) return (body as { source: AdminSourceEntry }).source;
  throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
}

export interface AdminSourceDetail extends AdminSourceEntry {
  revisionCount: number;
  revisionVersion: number;
}

export interface AdminRevision {
  version: number;
  action: string;
  before: Record<string, string>;
  after: Record<string, string>;
  changedFields: string[];
  updatedBy: string | null;
  createdAt: string | null;
}

export interface SourceUpdatePayload {
  expectedRevision: number;
  sourceName?: string;
  institution?: string;
  primaryUrl?: string;
  description?: string;
  acquisitionMethod?: string;
  endpointUrl?: string;
  dataFormat?: string;
  frequency?: string;
  updateSchedule?: string;
  status?: string;
}

export interface SourceUpdateResult {
  source: AdminSourceEntry;
  revision?: AdminRevision;
  changedFields?: string[];
}

export async function fetchAdminSourceDetail(sourceId: string): Promise<AdminSourceDetail> {
  const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/`);
  if (!res.ok) {
    if (res.status === 404) throw new Error(`Sumber '${sourceId}' tidak tersedia.`);
    throw new Error(`HTTP ${res.status}`);
  }
  return (await res.json()) as AdminSourceDetail;
}

export async function loadAdminSyncHistory(
  query: SyncHistoryQuery,
  options: { signal: AbortSignal; timeoutMs?: number },
): Promise<SyncHistoryResult> {
  const params = new URLSearchParams({page: String(query.page), pageSize: String(query.pageSize)});
  if (query.sourceId) params.set("sourceId", query.sourceId);
  if (query.status) params.set("status", query.status);

  const timeoutController = new AbortController();
  const timeout = setTimeout(() => timeoutController.abort(), options.timeoutMs ?? 15_000);
  const signal = AbortSignal.any([options.signal, timeoutController.signal]);
  let onAbort = () => {};
  const cancelled = new Promise<never>((_, reject) => {
    onAbort = () => reject(new DOMException("The operation was aborted", "AbortError"));
    if (signal.aborted) onAbort();
    else signal.addEventListener("abort", onAbort, { once: true });
  });
  try {
    return await Promise.race([cancelled, (async () => {
      if (signal.aborted) throw new DOMException("The operation was aborted", "AbortError");
      const response = await adminFetch(`/admin/sync-history/?${params}`, { signal });
      if (!response.ok) {
        if (response.status === 401) throw new Error("Sesi admin telah berakhir atau diperlukan. Silakan masuk kembali.");
        if (response.status === 403) throw new Error("Anda tidak berwenang melihat riwayat sinkronisasi.");
        throw new Error("Gagal memuat riwayat sinkronisasi.");
      }
      return await response.json() as SyncHistoryResult;
    })()]);
  } catch (error) {
    if (options.signal.aborted) throw new DOMException("The operation was aborted", "AbortError");
    if (timeoutController.signal.aborted) throw new Error("Waktu tunggu pemuatan riwayat sinkronisasi habis. Silakan coba lagi.");
    if (error instanceof Error && error.message.startsWith("Sesi admin")) throw error;
    if (error instanceof Error && error.message.startsWith("Anda tidak berwenang")) throw error;
    if (error instanceof Error && error.message.startsWith("Gagal memuat riwayat")) throw error;
    throw new Error("Koneksi ke layanan riwayat sinkronisasi bermasalah. Silakan coba lagi.");
  } finally {
    clearTimeout(timeout);
    signal.removeEventListener("abort", onAbort);
  }
}

export async function requestAdminBpsResync(sourceId: string, requestId: string): Promise<AdminResyncAccepted> {
  const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/resync/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requestId }),
  });
  if (res.status === 401) throw new Error("Sesi admin berakhir. Periksa riwayat sebelum mengambil tindakan lain.");
  if (!res.ok) throw new Error(`Permintaan sinkronisasi belum dapat dipastikan (HTTP ${res.status}). Periksa riwayat sebelum mengulang.`);
  const body = await res.json() as AdminResyncAccepted;
  if (!body?.id || !["queued", "running"].includes(body.status)) throw new Error("Respons permintaan tidak dapat dipastikan. Periksa riwayat sebelum mengulang.");
  return body;
}

export async function fetchAdminResyncJob(id: string): Promise<AdminResyncJob> {
  const res = await adminFetch(`/admin/resync-jobs/${encodeURIComponent(id)}/`);
  if (res.status === 401) throw new Error("Sesi admin telah berakhir. Silakan masuk kembali.");
  if (!res.ok) throw new Error(`Status sinkronisasi tidak dapat dimuat (HTTP ${res.status}).`);
  return await res.json() as AdminResyncJob;
}

export async function fetchActiveAdminResync(sourceId: string): Promise<AdminResyncJob | null> {
  const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/resync-active/`);
  if (!res.ok) throw new Error("Status antrean tidak dapat diperiksa. Muat ulang sebelum melanjutkan.");
  const body = await res.json() as { job: AdminResyncJob | null };
  if (!body || !(body.job === null || (typeof body.job?.id === "string" &&
      ["queued", "running"].includes(body.job.status)))) {
    throw new Error("Status antrean tidak dapat dipastikan. Muat ulang sebelum melanjutkan.");
  }
  return body.job;
}

export async function reconcileAdminResyncJob(id: string, payload: { confirmed: true; reason: string }): Promise<AdminResyncJob> {
  if (payload.confirmed !== true || !payload.reason.trim()) throw new Error("Konfirmasi pemeriksaan dan alasan wajib diisi.");
  const res = await adminFetch(`/admin/resync-jobs/${encodeURIComponent(id)}/reconcile/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmed: true, reason: payload.reason.trim() }),
  });
  if (!res.ok) throw new Error(`Rekonsiliasi tidak dapat dipastikan (HTTP ${res.status}). Muat ulang status sebelum mencoba lagi.`);
  return await res.json() as AdminResyncJob;
}

export async function fetchAdminSourceRevisions(sourceId: string): Promise<AdminRevision[]> {
  const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/revisions/`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  return (body?.revisions ?? []) as AdminRevision[];
}

export async function updateAdminSource(
  sourceId: string,
  payload: SourceUpdatePayload,
): Promise<SourceUpdateResult> {
  const res = await adminFetch(`/admin/sources/${encodeURIComponent(sourceId)}/update/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (res.ok) return body as SourceUpdateResult;
  throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
}

// ---------------------------------------------------------------------------
// Fitur 8 – Umpan Balik
// ---------------------------------------------------------------------------

export interface FeedbackCategory {
  value: string;
  label: string;
}

export interface FeedbackPayload {
  category: string;
  description: string;
  sender_name?: string;
  sender_email?: string;
  related_indicator_code?: string;
  related_period?: string;
}

export interface FeedbackResult {
  id: number | null;
  status: "idle" | "loading" | "success" | "error";
  message: string;
}

export function useFeedbackCategories() {
  const [categories, setCategories] = useState<FeedbackCategory[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/feedback/categories/`)
      .then((r) => r.json())
      .then((body) => { if (body?.categories) setCategories(body.categories); })
      .catch(() => {});
  }, []);

  return categories;
}

export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackResult> {
  try {
    const res = await fetch(`${API_BASE}/feedback/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    if (res.status === 201) {
      return { id: body.id, status: "success", message: body.message };
    }
    const msg =
      body?.error ??
      Object.values(body ?? {}).flat().join(" ") ??
      "Terjadi kesalahan saat mengirim umpan balik.";
    return { id: null, status: "error", message: String(msg) };
  } catch {
    return { id: null, status: "error", message: "Tidak dapat menghubungi server." };
  }
}

// ---------------------------------------------------------------------------
// Fitur 15: Daftar Umpan Balik Admin
// ---------------------------------------------------------------------------

export interface AdminFeedbackItem {
  id: number;
  category: string;
  category_label: string;
  description: string;
  sender_name: string;
  sender_email: string;
  related_indicator_code: string;
  related_period: string;
  status: string;
  status_label: string;
  admin_notes: string;
  ip_address: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminFeedbackListResponse {
  count: number;
  feedbacks: AdminFeedbackItem[];
  available_statuses: { value: string; label: string }[];
}

export interface AdminFeedbackDetail extends AdminFeedbackItem {
  csrfToken: string;
  related_indicator: {
    code: string;
    name: string;
    category: string;
    unit: string;
  } | null;
  audit_logs: FeedbackAuditLogEntry[];
}

export interface FeedbackAuditLogEntry {
  id: number;
  old_status: string;
  old_status_label: string;
  new_status: string;
  new_status_label: string;
  notes: string;
  changed_by: string;
  changed_at: string | null;
}

export async function fetchAdminFeedbacks(params?: {
  search?: string;
  status?: string;
  category?: string;
}): Promise<AdminFeedbackListResponse> {
  const query = new URLSearchParams();
  if (params?.search?.trim()) query.set("search", params.search.trim());
  if (params?.status && params.status !== "all") query.set("status", params.status);
  if (params?.category && params.category !== "all") query.set("category", params.category);

  const qs = query.toString() ? `?${query.toString()}` : "";
  const res = await adminFetch(`/admin/feedback/${qs}`);
  if (!res.ok) {
    if (res.status === 401) throw new Error("Sesi admin diperlukan. Silakan login.");
    if (res.status === 403) throw new Error("Hak akses admin diperlukan.");
    throw new Error(`HTTP ${res.status}`);
  }
  return (await res.json()) as AdminFeedbackListResponse;
}

export async function fetchAdminFeedbackDetail(id: number): Promise<AdminFeedbackDetail> {
  const res = await adminFetch(`/admin/feedback/${id}/`);
  if (!res.ok) {
    if (res.status === 404) throw new Error("Umpan balik tidak ditemukan.");
    if (res.status === 401) throw new Error("Sesi admin diperlukan. Silakan login.");
    if (res.status === 403) throw new Error("Hak akses admin diperlukan.");
    throw new Error(`HTTP ${res.status}`);
  }
  const body = await res.json();
  return { ...body.feedback, csrfToken: body.csrfToken } as AdminFeedbackDetail;
}

export async function updateAdminFeedbackStatus(
  id: number,
  payload: { status: string; notes: string; csrfToken: string },
): Promise<AdminFeedbackDetail> {
  const res = await adminFetch(`/admin/feedback/${id}/status/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": payload.csrfToken,
    },
    body: JSON.stringify({ status: payload.status, notes: payload.notes }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body?.error ?? `Gagal memperbarui status (HTTP ${res.status})`);
  }
  return { ...body.feedback, csrfToken: body.csrfToken } as AdminFeedbackDetail;
}

// ---------------------------------------------------------------------------
// Feature 19 – Dashboard Monitoring Admin
// ---------------------------------------------------------------------------

export interface MonitoringSummary {
  totalSources: number;
  activeSources: number;
  inactiveSources: number;
  syncSuccess: number;
  syncFailed: number;
  syncRunning: number;
  quality: { label: string; validated: number; total: number };
  lastSyncAt: string | null;
  lastUpdateAt: string | null;
}

export interface MonitoringSource {
  sourceId: string;
  sourceName: string;
  institution: string;
  status: string;
  active: boolean;
  lastSyncStatus: string | null;
  lastSyncAt: string | null;
  lastSyncMessage: string;
  lastPeriod: string | null;
  lastObservationDate: string | null;
  observationCount: number;
  updateSchedule: string;
}

export async function fetchMonitoringSummary(): Promise<MonitoringSummary> {
  const res = await adminFetch("/admin/monitoring/summary/");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as MonitoringSummary;
}

export async function fetchMonitoringSources(): Promise<MonitoringSource[]> {
  const res = await adminFetch("/admin/monitoring/sources/");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  return (body?.sources ?? []) as MonitoringSource[];
}

export async function fetchMonitoringHistory(params?: { page?: number; pageSize?: number; status?: string; sourceId?: string }): Promise<{ items: { id: string; sourceId: string | null; status: string; startedAt: string | null; message: string }[]; total: number }> {
  const q = new URLSearchParams();
  q.set("page", String(params?.page ?? 1));
  q.set("pageSize", String(params?.pageSize ?? 20));
  if (params?.status) q.set("status", params.status);
  if (params?.sourceId) q.set("sourceId", params.sourceId);
  const res = await adminFetch(`/admin/monitoring/history/?${q}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as { items: { id: string; sourceId: string | null; status: string; startedAt: string | null; message: string }[]; total: number };
}

// ---------------------------------------------------------------------------
// Feature 24 – Konfigurasi Threshold Diagnostik
// ---------------------------------------------------------------------------

export interface ThresholdEntry {
  indicatorCode: string;
  indicatorName: string;
  category: string;
  paramKey: string;
  label: string;
  value: string;
  unit: string;
  minAllowed: string;
  maxAllowed: string;
  description: string;
  status: string;
  configured: boolean;
  version: number;
  updatedAt: string | null;
  updatedBy: string | null;
  latestValue: string | null;
}

export interface ThresholdEvaluation {
  threshold: string;
  unit: string;
  observed: string | null;
  exceeded: boolean;
  status: string;
  impact: string;
}

export interface ThresholdHistoryItem {
  oldValue: Record<string, string>;
  newValue: Record<string, string>;
  actor: string | null;
  reason: string;
  createdAt: string | null;
}

export async function fetchThresholds(): Promise<ThresholdEntry[]> {
  const res = await adminFetch("/admin/thresholds/");
  if (!res.ok) {
    if (res.status === 401) throw new Error("Sesi admin diperlukan. Silakan login.");
    if (res.status === 403) throw new Error("Hak akses admin diperlukan.");
    throw new Error(`HTTP ${res.status}`);
  }
  const body = await res.json();
  return (body?.thresholds ?? []) as ThresholdEntry[];
}

export async function fetchThresholdDetail(
  code: string,
  param: string,
): Promise<{ threshold: ThresholdEntry; evaluation: ThresholdEvaluation; latestPeriod: string | null; latestUnit: string | null }> {
  const res = await adminFetch(`/admin/thresholds/${encodeURIComponent(code)}/${encodeURIComponent(param)}/`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  return (await res.json()) as {
    threshold: ThresholdEntry;
    evaluation: ThresholdEvaluation;
    latestPeriod: string | null;
    latestUnit: string | null;
  };
}

export async function updateThreshold(
  code: string,
  param: string,
  payload: { value: string; status?: string; reason?: string },
): Promise<{ threshold: ThresholdEntry; evaluation: ThresholdEvaluation; message: string }> {
  const res = await adminFetch(`/admin/thresholds/${encodeURIComponent(code)}/${encodeURIComponent(param)}/update/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  return body as { threshold: ThresholdEntry; evaluation: ThresholdEvaluation; message: string };
}

export async function fetchThresholdHistory(code: string, param: string): Promise<ThresholdHistoryItem[]> {
  const res = await adminFetch(`/admin/thresholds/${encodeURIComponent(code)}/${encodeURIComponent(param)}/history/`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  return (body?.history ?? []) as ThresholdHistoryItem[];
}

/** Validasi sisi klien sebelum request. Kembalikan pesan error atau null bila valid. */
export function validateThresholdInput(value: string, minAllowed: string, maxAllowed: string, unit: string, expectedUnit: string): string | null {
  if (!value.trim()) return "Nilai threshold wajib diisi.";
  if (!/^-?\d+(?:\.\d+)?$/.test(value.trim())) return "Nilai threshold harus berupa angka.";
  if (unit !== expectedUnit) return `Satuan harus '${expectedUnit}' sesuai definisi parameter.`;
  const v = Number(value);
  if (Number.isNaN(v)) return "Nilai threshold harus berupa angka.";
  if (v < Number(minAllowed) || v > Number(maxAllowed)) {
    return `Nilai threshold berada di luar rentang yang diperbolehkan (${minAllowed}-${maxAllowed} ${expectedUnit}). Periksa kembali nilai dan satuan yang digunakan.`;
  }
  return null;
}
