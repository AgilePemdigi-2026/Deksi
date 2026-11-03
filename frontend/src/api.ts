import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api";

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
  params?: { period?: string; observation_date?: string },
): Promise<SourceTrace> {
  const query = new URLSearchParams();
  if (params?.period) query.set("period", params.period);
  if (params?.observation_date) query.set("observation_date", params.observation_date);
  const suffix = query.toString() ? `?${query}` : "";
  const res = await fetch(`${API_BASE}/indicators/${encodeURIComponent(code)}/source-trace/${suffix}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as SourceTrace;
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
