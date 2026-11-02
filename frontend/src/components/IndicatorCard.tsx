import type { IndicatorMeta } from "../data/indicators";

const directionGlyph = (meta: IndicatorMeta) => {
  if (meta.deltaDirection === "up") return "▲";
  if (meta.deltaDirection === "down") return "▼";
  return "●";
};

const Sparkline = ({ points, color }: { points: number[]; color: string }) => {
  const width = 220;
  const height = 46;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const step = width / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = i * step;
    const y = height - 6 - ((p - min) / span) * (height - 12);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-hidden="true"
    >
      <polyline
        points={coords.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={coords[coords.length - 1].split(",")[0]}
        cy={coords[coords.length - 1].split(",")[1]}
        r="3"
        fill={color}
      />
    </svg>
  );
};

export function IndicatorCard({ meta }: { meta: IndicatorMeta }) {
  return (
    <article className="indicator-card">
      <div className="indicator-head">
        <div>
          <p className="indicator-category">{meta.category}</p>
          <h3 className="indicator-name">{meta.name}</h3>
        </div>
        <span
          className={meta.deltaPositive ? "delta delta-good" : "delta"}
        >
          {meta.deltaDirection === "flat" ? null : (
            <span className="delta-glyph">{directionGlyph(meta)}</span>
          )}
          {meta.delta}
        </span>
      </div>
      <div className="indicator-value-row">
        <div className="indicator-value">
          {meta.value}
          <span className="indicator-unit">{meta.unit}</span>
        </div>
        <div className="indicator-period">{meta.period}</div>
      </div>
      <Sparkline points={meta.sparkline} color={meta.sparklineColor} />
      <p className="indicator-note">{meta.note}</p>
      <footer className="indicator-footer">
        <span className="indicator-source">
          {meta.source} • Rilis: {meta.sourceDate}
        </span>
        <a className="indicator-link" href="#detail">
          Lihat Detail →
        </a>
      </footer>
    </article>
  );
}
