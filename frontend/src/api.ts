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

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
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

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

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
}

export interface AcquisitionMethod {
  value: string;
  label: string;
  formats: string[];
  handler: string;
  endpointRequired: boolean;
  description: string;
}

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
    const bootstrap = await fetch(`${API_BASE}/auth/csrf/`, { credentials: "include" });
    if (!bootstrap.ok) throw new Error("Token keamanan tidak tersedia.");
    const body = await bootstrap.json();
    if (typeof body?.csrfToken !== "string" || !body.csrfToken) throw new Error("Token keamanan tidak tersedia.");
    headers.set("X-CSRFToken", body.csrfToken);
  }
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include", ...init, headers });
  return res;
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
  return (body?.sources ?? []) as AdminSourceEntry[];
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
