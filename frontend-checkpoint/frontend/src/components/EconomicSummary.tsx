import type { SummaryCard } from "../api";
import { IndicatorCard } from "./IndicatorCard";

const CARD_COLORS: Record<string, string> = {
  pdb: "#2563eb",
  inflasi: "#16a34a",
  fiskal: "#0f172a",
  investasi: "#0891b2",
  birate: "#7c3aed",
  tpt: "#ea580c",
};

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export const formatDateID = (iso?: string | null): string => {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.getDate()} ${MONTHS_SHORT[date.getMonth()]} ${date.getFullYear()}`;
};

const toCardMeta = (card: SummaryCard) => ({
  id: card.id,
  category: card.category || "Indikator Ekonomi",
  name: card.name,
  value: card.value ?? "-",
  unit: card.value ? card.unit : "",
  period: card.period ?? "Data belum tersedia",
  delta: card.delta ?? "Tidak ada pembanding",
  deltaDirection: card.deltaDirection,
  deltaPositive: card.deltaPositive,
  note: card.dataAvailabilityNote
    ? `${card.note} ${card.dataAvailabilityNote}`
    : card.note,
  source: card.source || "Sumber belum tersedia",
  sourceDate: formatDateID(card.observationDate) || "belum tersedia",
  sparkline: card.sparkline ?? [],
  sparklineColor: CARD_COLORS[card.id] ?? "#2563eb",
});

export function EconomicSummary({
  cards,
  loading,
  error,
}: {
  cards: SummaryCard[];
  loading: boolean;
  error: string | null;
}) {
  return (
    <section className="summary" id="indikator">
      <div className="section-head">
        <div>
          <h2 className="section-title">Indikator Ekonomi Utama</h2>
          <p className="section-sub">
            Nilai, periode, satuan, dan sumber mengikuti respons API DEKSI.
          </p>
        </div>
        <span className="section-badge">Respons API DEKSI</span>
      </div>
      {loading && <p className="summary-loading">Memuat data dari backend DEKSI…</p>}
      {!loading && error && <p className="summary-error">{error}</p>}
      {!loading && !error && cards.length === 0 && <p className="summary-empty">Belum ada indikator pada respons API. Tidak ada nilai contoh yang disisipkan.</p>}
      <div className="summary-grid">
        {cards.map((card) => (
          <IndicatorCard key={card.id} meta={toCardMeta(card)} />
        ))}
      </div>
    </section>
  );
}
