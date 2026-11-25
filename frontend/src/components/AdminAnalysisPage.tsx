import { useEffect, useState } from 'react'
import { CandidateReviewError, fetchAdminAnalysisResults, type CandidatePage, type ReviewCandidate } from '../api'
import { safeExternalUrl } from '../features/indicators/data'
import { AdminNavigation } from './AdminNavigation'
import './admin-analysis.css'

type StatusFilter = 'all' | 'pending' | 'published' | 'rejected'

const statusLabels: Record<StatusFilter, string> = {
  all: 'Semua status',
  pending: 'Menunggu peninjauan',
  published: 'Layak publikasi',
  rejected: 'Ditolak',
}

function valueOrUnavailable(value: string | null | undefined): string {
  return value || 'Tidak tersedia'
}

export function AdminAnalysisPage() {
  const [status, setStatus] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)
  const [result, setResult] = useState<CandidatePage | null>(null)
  const [selected, setSelected] = useState<ReviewCandidate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    setSelected(null)
    fetchAdminAnalysisResults(page, status).then(data => {
      if (active) setResult(data)
    }).catch((reason: unknown) => {
      if (!active) return
      setError(reason instanceof CandidateReviewError || reason instanceof Error
        ? reason.message
        : 'Hasil analisis tidak dapat dimuat.')
      setResult(null)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [page, status, reload])

  const changeStatus = (value: StatusFilter) => {
    setStatus(value)
    setPage(1)
  }

  return (
    <main className="admin-analysis" aria-labelledby="admin-analysis-title">
      <header className="admin-analysis__header">
        <div>
          <p className="admin-analysis__eyebrow">AREA PENGELOLA</p>
          <h1 id="admin-analysis-title">Detail Peninjauan Hasil Analisis</h1>
          <p className="admin-analysis__intro">
            Periksa nilai resmi, periode, provenance sumber, dan status setiap versi sebelum
            menetapkan kelayakan publikasi.
          </p>
        </div>
      </header>

      <AdminNavigation active="analysis" />

      <section className="admin-analysis__panel" aria-labelledby="analysis-list-title">
        <div className="admin-analysis__panel-header">
          <div>
            <p className="admin-analysis__eyebrow">REVIEW / VERSI HASIL</p>
            <h2 id="analysis-list-title">Hasil yang tersedia</h2>
          </div>
          <label className="admin-analysis__filter">
            Status
            <select value={status} onChange={event => changeStatus(event.target.value as StatusFilter)}>
              {(Object.keys(statusLabels) as StatusFilter[]).map(value =>
                <option key={value} value={value}>{statusLabels[value]}</option>,
              )}
            </select>
          </label>
        </div>

        {loading && <p className="admin-analysis__state" role="status">Memuat hasil analisis…</p>}
        {!loading && error && (
          <div className="admin-analysis__state admin-analysis__state--error" role="alert">
            <p>{error}</p>
            <button type="button" onClick={() => setReload(value => value + 1)}>Coba lagi</button>
          </div>
        )}
        {!loading && !error && result && result.items.length === 0 && (
          <p className="admin-analysis__state" role="status">Belum ada versi hasil untuk ditinjau.</p>
        )}
        {!loading && !error && result && result.items.length > 0 && (
          <>
            <div className="admin-analysis__list" aria-label="Daftar versi hasil analisis">
              {result.items.map(item => (
                <button
                  type="button"
                  className="admin-analysis__item"
                  key={item.id}
                  aria-pressed={selected?.id === item.id}
                  onClick={() => setSelected(item)}
                >
                  <span className="admin-analysis__item-main">
                    <strong>{valueOrUnavailable(item.indicatorName)}</strong>
                    <span>{valueOrUnavailable(item.sourceName)} · {valueOrUnavailable(item.period)}</span>
                  </span>
                  <span className="admin-analysis__item-value">{valueOrUnavailable(item.value)} {valueOrUnavailable(item.unit)}</span>
                  <span className={`admin-analysis__status admin-analysis__status--${item.status}`}>
                    {statusLabels[item.status as Exclude<StatusFilter, 'all'>] ?? item.status}
                  </span>
                </button>
              ))}
            </div>
            <div className="admin-analysis__pagination">
              <span>{result.total} versi · Halaman {result.page}</span>
              <div>
                <button type="button" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>Sebelumnya</button>
                <button type="button" disabled={!result.hasNext} onClick={() => setPage(value => value + 1)}>Berikutnya</button>
              </div>
            </div>
          </>
        )}
      </section>

      {selected && (
        <section className="admin-analysis__panel admin-analysis__detail" aria-labelledby="analysis-detail-title">
          <div className="admin-analysis__panel-header">
            <div>
              <p className="admin-analysis__eyebrow">VERSI #{selected.id} · {valueOrUnavailable(selected.indicator)}</p>
              <h2 id="analysis-detail-title">{valueOrUnavailable(selected.indicatorName)} · {valueOrUnavailable(selected.period)}</h2>
            </div>
            <span className={`admin-analysis__status admin-analysis__status--${selected.status}`}>
              {statusLabels[selected.status as Exclude<StatusFilter, 'all'>] ?? selected.status}
            </span>
          </div>

          <section className="admin-analysis__section" aria-labelledby="analysis-official-title">
            <h3 id="analysis-official-title">Nilai resmi dan periode</h3>
            <dl>
              <dt>Nilai</dt><dd>{valueOrUnavailable(selected.value)} {valueOrUnavailable(selected.unit)}</dd>
              <dt>Nilai sebelumnya</dt><dd>{selected.previousValue == null ? 'Tidak tersedia' : `${selected.previousValue} ${valueOrUnavailable(selected.previousUnit)} · ${valueOrUnavailable(selected.previousPeriod)}`}</dd>
              <dt>Tanggal observasi</dt><dd>{valueOrUnavailable(selected.observationDate)}</dd>
              <dt>Tanggal rilis</dt><dd>{valueOrUnavailable(selected.publicationDate)}</dd>
              <dt>Frekuensi / jenis data</dt><dd>{valueOrUnavailable(selected.frequency)} / {valueOrUnavailable(selected.dataType)}</dd>
            </dl>
          </section>

          <section className="admin-analysis__section admin-analysis__unavailable" aria-label="Komponen analisis">
            <h3>Economic Engine</h3>
            <p>Belum tersedia untuk versi ini. Tidak ada hasil turunan yang tersimpan untuk ditinjau.</p>
            <h3>Diagnostic flags</h3>
            <p>Belum tersedia untuk versi ini. Status diagnostik tidak diasumsikan aman atau lolos.</p>
            <h3>Narasi Grounded AI</h3>
            <p>Belum tersedia untuk versi ini. Tidak ada narasi AI yang digunakan sebagai dasar peninjauan.</p>
          </section>

          <section className="admin-analysis__section" aria-labelledby="analysis-trace-title">
            <h3 id="analysis-trace-title">Source Trace dan bukti RAW</h3>
            <dl>
              <dt>ID sumber</dt><dd>{valueOrUnavailable(selected.sourceId)}</dd>
              <dt>Sumber pada versi ini</dt><dd>{valueOrUnavailable(selected.sourceName)}</dd>
              <dt>Portal sumber</dt><dd>{safeExternalUrl(selected.sourceUrl)
                ? <a href={safeExternalUrl(selected.sourceUrl) ?? undefined} target="_blank" rel="noopener noreferrer">Buka portal sumber</a>
                : 'Tidak tersedia'}</dd>
              <dt>ID dokumen RAW</dt><dd>{selected.rawFileId == null ? 'Tidak tersedia' : selected.rawFileId}</dd>
              <dt>Nama dokumen</dt><dd>{valueOrUnavailable(selected.rawEvidence?.documentName)}</dd>
              <dt>Periode dokumen</dt><dd>{valueOrUnavailable(selected.rawEvidence?.periodLabel)}</dd>
              <dt>Waktu akuisisi</dt><dd>{valueOrUnavailable(selected.rawEvidence?.retrievedAt)}</dd>
              <dt>SHA-256</dt><dd>{valueOrUnavailable(selected.rawEvidence?.checksumSha256)}</dd>
            </dl>
            <p className="admin-analysis__note">
              Source Trace dan metadata RAW adalah snapshot provenance, bukan bukti bahwa nilai
              telah diverifikasi. Tanggal observasi berbeda dari tanggal rilis.
            </p>
          </section>

          <section className="admin-analysis__section" aria-labelledby="analysis-review-title">
            <h3 id="analysis-review-title">Riwayat peninjauan</h3>
            <dl>
              <dt>Dibuat</dt><dd>{valueOrUnavailable(selected.createdAt)}</dd>
              <dt>Ditinjau oleh</dt><dd>{valueOrUnavailable(selected.reviewedBy)}</dd>
              <dt>Waktu peninjauan</dt><dd>{valueOrUnavailable(selected.reviewedAt)}</dd>
              <dt>Catatan</dt><dd>{valueOrUnavailable(selected.reviewNotes)}</dd>
            </dl>
          </section>
        </section>
      )}
    </main>
  )
}
