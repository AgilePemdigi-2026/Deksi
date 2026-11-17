import { useEffect, useMemo, useRef, useState } from "react";
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

function availabilityOf(s: SourceEntry): { label: string; kind: "ok" | "warn" | "bad" } {
  if (s.status === "inactive") return { label: "Nonaktif", kind: "warn" };
  if (s.available) return { label: "Data tersedia", kind: "ok" };
  return { label: "Belum ada data", kind: "bad" };
}

function csvCell(value: unknown): string {
  const raw = value === null || value === undefined ? "" : String(value);
  // Mitigasi formula spreadsheet: prefix nilai teks diawali =,+,-,@,tab,CR.
  const needsGuard = /^[ \t\r\n]*[=+\-@]/.test(raw);
  const guarded = needsGuard ? `'${raw}` : raw;
  return `"${guarded.replace(/"/g, '""')}"`;
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
  const activeSourceRef = useRef<string | null>(activeSource);
  activeSourceRef.current = activeSource;

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
    const requestSource = activeSource;
    let cancelled = false;
    // Kosongkan detail lama agar trace/indikator sumber sebelumnya
    // tidak tampil sebagai milik sumber baru selama fetch berjalan.
    setDetail(null);
    setActiveIndicator(null);
    setActivePeriod(undefined);
    setDetailLoading(true);
    setDetailError(null);
    fetchSourceDetail(requestSource)
      .then((body) => {
        if (!cancelled && requestSource === activeSourceRef.current) setDetail(body);
      })
      .catch(() => {
        if (!cancelled && requestSource === activeSourceRef.current)
          setDetailError("Detail sumber tidak dapat dimuat. Metadata daftar di atas tetap berlaku.");
      })
      .finally(() => {
        if (!cancelled && requestSource === activeSourceRef.current) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSource]);

  const activeDetailIndicators = useMemo(
    () => (detail && detail.sourceId === activeSource ? detail.indicatorDetails ?? [] : []),
    [detail, activeSource],
  );

  useEffect(() => {
    if (activeIndicator) return;
    if (!detail || detail.sourceId !== activeSource) return;
    if (activeDetailIndicators.length > 0) setActiveIndicator(activeDetailIndicators[0].code);
  }, [activeDetailIndicators, activeIndicator, detail, activeSource]);

  const institutions = useMemo(() => Array.from(new Set(sources.map((s) => s.institution).filter(Boolean))), [sources]);
  const categories = useMemo(() => Array.from(new Set(sources.map((s) => frequencyLabel(s.frequency)).filter(Boolean))), [sources]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let rows = sources.filter((s) => {
      if (institution !== "Semua institusi" && s.institution !== institution) return false;
      if (category !== "Semua kategori" && frequencyLabel(s.frequency) !== category) return false;
      const v = availabilityOf(s).label;
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
    const body = filtered.map((s) => [csvCell(s.sourceId), csvCell(s.sourceName), csvCell(s.institution), String(s.indicatorCount ?? ""), String(s.observationCount ?? ""), csvCell(frequencyLabel(s.frequency)), csvCell(s.latestPeriod ?? ""), csvCell(availabilityOf(s).label)].join(",")).join("\n");
    const blob = new Blob([header + body], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "deksi-katalog-sumber.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const openDetail = (sourceId: string) => {
    if (sourceId === activeSource) return;
    setDetail(null);
    setDetailError(null);
    setActiveSource(sourceId);
    setActiveIndicator(null);
    setActivePeriod(undefined);
    setPage(safePage);
  };

  const pagerPages = useMemo(() => {
    const set = new Set<number>([1, totalPages, safePage - 1, safePage, safePage + 1]);
    return [...set].filter((n) => n >= 1 && n <= totalPages).sort((a, b) => a - b);
  }, [totalPages, safePage]);

  return (
    <section className="sources-page catalog" id="sumber-data-page" aria-labelledby="sources-title">
      <p className="catalog-crumb">Dashboard &gt; Sumber Data</p>
      <div className="catalog-hero">
        <div>
          <p className="catalog-kicker">KATALOG SUMBER RESMI</p>
          <h2 className="section-title" id="sources-title">Sumber Data</h2>
          <p className="section-sub">
            Jelajahi publikasi resmi di balik indikator ekonomi DEKSI. Temukan cakupan data, jadwal rilis, dan ketersediaan data setiap sumber.
          </p>
        </div>
        <button type="button" className="catalog-download" onClick={downloadCatalog}>⭳ Unduh katalog</button>
      </div>

      <nav className="sources-nav" aria-label="Navigasi halaman">
        <a href="/">Beranda</a>
        <a href="/#economic-indicators">Indikator</a>
        <a href="/#economic-insights">Panduan membaca</a>
        <a href="/sumber-data" aria-current="page">Sumber Data</a>
        <a href="/#about-deksi">Tentang</a>
      </nav>

      {loading && <p className="summary-loading">Memuat daftar sumber dari backend DEKSI…</p>}
      {!loading && error && <p className="summary-error">{error}</p>}
      {!loading && !error && sources.length === 0 && (
        <p className="summary-empty">Belum ada sumber atau data. Tidak ada nilai contoh yang disisipkan.</p>
      )}

      <p className="catalog-note">ⓘ Data live dari API DEKSI. Jadwal yang tercatat berasal dari metadata sumber; waktu pembaruan aktual dapat berbeda.</p>

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
          <label>Status data<select value={verification} onChange={(e) => { setVerification(e.target.value); setPage(1); }}><option>Semua status</option><option>Data tersedia</option><option>Nonaktif</option><option>Belum ada data</option></select></label>
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
                <thead><tr><th>SUMBER DATA</th><th>INSTITUSI</th><th>CAKUPAN INDIKATOR</th><th>RILIS</th><th>PEMBARUAN</th><th>STATUS DATA</th><th>AKSES</th></tr></thead>
                <tbody>
                  {pageRows.map((s, i) => {
                    const v = availabilityOf(s);
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
                <button type="button" aria-label="Halaman sebelumnya" disabled={safePage <= 1} onClick={() => setPage(Math.max(1, safePage - 1))}>‹</button>
                {pagerPages.map((n) => <button key={n} type="button" aria-label={`Halaman ${n}`} aria-current={n === safePage ? "page" : undefined} className={n === safePage ? "active" : ""} onClick={() => setPage(n)}>{n}</button>)}
                <button type="button" aria-label="Halaman berikutnya" disabled={safePage >= totalPages} onClick={() => setPage(Math.min(totalPages, safePage + 1))}>›</button>
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
              if (s.sourceId === activeSource) return;
              setDetail(null);
              setDetailError(null);
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
          {detailError && !detailLoading && <p className="summary-error">{detailError}</p>}
          {detail && !detailLoading && detail.sourceId === activeSource && (
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

      {activeIndicator && detail && detail.sourceId === activeSource && (
        <SourceTracePanel key={`${activeSource}:${activeIndicator}`} code={activeIndicator} period={activePeriod} />
      )}
    </section>
  );
}
