import { useMemo } from "react";

const FALLBACK_PERIOD = "Memuat periode terbaru…";

export function Hero({
  updatedAt,
  period,
  loading,
  error,
}: {
  updatedAt: string | null;
  period: string | null;
  loading: boolean;
  error: string | null;
}) {
  const strip = useMemo(() => {
    if (error) {
      return {
        update: "⚠️ Tidak dapat menghubungi backend DEKSI",
        period: FALLBACK_PERIOD,
        tone: "error" as const,
      };
    }
    if (loading || !updatedAt) {
      return {
        update: "🕘 Terakhir diperbarui: memuat…",
        period: FALLBACK_PERIOD,
        tone: "loading" as const,
      };
    }
    return {
      update: `🕘 Terakhir diperbarui: ${updatedAt}`,
      period: `🗓️ Periode Analisis Terbaru: ${period ?? ""}`.trim(),
      tone: "ok" as const,
    };
  }, [updatedAt, period, loading, error]);

  return (
    <section className="hero" id="dashboard">
      <p className="hero-eyebrow">
        Platform Data &amp; Analisis Ekonomi • Data dari Kementerian &amp; Lembaga Resmi
      </p>
      <h1 className="hero-title">Kondisi Ekonomi Indonesia</h1>
      <p className="hero-sub">
        Ringkasan indikator ekonomi makro terbaru berdasarkan data resmi
        kementerian dan lembaga negara yang diperbarui secara berkala.
      </p>
      <div className="hero-strip">
        <span
          className={strip.tone === "ok" && strip.update ? "strip-item" : "strip-item"}
          data-status={strip.tone}
        >
          {strip.update}
        </span>
        <span className="strip-item">{strip.period}</span>
        <span className="strip-right">✅ Sumber Terverifikasi: BPS • BI • KEMENKEU • BKPM</span>
      </div>
    </section>
  );
}
