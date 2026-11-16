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

const PAGE_SIZE = 8;

function frequencyLabel(freq: string | undefined): string {
  const v = (freq || "").toLowerCase();
  if (v === "daily") return "Harian";
  if (v === "monthly") return "Bulanan";
  if (v === "quarterly") return "Triwulanan";
  if (v === "semiannual") return "Semesteran";
  if (v === "annual") return "Tahunan";
  if (v === "adhoc") return "Ad-hoc";
  if (v === "mixed") return "Campuran";
  return freq || displayOrUnavailable(freq);
}

function verificationOf(s: SourceEntry): { label: string; kind: "ok" | "warn" | "bad" } {
  if (s.status === "inactive") return { label: "Dalam tinjauan", kind: "warn" };
  if (s.available) return { label: "Terverifikasi", kind: "ok" };
  return { label: "Perlu pembaruan", kind: "bad" };
}

function toCatalogId(s: SourceEntry, idx: number): string {
  const inst = (s.institution || s.sourceId || "XX").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 6) || "SRC";
  return `${inst}-${String(idx + 1).padStart(2, "0")}`;
}

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
  const [query, setQuery] = useState("");
  const [institution, setInstitution] = useState("Semua institusi");
  const [category, setCategory] = useState("Semua kategori");
  const [verification, setVerification] = useState("Semua status");
  const [sort, setSort] = useState("Relevansi");
  const [page, setPage] = useState(1);

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

  const institutions = useMemo(() => Array.from(new Set(sources.map((s) => s.institution).filter(Boolean))), [sources]);
  const categories = useMemo(() => Array.from(new Set(sources.map((s) => frequencyLabel(s.frequency)).filter(Boolean))), [sources]);
  const totalIndicators = useMemo(() => sources.reduce((a, s) => a + (s.indicatorCount || 0), 0), [sources]);
  const verifiedCount = useMemo(() => sources.filter((s) => verificationOf(s).kind === "ok").length, [sources]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let rows = sources.filter((s) => {
      if (institution !== "Semua institusi" && s.institution !== institution) return false;
      if (category !== "Semua kategori" && frequencyLabel(s.frequency) !== category) return false;
      const v = verificationOf(s).label;
      if (verification !== "Semua status" && v !== verification) return false;
      if (!q) return true;
      const hay = `${s.sourceName} ${s.sourceId} ${s.institution} ${(s.indicators || []).join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
    if (sort === "Nama A-Z") rows = [...rows].sort((a, b) => a.sourceName.localeCompare(b.sourceName));
    if (sort === "Indikator terbanyak") rows = [...rows].sort((a, b) => (b.indicatorCount || 0) - (a.indicatorCount || 0));
    return rows;
  }, [sources, query, institution, category, verification, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const downloadCatalog = () => {
    const header = "source_id,source_name,institution,indicators,observations,frequency,latest_period,status\n";
    const body = filtered.map((s) => [s.sourceId, `"${(s.sourceName || "").replace(/"/g, '""')}"`, `"${(s.institution || "").replace(/"/g, '""')}"`, s.indicatorCount, s.observationCount, frequencyLabel(s.frequency), `"${s.latestPeriod || ""}"`, verificationOf(s).label].join(",")).join("\n");
    const blob = new Blob([header + body], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "deksi-katalog-sumber.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const openDetail = (sourceId: string) => {
    setActiveSource(sourceId);
    setActiveIndicator(null);
    setActivePeriod(undefined);
    setPage(safePage);
  };

  return (
    <section className="sources-page catalog" id="sumber-data-page" aria-labelledby="sources-title">
      <p className="catalog-crumb">Dashboard &gt; Sumber Data</p>
      <div className="catalog-hero">
        <div>
          <p className="catalog-kicker">KATALOG SUMBER RESMI</p>
          <h2 className="section-title" id="sources-title">Sumber Data</h2>
          <p className="section-sub">
            Jelajahi publikasi resmi di balik indikator ekonomi DEKSI. Temukan cakupan data, jadwal rilis, dan jejak verifikasi setiap sumber.
          </p>
        </div>
        <button type="button" className="catalog-download" onClick={downloadCatalog}>⭳ Unduh katalog</button>
      </div>

      <div className="catalog-stats">
        <div className="catalog-stat"><p>SUMBER DATA</p><strong>{sources.length}</strong><span>Publikasi &amp; kumpulan data</span></div>
        <div className="catalog-stat"><p>INSTITUSI RESMI</p><strong>{institutions.length}</strong><span>{institutions.join(", ") || "—"}</span></div>
        <div className="catalog-stat"><p>CAKUPAN INDIKATOR</p><strong>{totalIndicators}</strong><span>Indikator ekonomi terpetakan</span></div>
        <div className="catalog-stat"><p>SUMBER TERVERIFIKASI</p><strong>{verifiedCount} / {sources.length}</strong><span>{sources.length - verifiedCount} perlu perhatian</span></div>
      </div>

      <p className="catalog-note">ⓘ Data live dari API DEKSI. Pembaruan mengikuti jadwal rilis institusi.</p>

      <div className="catalog-explore">
        <div className="catalog-explore-head">
          <div>
            <h3>Jelajahi sumber data</h3>
            <p>Cari sumber, periksa cakupannya, lalu telusuri indikator ke publikasi asal.</p>
          </div>
          <span className="catalog-count">● {filtered.length} sumber terdaftar</span>
        </div>
        <div className="catalog-filters">
          <label>Cari sumber data<input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Nama sumber, indikator, atau kata kunci..." /></label>
          <label>Institusi<select value={institution} onChange={(e) => { setInstitution(e.target.value); setPage(1); }}><option>Semua institusi</option>{institutions.map((i) => <option key={i}>{i}</option>)}</select></label>
          <label>Kategori<select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}><option>Semua kategori</option>{categories.map((c) => <option key={c}>{c}</option>)}</select></label>
          <label>Status verifikasi<select value={verification} onChange={(e) => { setVerification(e.target.value); setPage(1); }}><option>Semua status</option><option>Terverifikasi</option><option>Dalam tinjauan</option><option>Perlu pembaruan</option></select></label>
        </div>

        {loading && <p className="summary-loading">Memuat daftar sumber dari backend DEKSI…</p>}
        {!loading && error && <p className="summary-error">{error}</p>}
        {!loading && !error && sources.length === 0 && (
          <p className="summary-empty">Belum ada sumber atau data. Tidak ada nilai contoh yang disisipkan.</p>
        )}

        {!loading && !error && sources.length > 0 && (
          <>
            <div className="catalog-meta"><span>Menampilkan {(safePage - 1) * PAGE_SIZE + 1}–{(safePage - 1) * PAGE_SIZE + pageRows.length} dari {filtered.length} sumber data</span>
              <label>Urutkan: <select value={sort} onChange={(e) => setSort(e.target.value)}><option>Relevansi</option><option>Nama A-Z</option><option>Indikator terbanyak</option></select></label>
            </div>
            <div className="catalog-table-wrap" role="region" aria-label="Tabel sumber data" tabIndex={0}>
              <table className="catalog-table">
                <thead><tr><th>SUMBER DATA</th><th>INSTITUSI</th><th>CAKUPAN INDIKATOR</th><th>RILIS</th><th>PEMBARUAN</th><th>VERIFIKASI</th><th>AKSES</th></tr></thead>
                <tbody>
                  {pageRows.map((s, i) => {
                    const v = verificationOf(s);
                    return (
                      <tr key={s.sourceId}>
                        <td><strong>{s.sourceName}</strong><span className="catalog-sub">{toCatalogId(s, i)} · {s.sourceId}</span></td>
                        <td><span className="catalog-pill">{s.sourceId}</span><span className="catalog-sub">{s.institution}</span></td>
                        <td><span className="catalog-sub">{s.description?.slice(0, 80) || INSTITUTION_BLURB[s.sourceId] || ""}</span><span className="catalog-link">{s.indicatorCount} indikator</span></td>
                        <td>{frequencyLabel(s.frequency)}</td>
                        <td><strong>{s.latestPeriod || "—"}</strong><span className="catalog-sub">{s.latestObservationDate || s.updateSchedule || ""}</span></td>
                        <td><span className={`catalog-badge catalog-badge--${v.kind}`}>{v.label}</span></td>
                        <td><button type="button" className="catalog-detail" onClick={() => openDetail(s.sourceId)}>Detail →</button><button type="button" className="catalog-trace" onClick={() => openDetail(s.sourceId)}>⛓ Source Trace</button></td>
                      </tr>
                    );
                  })}
                  {pageRows.length === 0 && <tr><td colSpan={7}>Tidak ada sumber untuk filter ini.</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="catalog-pager"><span>{PAGE_SIZE} sumber per halaman · Halaman {safePage} dari {totalPages}</span>
              <span>
                {[1, 2, 3].filter((n) => n <= totalPages).map((n) => <button key={n} type="button" className={n === safePage ? "active" : ""} onClick={() => setPage(n)}>{n}</button>)}
                <button type="button" disabled={safePage >= totalPages} onClick={() => setPage(safePage + 1)}>›</button>
              </span>
            </div>
          </>
        )}
      </div>

      <div className="catalog-bottom">
        <div className="catalog-log">
          <h3>Catatan pembaruan sumber</h3>
          {sources.slice(0, 3).map((s) => <p key={s.sourceId}><span>{s.latestPeriod || "—"}</span> <strong>{s.institution} · {s.sourceName}</strong><br />{s.updateSchedule || s.description?.slice(0, 80) || ""}</p>)}
        </div>
        <div className="catalog-transparency">
          <p>⛨ TRANSPARANSI DATA</p>
          <h3>Setiap indikator memiliki jejak sumber.</h3>
          <p>Source Trace menghubungkan publikasi resmi, periode rilis, data input, dan perhitungan DEKSI.</p>
          <button type="button" onClick={() => activeIndicator && document.getElementById("source-trace-panel")?.scrollIntoView({ behavior: "smooth" })}>↗ Buka Source Trace</button>
        </div>
      </div>

      <div className="sources-grid legacy">
        {sources.map((s) => (
          <button
            key={s.sourceId}
            type="button"
            onClick={() => {
              setActiveSource(s.sourceId);
              setActiveIndicator(null);
              setActivePeriod(undefined);
            }}
            className={s.sourceId === activeSource ? "source-card active" : "source-card"}
            aria-pressed={s.sourceId === activeSource}
            hidden
          >
            {s.sourceName}
          </button>
        ))}
      </div>

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
