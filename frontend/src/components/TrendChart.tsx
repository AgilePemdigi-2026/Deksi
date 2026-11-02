import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { IndicatorId } from "../data/indicators";
import { indicatorTrends } from "../data/indicators";
import { useTrend, type TrendPoint } from "../api";

const GRANULARITIES = ["Kuartalan", "Tahunan"] as const;
type Granularity = (typeof GRANULARITIES)[number];

const TIMEFRAMES = ["3 Tahun", "5 Tahun", "10 Tahun", "Semua"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

const YEARS: Record<Exclude<Timeframe, "Semua">, number> = {
  "3 Tahun": 3,
  "5 Tahun": 5,
  "10 Tahun": 10,
};

const numberFormat = new Intl.NumberFormat("id-ID", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

interface ChartPoint extends Record<string, unknown> {
  label: string;
  value: number;
}

const TrendTooltip = ({
  active,
  payload,
  suffix,
}: {
  active?: boolean;
  payload?: { payload: ChartPoint }[];
  suffix: string;
}) => {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="trend-tooltip">
      <p className="trend-tooltip-label">
        {point.label} ({suffix})
      </p>
      <p className="trend-tooltip-value">{numberFormat.format(point.value)}</p>
    </div>
  );
};

const aggregateYearly = (points: ChartPoint[]): ChartPoint[] => {
  const buckets = new Map<string, number[]>();
  points.forEach((p) => {
    const year = p.label.slice(-4);
    buckets.set(year, [...(buckets.get(year) ?? []), p.value]);
  });
  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([year, values]) => ({
      label: year,
      value: Number(
        (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2),
      ),
    }));
};

const pointYear = (point: TrendPoint): number => {
  if (typeof point.year === "number") return point.year;
  const match = (point.label ?? "").match(/\d{4}\s*$/);
  return match ? Number(match[0]) : 0;
};

export function TrendChart() {
  const [activeId, setActiveId] = useState<IndicatorId>("pdb");
  const [granularity, setGranularity] = useState<Granularity>("Kuartalan");
  const [timeframe, setTimeframe] = useState<Timeframe>("5 Tahun");

  const trendMeta = indicatorTrends[activeId];
  const { trend, loading, error } = useTrend(activeId);

  const unit = trend?.unit ?? trendMeta.unitSuffix;
  const supported = trend?.granularities?.length
    ? trend.granularities
    : ([] as string[]);

  const chartData = useMemo<ChartPoint[]>(() => {
    const points = trend?.points ?? [];
    if (!points.length) return [];
    let slice = points.map((p) => ({ label: p.label, value: p.value, year: pointYear(p) }));
    if (timeframe !== "Semua" && supported.includes(granularity)) {
      const latest = Math.max(...slice.map((p) => p.year), 0);
      const cutoff = latest - YEARS[timeframe as Exclude<Timeframe, "Semua">];
      if (latest > 0) slice = slice.filter((p) => p.year >= cutoff);
    }
    if (granularity === "Tahunan") return aggregateYearly(slice);
    return slice.map(({ label, value }) => ({ label, value }));
  }, [trend, granularity, timeframe, supported]);

  const average = useMemo(
    () =>
      chartData.length
        ? Number((chartData.reduce((a, b) => a + b.value, 0) / chartData.length).toFixed(2))
        : 0,
    [chartData],
  );

  const yDomain: [number | string, number | string] = ["auto", "auto"];

  return (
    <section className="trend" id="analisis">
      <div className="trend-card">
        <div className="trend-head">
          <div>
            <h2 className="trend-title">⚡ Tren Ekonomi Indonesia</h2>
            <p className="trend-sub">{trendMeta.description}</p>
          </div>
        </div>

        <div className="trend-tabs" role="tablist" aria-label="Pilih indikator">
          {Object.values(indicatorTrends).map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={item.id === activeId}
              className={item.id === activeId ? "tab tab-active" : "tab"}
              onClick={() => setActiveId(item.id)}
            >
              {item.name}
            </button>
          ))}
        </div>

        <div className="trend-controls">
          <div className="trend-tabs compact" role="tablist" aria-label="Pilih granularitas">
            {GRANULARITIES.map((g) => (
              <button
                key={g}
                type="button"
                role="tab"
                aria-selected={g === granularity}
                className={g === granularity ? "tab tab-active" : "tab"}
                onClick={() => setGranularity(g)}
              >
                {g}
              </button>
            ))}
          </div>
          <div className="trend-tabs compact" role="tablist" aria-label="Pilih rentang waktu">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                type="button"
                role="tab"
                aria-selected={tf === timeframe}
                className={tf === timeframe ? "tab tab-active" : "tab"}
                onClick={() => setTimeframe(tf)}
              >
                {tf}
              </button>
            ))}
          </div>
          <span className="trend-unit">Unit: {unit}</span>
        </div>

        <div className="trend-legend">
          <span className="legend-item">
            <span className="legend-line" />
            {trendMeta.name} ({unit})
          </span>
          <span className="legend-item">
            <span className="legend-dash" />
            Rata-rata Rentang ({numberFormat.format(average)})
          </span>
        </div>

        <div className="trend-chart">
          {loading && <p className="trend-loading">Memuat data historis…</p>}
          {!loading && error && <p className="trend-error">{error}</p>}
          {!loading && !error && chartData.length === 0 && (
            <p className="trend-error">Data historis belum tersedia untuk indikator ini.</p>
          )}
          {!loading && !error && chartData.length > 0 && (
            <ResponsiveContainer width="100%" height={340}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={trendMeta.color} stopOpacity={0.16} />
                    <stop offset="100%" stopColor={trendMeta.color} stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "#e2e8f0" }}
                  interval="preserveStartEnd"
                  minTickGap={28}
                />
                <YAxis
                  domain={yDomain}
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => numberFormat.format(v)}
                  allowDataOverflow={false}
                />
                <ReferenceLine
                  y={average}
                  stroke="#94a3b8"
                  strokeDasharray="6 4"
                  strokeWidth={1.2}
                />
                <Tooltip
                  content={<TrendTooltip suffix={unit} />}
                  cursor={{ stroke: "#64748b", strokeDasharray: "4 4" }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="none"
                  fill="url(#trendFill)"
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={trendMeta.color}
                  strokeWidth={2.4}
                  dot={false}
                  isAnimationActive={false}
                  activeDot={{ r: 5, fill: trendMeta.color, stroke: "#fff", strokeWidth: 2 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="trend-footnote">
          <span>
            {trendMeta.footnote}
            {trend?.note ? ` ${trend.note}` : ""}
            {trend && !trend.hasCurrentYearData && trend.dataAvailableUntil
              ? ` Data terbaru tersedia sampai ${trend.dataAvailableUntil}.`
              : ""}
          </span>
          <a
            className="trend-footnote-link"
            href="https://www.bps.go.id/id/statistics-table"
            target="_blank"
            rel="noopener noreferrer"
          >
            Buka Sumber Data Resmi ↗
          </a>
        </div>
      </div>
    </section>
  );
}
