import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { LoadSyncHistory, SyncHistoryQuery, SyncHistoryResult, SyncStatus } from './types'
import './sync-history.css'

type Props = { loadHistory?: LoadSyncHistory }
type State = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: SyncHistoryResult }
type Settled = { query: SyncHistoryQuery; retry: number; loader: LoadSyncHistory; state: State }
const statusLabels: Record<SyncStatus, string> = { running: 'Berlangsung', success: 'Berhasil', failed: 'Gagal' }
const safeErrors = new Set([
  'Sesi admin telah berakhir atau diperlukan. Silakan masuk kembali.',
  'Anda tidak berwenang melihat riwayat sinkronisasi.',
  'Gagal memuat riwayat sinkronisasi.',
  'Waktu tunggu pemuatan riwayat sinkronisasi habis. Silakan coba lagi.',
  'Koneksi ke layanan riwayat sinkronisasi bermasalah. Silakan coba lagi.',
])

function dateText(value: string | null): string {
  if (!value || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) return 'Tidak tersedia'
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  const calendar = new Date(0)
  calendar.setUTCFullYear(year, month - 1, day)
  if (calendar.getUTCFullYear() !== year || calendar.getUTCMonth() !== month - 1 || calendar.getUTCDate() !== day) return 'Tidak tersedia'
  return value
}

export default function SyncHistoryPage({ loadHistory }: Props = {}) {
  const [query, setQuery] = useState<SyncHistoryQuery>({ page: 1, pageSize: 20 })
  const [draftSource, setDraftSource] = useState('')
  const [retry, setRetry] = useState(0)
  const [settled, setSettled] = useState<Settled | null>(null)
  const state: State = settled && settled.query === query && settled.retry === retry && settled.loader === loadHistory ? settled.state : { kind: 'loading' }

  useEffect(() => {
    if (!loadHistory) return
    const controller = new AbortController()
    Promise.resolve().then(() => controller.signal.aborted ? null : loadHistory(query, { signal: controller.signal })).then(
      data => { if (!controller.signal.aborted && data) setSettled({ query, retry, loader: loadHistory, state: { kind: 'ready', data } }) },
      error => { if (!controller.signal.aborted) setSettled({ query, retry, loader: loadHistory, state: { kind: 'error', message: error instanceof Error && safeErrors.has(error.message) ? error.message : 'Periksa koneksi dan coba lagi.' } }) },
    )
    return () => controller.abort()
  }, [loadHistory, query, retry])

  function submitSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const sourceId = draftSource.trim()
    setQuery(current => ({ ...current, sourceId: sourceId || undefined, page: 1 }))
  }

  const connectedState = !loadHistory ? 'disconnected' : state.kind
  return (
    <main className="sync-history" aria-labelledby="sync-history-title">
      <header className="sync-history__header">
        <div>
          <p className="sync-history__eyebrow">DEKSI / AREA ADMIN</p>
          <h1 id="sync-history-title">Riwayat Sinkronisasi</h1>
          <p className="sync-history__intro">
            Pantau proses pengambilan data dari sumber. Riwayat ini terpisah dari perubahan
            konfigurasi sumber dan publikasi observasi.
          </p>
          <a className="sync-history__back" href="/admin/sumber">Kelola Sumber Data</a>
        </div>
        <span className="sync-history__badge">Admin DEKSI</span>
      </header>

      <section className="sync-history__panel" aria-labelledby="sync-list-title">
        <div className="sync-history__panel-header">
          <div>
            <p className="sync-history__eyebrow">LOG SISTEM / SINKRONISASI</p>
            <h2 id="sync-list-title">Aktivitas sinkronisasi</h2>
          </div>
          <span className="sync-history__connection">{!loadHistory ? 'Belum terhubung' : state.kind === 'loading' ? 'Memuat' : state.kind === 'error' ? 'Tidak tersedia' : 'Data dimuat'}</span>
        </div>
        {loadHistory && <form className="sync-history__filters" onSubmit={submitSource}>
          <label htmlFor="sync-source">ID sumber<input id="sync-source" value={draftSource} onChange={event => setDraftSource(event.target.value)} /></label>
          <button type="submit">Terapkan sumber</button>
          <label htmlFor="sync-status">Status<select id="sync-status" value={query.status ?? ''} onChange={event => setQuery(current => ({ ...current, status: (event.target.value || undefined) as SyncStatus | undefined, page: 1 }))}>
            <option value="">Semua status</option><option value="running">Berlangsung</option><option value="success">Berhasil</option><option value="failed">Gagal</option>
          </select></label>
        </form>}
        <div className="sync-history__table-wrap" role="region" aria-label="Tabel riwayat sinkronisasi" tabIndex={0}>
          <table className="sync-history__table">
            <caption>Riwayat proses sinkronisasi</caption>
            <thead>
              <tr><th scope="col">Waktu mulai</th><th scope="col">Sumber</th><th scope="col">Status</th><th scope="col">Waktu selesai</th><th scope="col">Pelaku</th><th scope="col">Jumlah item</th><th scope="col">Keterangan</th></tr>
            </thead>
            <tbody>
              {connectedState !== 'ready' || state.kind !== 'ready' || state.data.items.length === 0 ? <tr><td colSpan={7}>
                <div className="sync-history__placeholder" role="status">
                  <span className="sync-history__mark" aria-hidden="true">↗</span>
                  <div>
                    <h3>{connectedState === 'disconnected' ? 'Riwayat belum terhubung' : connectedState === 'loading' ? 'Memuat riwayat' : connectedState === 'error' ? 'Riwayat tidak dapat dimuat' : 'Belum ada riwayat'}</h3>
                    <p>{connectedState === 'disconnected' ? 'Data akan ditampilkan setelah layanan riwayat terhubung.' : connectedState === 'error' ? (state.kind === 'error' ? state.message : 'Periksa koneksi dan coba lagi.') : connectedState === 'ready' ? 'Tidak ada riwayat untuk pilihan ini.' : 'Mohon tunggu.'}</p>
                    {connectedState === 'error' && <button type="button" onClick={() => setRetry(value => value + 1)}>Coba lagi</button>}
                  </div>
                </div>
              </td></tr> : state.data.items.map(item => <tr className="sync-history__row" key={item.id}>
                <td>{dateText(item.startedAt)}</td><td>{item.sourceName || 'Tidak tersedia'}<span className="sync-history__subtext">ID: {item.sourceId || 'Tidak tersedia'}</span></td>
                <td>{statusLabels[item.status] ?? 'Tidak tersedia'}{item.status === 'running' && <span className="sync-history__subtext">Hasil akhir belum tercatat; proses belum tentu masih aktif.</span>}</td>
                <td>{dateText(item.finishedAt)}</td><td>{item.actor ?? 'Tidak tersedia'}</td><td>{item.itemCount ?? 'Tidak tersedia'}</td><td>
                  {item.message ?? 'Tidak tersedia'}
                  {item.status === 'failed' && <details><summary>Detail kegagalan</summary>
                    <p>Sumber: {item.sourceName || 'Tidak tersedia'} ({item.sourceId || 'Tidak tersedia'})</p>
                    <p>Mulai: {dateText(item.startedAt)} · Selesai: {dateText(item.finishedAt)}</p>
                    <p>{item.message ?? 'Penyebab rinci tidak tersedia.'}</p>
                  </details>}
                </td>
              </tr>)}
            </tbody>
          </table>
        </div>
        {loadHistory && state.kind === 'ready' && <nav className="sync-history__pagination" aria-label="Halaman riwayat">
          <button type="button" disabled={query.page <= 1} onClick={() => setQuery(current => ({ ...current, page: current.page - 1 }))}>Sebelumnya</button>
          <span>Halaman {state.data.pagination.page} · {state.data.pagination.total} catatan</span>
          <button type="button" disabled={!state.data.pagination.hasNext} onClick={() => setQuery(current => ({ ...current, page: current.page + 1 }))}>Berikutnya</button>
        </nav>}
        <p className="sync-history__note">
          Catatan lama yang jenisnya tidak diketahui tidak dilabeli sebagai sinkronisasi tanpa informasi yang cukup.
        </p>
      </section>

      <section className="sync-history__legend" aria-labelledby="sync-status-title">
        <div>
          <p className="sync-history__eyebrow">PANDUAN MEMBACA</p>
          <h2 id="sync-status-title">Arti status</h2>
          <p>Status berikut adalah penjelasan tampilan, bukan status proses saat ini.</p>
        </div>
        <dl className="sync-history__definitions">
          <div><dt><span className="sync-history__dot sync-history__dot--running" />Berlangsung</dt><dd>Proses telah dimulai, tetapi hasil akhir belum tercatat. Ini tidak memastikan proses masih aktif.</dd></div>
          <div><dt><span className="sync-history__dot sync-history__dot--success" />Berhasil</dt><dd>Proses pengambilan data selesai sesuai ketentuan. Bukan tanda data sudah direview atau dipublikasikan.</dd></div>
          <div><dt><span className="sync-history__dot sync-history__dot--failed" />Gagal</dt><dd>Proses berakhir dengan kegagalan yang tercatat.</dd></div>
        </dl>
      </section>
    </main>
  )
}
