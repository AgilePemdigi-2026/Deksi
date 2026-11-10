import { useEffect, useMemo, useState } from "react";
import {
  displayOrUnavailable,
  fetchSourceDetail,
  fetchSources,
  type SourceDetail,
  type SourceEntry,
} from "../api";
import { SourceTracePanel } from "./SourceTracePanel";

export interface SourcePageSelection {
  sourceId?: string;
  indicator?: string;
  period?: string;
}

const INSTITUTION_BLURB: Record<string, string> = {
  BPS: "Statistik nasional: PDB, inflasi, ketenagakerjaan.",
  BI: "Moneter: BI-Rate, JISDOR, indikator moneter.",
  KEMENKEU: "Fiskal: realisasi APBN KiTa kumulatif.",
  BKPM: "Investasi: realisasi PMA/PMDN triwulanan.",
};

export function SourceDataPage({ selection }: { selection: SourcePageSelection }) {
  const [sources, setSources] = useState<SourceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<string | null>(selection.sourceId ?? null);
  const [detail, setDetail] = useState<SourceDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [activeIndicator, setActiveIndicator] = useState<string | null>(selection.indicator ?? null);
  const [activePeriod, setActivePeriod] = useState<string | undefined>(selection.period);

  useEffect(() => {
    setActiveSource(selection.sourceId ?? null);
    setActiveIndicator(selection.indicator ?? null);
    setActivePeriod(selection.period);
  }, [selection.sourceId, selection.indicator, selection.period]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSources()
      .then((rows) => {
        if (cancelled) return;
        setSources(rows);
        setError(null);
        if (!activeSource && rows.length > 0) {
          const preferred =
            (selection.sourceId && rows.find((r) => r.sourceId === selection.sourceId)) || rows[0];
          setActiveSource(preferred.sourceId);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Tidak dapat memuat daftar sumber dari backend DEKSI.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!activeSource) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    fetchSourceDetail(activeSource)
      .then((body) => {
        if (!cancelled) setDetail(body);
      })
      .catch(() => {
        if (!cancelled) setDetailError("Detail sumber tidak dapat dimuat. Metadata daftar di atas tetap berlaku.");
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeSource]);

  const activeDetailIndicators = useMemo(() => detail?.indicatorDetails ?? [], [detail]);

  useEffect(() => {
    if (activeIndicator) return;
    if (activeDetailIndicators.length > 0) setActiveIndicator(activeDetailIndicators[0].code);
  }, [activeDetailIndicators, activeIndicator]);

  return (
    <section className="sources-page" id="sumber-data-page" aria-labelledby="sources-title">
      <div className="section-head">
        <div>
          <h2 className="section-title" id="sources-title">Sumber Data</h2>
          <p className="section-sub">
            Transparansi dan keterlacakan data ekonomi. Setiap angka dibaca bersama institusi,
            periode, satuan, tanggal rilis, dan tautan publikasi resmi. Halaman publik tanpa login.
          </p>
        </div>
        <span className="section-badge">Respons API DEKSI</span>
      </div>

      <nav className="sources-nav" aria-label="Navigasi halaman">
        <a href="/">Beranda</a>
        <a href="#indikator">Indikator</a>
        <a href="#analisis">Analisis</a>
        <a href="/sumber-data" aria-current="page">Sumber Data</a>
        <a href="#tentang">Tentang</a>
      </nav>

      {loading && <p className="summary-loading">Memuat daftar sumber dari backend DEKSI…</p>}
      {!loading && error && <p className="summary-error">{error}</p>}
      {!loading && !error && sources.length === 0 && (
        <p className="summary-empty">Belum ada sumber atau data. Tidak ada nilai contoh yang disisipkan.</p>
      )}

      {!loading && !error && sources.length > 0 && (
        <div className="sources-grid">
          {sources.map((s) => (
            <button
              key={s.sourceId}
              type="button"
              onClick={() => {
                setActiveSource(s.sourceId);
                setActiveIndicator(null);
                setActivePeriod(undefined);
                window.location.assign(`/sumber-data?source=${encodeURIComponent(s.sourceId)}`);
              }}
              className={s.sourceId === activeSource ? "source-card active" : "source-card"}
              aria-pressed={s.sourceId === activeSource}
            >
              <p className="source-institution">{s.institution}{s.status ? ` · ${s.status}` : ""}</p>
              <p className="source-name">{s.sourceName}</p>
              <p className="source-desc">{s.description || INSTITUTION_BLURB[s.sourceId] || ""}</p>
              <p className="source-meta">
                {s.indicatorCount} indikator · {s.observationCount} observasi
              </p>
              <p className="source-meta">
                Jenis: {displayOrUnavailable(s.acquisitionMethod || s.dataFormat)} · Jadwal: {displayOrUnavailable(s.updateSchedule || s.frequency)}
              </p>
              <p className="source-meta">
                Terbaru: {displayOrUnavailable(s.latestPeriod)} ·{" "}
                {s.available ? "Tersedia" : "Belum tersedia"}
              </p>
            </button>
          ))}
        </div>
      )}

      {activeSource && (
        <div className="source-detail">
          {detailLoading && <p className="summary-loading">Memuat indikator {activeSource}…</p>}
          {detailError && <p className="summary-error">{detailError}</p>}
          {detail && !detailLoading && (
            <>
              <div className="source-detail-head">
                <div>
                  <h3>{detail.institution}</h3>
                  <p>{detail.description || INSTITUTION_BLURB[detail.sourceId] || ""}</p>
                </div>
                <a href={detail.primaryUrl} target="_blank" rel="noopener noreferrer">
                  Portal resmi ↗
                </a>
              </div>
              {activeDetailIndicators.length === 0 ? (
                <p className="summary-empty">Belum ada indikator terpublikasi dari sumber ini.</p>
              ) : (
                <div className="source-indicators">
                  {activeDetailIndicators.map((ind) => (
                    <button
                      key={ind.code}
                      type="button"
                      onClick={() => {
                        setActiveIndicator(ind.code);
                        setActivePeriod(undefined);
                        window.location.assign(`/sumber-data?source=${encodeURIComponent(detail.sourceId)}&indicator=${encodeURIComponent(ind.code)}`);
                      }}
                      className={ind.code === activeIndicator ? "source-ind active" : "source-ind"}
                    >
                      <span className="source-ind-name">{ind.name}</span>
                      <span className="source-ind-meta">
                        {displayOrUnavailable(ind.value)} {ind.available ? ind.unit : ""} ·{" "}
                        {displayOrUnavailable(ind.period)}
                      </span>
                      <span className="source-ind-type">{ind.valueType ?? ind.dataType ?? "Tidak tersedia"}</span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeIndicator && (
        <SourceTracePanel code={activeIndicator} period={activePeriod} />
      )}
    </section>
  );
}
