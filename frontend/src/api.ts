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
