import { useEffect } from 'react'
import { Field, FeatureShell, SourceLink, type DetailProps } from './DetailPage'
import { contextHref, formatDecimal } from './data'
import { boundContext, rawDownloadHref } from './source'
import type { Route } from './types'
import { useDetailData } from './useDetailData'
import './source-trace.css'

export function SourceTracePage({ code, selector, data, loading, error, onRetry }: DetailProps) {
  const reading = data?.contextError ? null : data?.selected ?? null
  const bound = !loading && !error ? boundContext(data) : null
  const returnHref = bound ? contextHref(bound.reading, bound.guard) : null
  const downloadHref = reading ? rawDownloadHref(reading.rawFile?.downloadUrl, reading.indicatorCode) : null
  const stages = [
    ['Institusi', reading?.source?.institution],
    ['Dokumen primer', reading?.rawFile?.documentName],
    ['Rilis', reading?.publicationDate],
    ['Observasi', reading?.period],
    ['Kalkulasi', null], ['Analisis', null],
  ]
  return <FeatureShell><main id="feature-content" className="fd-main source-trace-feature" tabIndex={-1} aria-busy={loading}>
    <nav className="fd-breadcrumb" aria-label="Breadcrumb"><a href="/">Dashboard</a><span aria-hidden="true">/</span>{returnHref ? <><a href={returnHref}>Detail indikator</a><span aria-hidden="true">/</span></> : null}<span aria-current="page">Source Trace Data</span></nav>
    <header className="fd-heading"><div><p className="fd-kicker">07 / SOURCE TRACE DATA</p><h1>Source Trace Data.</h1></div><p className="fd-lead">Asal angka, dokumen, dan batas perhitungan dibaca terpisah. Metadata yang tersedia bukan klaim bahwa seluruh proses telah diverifikasi.</p></header>
    {loading && <p className="fd-status" role="status">Memuat metadata sumber…</p>}
    {(error || data?.contextError || !!data?.warnings.length) && <aside className="fd-status" role="alert"><strong>{error ?? data?.contextError ?? 'Sebagian metadata belum tersedia.'}</strong>{!!data?.warnings.length && <details><summary>Rincian respons API</summary><ul>{data.warnings.map(message => <li key={message}>{message}</li>)}</ul></details>}<button className="fd-button" type="button" onClick={onRetry}>Coba lagi</button></aside>}
    <p className="ft-context-note">{selector ? 'Konteks yang diminta dicocokkan dengan respons API. Bukan revisi immutable.' : 'Tanpa selector: metadata observasi terbaru pada respons API. Bukan snapshot historis.'}</p>
    <dl className="ft-summary" aria-label="Ringkasan sumber data">
      <Field label="Indikator terpilih">{reading?.indicatorName ?? data?.summary?.name ?? code}</Field>
      <Field label="Nilai observasi"><span className="ft-value">{formatDecimal(reading?.value)}</span><span className="ft-value-unit">{reading?.unit ?? 'Satuan belum tersedia'}</span><span className="ft-value-period">{reading?.period ?? 'Periode belum tersedia'}</span></Field>
      <Field label="Tipe kalkulasi">Belum diklasifikasikan API</Field>
      <Field label="Institusi sumber">{reading?.source?.institution}</Field>
      <Field label="Status dari backend">{reading?.validationStatus}</Field>
    </dl>
    <section className="ft-flow-section" aria-labelledby="ft-flow-title"><div className="fd-section-head"><h2 id="ft-flow-title">Alur keterlacakan data</h2><span>HUBUNGAN METADATA</span></div><p className="fd-small">Alur ini menggambarkan keterkaitan informasi, bukan tanda bahwa ingestion, validasi, kalkulasi, atau analisis sudah dijalankan.</p><ol className="ft-flow">{stages.map(([label, value], index) => <li key={label}><span>{String(index + 1).padStart(2, '0')} / {label}</span><p>{value ?? 'Belum tersedia'}</p></li>)}</ol></section>
    <div className="fd-columns"><div>
      <section className="fd-section ft-calculation"><p className="fd-kicker">METODE / INPUT / HASIL</p><h2>Komponen perhitungan.</h2><div className="ft-formula"><p className="fd-kicker">FORMULA MATEMATIKA</p><p>Formula belum tersedia.</p><span>API belum menyediakan ekspresi, versi metode, dan pengikatan input untuk angka ini.</span></div>
        <dl className="fd-metadata fd-metadata-row"><Field label="ID formula">Belum tersedia</Field><Field label="Versi metode">Belum tersedia</Field><Field label="Jenis data backend">{reading?.dataType}</Field></dl>
        <div className="fd-table-scroll" role="region" aria-label="Input deterministik yang disediakan backend" tabIndex={0}><table className="ft-table"><caption>Tabel input deterministik</caption><thead><tr><th scope="col">Parameter</th><th scope="col">Periode</th><th scope="col">Nilai</th><th scope="col">Satuan</th><th scope="col">Sumber</th><th scope="col">Status</th></tr></thead><tbody><tr><td colSpan={6}>Input perhitungan belum disediakan backend. Data hilang bukan nol.</td></tr></tbody></table></div>
        <dl className="fd-metadata fd-metadata-row"><Field label="Hasil perhitungan presisi">Belum tersedia</Field><Field label="Aturan pembulatan">Belum tersedia</Field><Field label="Hasil kalkulasi backend">Belum tersedia</Field></dl>
        <p className="fd-body-copy">Nilai observasi pada ringkasan tidak otomatis merupakan hasil kalkulasi DEKSI. Frontend tidak menghitung ulang pertumbuhan, rasio, atau hasil ekonomi agar bagian ini terlihat lengkap.</p>
      </section>
      <section className="fd-section"><p className="fd-kicker">RIWAYAT / BUKAN ASUMSI VERSI</p><h2>Riwayat revisi.</h2><p className="fd-body-copy">Riwayat revisi belum tersedia. API mengirim histori observasi, bukan jurnal perubahan untuk observasi yang sama. Tidak ada nomor versi atau timestamp revisi yang direka.</p></section>
      <section className="fd-section"><h2>Observasi yang tersedia.</h2><p className="fd-small">Hanya konteks yang dapat dicocokkan secara unik. Daftar ini dapat terbatas dan bukan seluruh histori atau jurnal revisi.</p>{data?.options.length ? <div className="fd-table-scroll" role="region" aria-label="Pilihan konteks observasi sumber" tabIndex={0}><table className="ft-table"><caption>Periode berbeda, bukan revisi angka</caption><thead><tr><th scope="col">Periode</th><th scope="col">Nilai</th><th scope="col">Satuan</th><th scope="col">Sumber</th><th scope="col">Konteks</th></tr></thead><tbody>{data.options.map(option => <tr key={option.guard}><th scope="row">{option.reading.period}</th><td>{formatDecimal(option.reading.value)}</td><td>{option.reading.unit}</td><td>{option.reading.source?.sourceId}</td><td><a href={contextHref(option.reading, option.guard, true)}>Lihat sumber<span className="fd-sr-only"> untuk {option.reading.period}</span> ↗</a></td></tr>)}</tbody></table></div> : <p className="fd-body-copy">Konteks observasi rinci belum tersedia.</p>}</section>
    </div><aside className="fd-aside" aria-label="Metadata sumber, rilis, dan transparansi">
      <section className="fd-section"><p className="fd-kicker">DOKUMEN & WAKTU</p><h2>Metadata rilis dan sumber.</h2><dl className="fd-metadata"><Field label="Dokumen sumber primer">{reading?.rawFile?.documentName}</Field><Field label="Nama sumber / dataset">{reading?.source?.sourceName}</Field><Field label="Periode observasi">{reading?.period}</Field><Field label="Tanggal observasi">{reading?.observationDate}</Field><Field label="Tanggal rilis">{reading?.publicationDate ? `${reading.publicationDate} (tanggal saja)` : null}</Field><Field label="Waktu akuisisi RAW">{reading?.rawFile?.retrievedAt}</Field><Field label="Frekuensi sumber">{reading?.frequency}</Field><Field label="ID sumber">{reading?.source?.sourceId}</Field><Field label="Waktu review pada respons">{reading?.reviewedAt}</Field></dl><div className="fd-links"><SourceLink url={reading?.rawFile?.sourceUrl}>Buka dokumen sumber</SourceLink><SourceLink url={reading?.source?.primaryUrl}>Buka portal institusi</SourceLink></div><h3>Referensi publikasi tambahan</h3><p className="fd-small">Daftar referensi terstruktur belum disediakan API. URL institusi tidak dipakai sebagai pengganti publikasi tertentu.</p></section>
      <section className="fd-section"><p className="fd-kicker">RAW / INTEGRITAS BERKAS</p><h2>Jejak dokumen.</h2><dl className="fd-metadata"><Field label="Checksum SHA-256">{reading?.rawFile?.checksumSha256}</Field><Field label="Ukuran berkas (byte)">{reading?.rawFile?.fileSizeBytes == null ? null : String(reading.rawFile.fileSizeBytes)}</Field><Field label="ID observasi / revisi">Belum disediakan API</Field></dl>{downloadHref ? <a className="fd-button" href={downloadHref} target="_blank" rel="noopener noreferrer">Unduh RAW dari API ↗</a> : <p className="fd-small">Tautan unduhan RAW belum tersedia atau tidak cocok dengan indikator.</p>}<p className="fd-small">Checksum mengidentifikasi byte berkas, bukan verifikasi kebenaran angka atau identitas snapshot. Metadata RAW kosong tidak disalin dari observasi lain.</p></section>
      <section className="fd-source-panel"><p className="fd-kicker">BATAS KETERLACAKAN</p><h2>Transparansi data.</h2><p>Status dari backend tidak disamakan dengan klaim “tervalidasi resmi”. Nilai resmi, metrik turunan, interpretasi, dan narasi AI merupakan hal berbeda.</p><p className="fd-small">Catatan rekonsiliasi statistik dan bukti versi terikat belum tersedia. Kecocokan konteks respons bukan jaminan snapshot immutable.</p></section>
    </aside></div>
    <div className="ft-actions">{returnHref ? <a className="fd-button" href={returnHref}>← Kembali ke Detail Indikator</a> : <p className="fd-small">Tautan kembali ke detail dinonaktifkan karena konteks yang sama belum dapat dipastikan.</p>}<a className="fd-button" href="/">Kembali ke dashboard</a></div>
  </main></FeatureShell>
}

export function SourceTraceScreen({ route }: { route: Extract<Route, { kind: 'detail' | 'source' }> }) {
  const state = useDetailData(route)
  useEffect(() => { document.title = 'Source Trace Data · DEKSI' }, [])
  return <SourceTracePage code={route.code} selector={route.selector} {...state} />
}
