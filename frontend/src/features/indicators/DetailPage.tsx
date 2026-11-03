import { useEffect, useId, type ReactNode } from 'react'
import { BrandMark } from '../../components/EditorialLanding'
import { summaryMatches } from './api'
import { boundContext } from './source'
import { useDetailData } from './useDetailData'
import { chartGeometry, contextHref, formatDecimal, INDICATORS, safeExternalUrl } from './data'
import type { DetailData, HistoryPoint, Route, Selector } from './types'

export function Field({ label, children }: { label: string; children?: ReactNode }) {
  return <div><dt>{label}</dt><dd>{children ?? 'Belum tersedia'}</dd></div>
}
export function SourceLink({ url, children }: { url: string | null | undefined; children: ReactNode }) {
  const safe = safeExternalUrl(url)
  return safe ? <a href={safe} target="_blank" rel="noopener noreferrer">{children} ↗<span className="fd-sr-only"> (tab baru)</span></a> : <span>Tautan belum tersedia atau tidak aman.</span>
}
export function FeatureShell({ children }: { children: ReactNode }) {
  return <div className="deksi-page indicator-feature">
    <a className="skip-link" href="#feature-content">Lewati ke konten utama</a>
    <header className="fd-top"><a href="/" className="fd-brand" aria-label="DEKSI, kembali ke dashboard"><BrandMark />DEKSI</a><a href="/#indikator">Kembali ke dashboard ↗</a><span>AKSES PUBLIK / TANPA AKUN</span></header>
    {children}
    <footer className="fd-footer"><strong>DEKSI / Data, konteks, sumber.</strong><p>Periode observasi, tanggal rilis, dan waktu akuisisi adalah metadata yang berbeda. Nama institusi bukan bukti angka sudah diverifikasi.</p></footer>
  </div>
}
export function FeatureUnavailable({ source = false }: { source?: boolean }) {
  return <FeatureShell><main id="feature-content" className="fd-main" tabIndex={-1}><p className="fd-kicker">{source ? '07 / SOURCE TRACE' : 'ALAMAT TIDAK TERSEDIA'}</p><h1>{source ? 'Source Trace belum dipasang.' : 'Halaman tidak ditemukan.'}</h1><p className="fd-lead">{source ? 'Halaman ini akan diintegrasikan pada branch fitur 7. Tidak ada metadata atau snapshot pengganti yang ditampilkan.' : 'Indikator, parameter observasi, atau revisi pada alamat ini tidak didukung. Tidak dialihkan ke nilai terbaru.'}</p><a className="fd-button" href="/">Kembali ke dashboard</a></main></FeatureShell>
}
function History({ history }: { history: HistoryPoint[] }) {
  const title = useId(), description = useId()
  const chart = chartGeometry(history, history[0]?.unit ?? '')
  const chartError = history.some(point => point.unit !== history[0]?.unit) ? 'Satuan histori tidak konsisten.' : new Set(history.map(point => point.sourceId ?? null)).size > 1 ? 'Sumber histori tidak konsisten.' : 'Jenis data atau frekuensi histori tidak konsisten.'
  return <section className="fd-section fd-history" aria-labelledby={title}>
    <div className="fd-section-head"><h2 id={title}>Histori indikator</h2><span>{history.length ? `${history.length} titik dari API` : 'DATA BELUM TERSEDIA'}</span></div>
    <p id={description} className="fd-muted">Grafik mengikuti respons histori, bukan perhitungan ekonomi frontend. Titik grafik tidak menjamin metadata Source Trace tersedia.</p>
    {!history.length ? <div className="fd-chart-empty"><p>Histori belum tersedia.</p><span>Tidak ada angka contoh atau seri nol pengganti.</span></div> : chart === null ? <p className="fd-chart-empty">{chartError} Grafik tidak ditampilkan; nilai asli tetap ada pada tabel.</p> : !chart.points.length ? <p className="fd-chart-empty">Nilai historis belum tersedia. Data kosong tidak dianggap nol.</p> : <figure>
      <p className="fd-chart-unit">Satuan: {history[0].unit}</p>
      <svg viewBox="0 0 760 244" role="img" aria-labelledby={`${title} ${description}`}>
        {chart.ticks.map(tick => <g key={tick.y}><line x1="120" x2="716" y1={tick.y} y2={tick.y} className="fd-grid" /><text x="108" y={tick.y + 4} textAnchor="end" className="fd-axis-label">{tick.label}</text></g>)}
        {chart.segments.map((points, i) => <polyline key={i} points={points} className="fd-line" />)}
        {chart.points.map((point, i) => <circle key={i} cx={point.x} cy={point.y} r="4" className="fd-point"><title>{`${point.period}: ${formatDecimal(point.value)} ${history[0].unit}`}</title></circle>)}
        <text x="120" y="230">{history[0].period}</text><text x="716" y="230" textAnchor="end">{history[history.length - 1].period}</text>
      </svg><figcaption>Geometri grafik menggunakan pendekatan numerik; tabel mempertahankan string presisi API. Garis diputus pada jeda periode reguler yang dapat dikenali dari tanggal API; kalender kerja harian tidak diasumsikan.</figcaption>
    </figure>}
    {history.length > 0 && <details><summary>Lihat tabel histori</summary><div className="fd-table-scroll" tabIndex={0} role="region" aria-label="Tabel histori indikator"><table><caption>Observasi historis, bukan jurnal revisi</caption><thead><tr><th scope="col">Periode</th><th scope="col">Tanggal observasi</th><th scope="col">Nilai</th><th scope="col">Satuan</th><th scope="col">Frekuensi</th><th scope="col">Jenis data</th><th scope="col">Sumber</th></tr></thead><tbody>{history.map((point, index) => <tr key={index}><th scope="row">{point.period}</th><td>{point.observationDate ?? 'Belum tersedia'}</td><td>{formatDecimal(point.value)}</td><td>{point.unit}</td><td>{point.frequency ?? 'Belum tersedia'}</td><td>{point.dataType ?? 'Belum tersedia'}</td><td>{point.sourceId ?? 'Belum tersedia'}</td></tr>)}</tbody></table></div></details>}
  </section>
}
export interface DetailProps { code: string; selector: Selector | null; data: DetailData | null; loading: boolean; error?: string | null; onRetry: () => void }
export function DetailPage({ code, selector, data, loading, error, onRetry }: DetailProps) {
  const reading = data?.contextError ? null : data?.selected ?? null
  const summary = !selector && data?.summary?.available ? data.summary : null
  const value = reading ? reading.value : summary?.value ?? null
  const unit = reading ? reading.unit : summary?.unit ?? null
  const period = reading ? reading.period : summary?.period ?? null
  const title = reading?.indicatorName ?? data?.summary?.name ?? 'Detail indikator.'
  const options = data?.options ?? []
  const requestedGuard = selector?.guard ?? options.find(option => JSON.stringify(option.reading) === JSON.stringify(reading))?.guard
  const activeGuard = options.some(option => option.guard === requestedGuard) ? requestedGuard : ''
  const delta = data && ((reading && summaryMatches(data.summary, reading)) || (!reading && !selector && !data.contextError)) ? data.summary?.delta : null
  const publicationDate = reading ? reading.publicationDate : summary?.publicationDate
  const observationDate = reading ? reading.observationDate : summary?.observationDate
  const source = reading ? reading.source?.institution : summary?.source
  const frequency = reading ? reading.frequency : summary?.frequency
  const dataType = reading ? reading.dataType : summary?.dataType
  const acquisition = reading ? reading.rawFile?.retrievedAt : summary?.retrievedAt
  const sourceContext = !loading && !error ? boundContext(data) : null
  const sourceHref = sourceContext ? contextHref(sourceContext.reading, sourceContext.guard, true) : null
  return <FeatureShell><main className="fd-main" id="feature-content" tabIndex={-1} aria-busy={loading}>
    <nav className="fd-breadcrumb" aria-label="Breadcrumb"><a href="/">Dashboard</a><span aria-hidden="true">/</span><span aria-current="page">Detail indikator</span></nav>
    <header className="fd-heading"><div><p className="fd-kicker">06 / DETAIL INDIKATOR EKONOMI</p><h1>{title}</h1></div><p className="fd-lead">Baca angka bersama periode, satuan, dan sumbernya. Informasi yang belum tersedia tidak diisi dengan data pengganti.</p></header>
    <nav className="fd-indicators" aria-label="Pilih indikator">{INDICATORS.map(([id, label]) => <a key={id} href={`/indikator/${id}`} aria-current={code === id ? 'page' : undefined}>{label}</a>)}</nav>
    {loading && <p className="fd-status" role="status">Memuat data indikator dari API DEKSI…</p>}
    {(error || data?.contextError || !!data?.warnings.length) && <aside className="fd-status" role="alert"><strong>{error ?? data?.contextError ?? 'Sebagian data belum tersedia.'}</strong>{!!data?.warnings.length && <details><summary>Rincian ketersediaan API</summary><ul>{data.warnings.map(message => <li key={message}>{message}</li>)}</ul></details>}<button type="button" className="fd-button" onClick={onRetry}>Coba lagi</button></aside>}
    <div className="fd-controls"><label htmlFor="fd-period">PERIODE OBSERVASI<select id="fd-period" disabled={loading || options.length === 0} value={activeGuard} onChange={event => { const option = options.find(item => item.guard === event.target.value); if (option) window.location.assign(contextHref(option.reading, option.guard)) }}><option value="" disabled>{options.length ? 'Pilih konteks yang tersedia' : 'Periode rinci belum tersedia'}</option>{options.map(option => <option key={option.guard} value={option.guard}>{option.reading.period} · {option.reading.observationDate} · {option.reading.source?.sourceId}</option>)}</select></label><p>Daftar mengikuti konteks sumber yang tersedia pada API. Histori yang lebih panjang tidak otomatis memiliki detail atau revisi yang dapat dipilih.</p></div>
    <div className="fd-columns"><div>
      <section className="fd-section fd-reading" aria-label="Nilai indikator terpilih"><p className="fd-kicker">{selector ? 'KONTEKS OBSERVASI TERPILIH' : 'NILAI TERBARU PADA RESPONS API'}</p><p className={`fd-metric${value === null ? ' fd-missing' : ''}`}>{formatDecimal(value)}</p><p className="fd-unit">{unit ?? 'Satuan belum tersedia'}</p>
        <dl className="fd-metadata fd-metadata-row"><Field label="Periode observasi">{period}</Field><Field label="Frekuensi sumber">{frequency}</Field><Field label="Jenis data backend">{dataType}</Field></dl>
        <div className="fd-comparison"><h2>Perubahan & pembanding</h2><p>{delta ?? 'Pembanding untuk konteks ini belum tersedia. Frontend tidak menghitung perubahan dari grafik.'}</p></div>
      </section>
      <History history={data?.history ?? []} />
      <section className="fd-section"><p className="fd-kicker">MEMBACA ANGKA</p><h2>Angka bukan kesimpulan.</h2><p className="fd-body-copy">Definisi rinci belum disediakan oleh endpoint detail yang tersedia. Angka naik atau turun tidak otomatis berarti baik atau buruk. Tidak ada interpretasi atau narasi AI pengganti pada halaman ini.</p></section>
    </div><aside className="fd-aside" aria-label="Konteks dan sumber">
      <section className="fd-section"><p className="fd-kicker">ASAL & WAKTU</p><h2>Konteks data.</h2><dl className="fd-metadata"><Field label="Institusi sumber">{source}</Field><Field label="Publikasi / nama sumber">{reading?.source?.sourceName}</Field><Field label="Tanggal observasi">{observationDate}</Field><Field label="Tanggal rilis">{publicationDate ? `${publicationDate} (tanggal saja)` : null}</Field><Field label="Waktu akuisisi">{acquisition}</Field><Field label="Dokumen RAW">{reading?.rawFile?.documentName}</Field></dl><div className="fd-links"><SourceLink url={reading?.rawFile?.sourceUrl}>Buka sumber dokumen</SourceLink><SourceLink url={reading?.source?.primaryUrl}>Buka portal institusi</SourceLink></div><p className="fd-small">Portal institusi dan dokumen primer bukan hal yang sama. Metadata RAW yang tidak disertakan tidak diganti dari observasi lain.</p></section>
      <section className="fd-source-panel"><p className="fd-kicker">07 / TELUSURI ANGKA INI</p><h2>Source Trace.</h2><p>Baca sumber, rilis, dan batas perhitungan untuk konteks yang sama. Metadata tidak dialihkan ke observasi lain.</p>{sourceHref ? <a className="fd-button" href={sourceHref}>Buka Source Trace ↗</a> : <button type="button" className="fd-button" disabled>Konteks Source Trace belum tersedia</button>}<p className="fd-small">Identitas revisi dan snapshot immutable belum disediakan backend. Kecocokan respons bukan jaminan versi historis.</p></section>
      <section className="fd-section"><h2>Status & keterbatasan</h2><dl className="fd-metadata"><Field label="Status dari backend">{reading?.validationStatus}</Field><Field label="Waktu review pada respons">{reading?.reviewedAt}</Field><Field label="ID observasi / revisi">Belum disediakan API</Field><Field label="Klasifikasi nilai resmi / turunan">Belum disediakan API</Field></dl><p className="fd-small">Status publikasi bukan klaim independen bahwa angka telah terverifikasi resmi.</p></section>
    </aside></div>
  </main></FeatureShell>
}
export function DetailScreen({ route }: { route: Extract<Route, { kind: 'detail' | 'source' }> }) {
  const state = useDetailData(route)
  useEffect(() => { document.title = 'Detail Indikator · DEKSI' }, [])
  return <DetailPage code={route.code} selector={route.selector} {...state} />
}
