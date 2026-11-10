import { useEffect, useRef, useState } from 'react'
import { fetchActiveAdminResync, fetchAdminResyncJob, requestAdminBpsResync, type AdminResyncJob } from '../../api'
import './resync-action.css'

type Props = { sourceId: string; sourceName: string; active: boolean; supported: boolean }
type Phase = 'idle' | 'submitting' | 'accepted' | 'uncertain'
const labels: Record<string, string> = { queued: 'Antrean', running: 'Berlangsung; worker belum tentu masih aktif', success: 'Berhasil', failed: 'Gagal', cancelled: 'Dibatalkan', unknown: 'Tidak diketahui — bukan sukses atau gagal' }

export default function ResyncAction({ sourceId, sourceName, active, supported }: Props) {
  const busy = useRef(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [job, setJob] = useState<AdminResyncJob | null>(null)
  const [message, setMessage] = useState('')
  const [historyChecked, setHistoryChecked] = useState(false)
  const [checking, setChecking] = useState(true)
  const available = sourceId === 'BPS' && active && supported

  useEffect(() => {
    let current = true
    if (!available) { setChecking(false); return () => { current = false } }
    setChecking(true)
    fetchActiveAdminResync(sourceId).then(found => {
      if (!current) return
      if (found) { setJob(found); setPhase('accepted') }
      else { setJob(null); setPhase('idle') }
    }).catch(() => {
      if (current) { setPhase('uncertain'); setMessage('Status antrean tidak dapat diperiksa. Muat ulang sebelum melanjutkan.') }
    }).finally(() => { if (current) setChecking(false) })
    return () => { current = false }
  }, [available, sourceId])

  async function submit() {
    if (!available || checking || !historyChecked || busy.current || phase !== 'idle') return
    if (!window.confirm(`Kirim permintaan sinkronisasi BPS untuk ${sourceName}?`)) return
    busy.current = true
    setPhase('submitting')
    setMessage('')
    try {
      const accepted = await requestAdminBpsResync(sourceId, crypto.randomUUID())
      const current = await fetchAdminResyncJob(accepted.id).catch(() => null)
      if (!current) {
        setPhase('uncertain')
        setMessage(`Permintaan diterima (${accepted.id}), tetapi status terbaru belum tersedia. Periksa riwayat; jangan kirim ulang.`)
      } else {
        setJob(current)
        setPhase('accepted')
      }
    } catch {
      setPhase('uncertain')
      setMessage('Hasil permintaan tidak diketahui. Periksa antrean dan riwayat sebelum tindakan lain.')
    } finally {
      busy.current = false
    }
  }

  async function refresh() {
    if (!job || busy.current) return
    busy.current = true
    try { setJob(await fetchAdminResyncJob(job.id)); setMessage('') }
    catch { setMessage('Status tidak dapat dimuat. Periksa sesi dan coba muat ulang status.') }
    finally { busy.current = false }
  }

  return <section className="resync-action" aria-label={`Sinkronisasi ${sourceName}`}>
    <button className="resync-action__button" type="button" onClick={() => void submit()} disabled={!available || checking || !historyChecked || phase !== 'idle'} aria-busy={phase === 'submitting' || checking}>
      {phase === 'submitting' ? 'Mengirim…' : `Sinkronkan ${sourceName}`}
    </button>
    {!available && <p className="resync-action__message" role="status">{sourceId !== 'BPS' ? 'Resinkronisasi hanya tersedia untuk sumber BPS.' : !active ? 'Sumber tidak aktif; sinkronisasi tidak tersedia.' : !supported ? 'Metode sumber ini belum didukung.' : ''}</p>}
    {available && checking && <p className="resync-action__message" role="status">Memeriksa antrean…</p>}
    {available && phase === 'idle' && <label className="resync-action__message"><input type="checkbox" checked={historyChecked} onChange={event => setHistoryChecked(event.target.checked)} /> Saya sudah memeriksa riwayat BPS dan memastikan tidak ada permintaan belum terselesaikan.</label>}
    {phase === 'submitting' && <p className="resync-action__message" role="status">Mengirim permintaan…</p>}
    {phase === 'uncertain' && <p className="resync-action__message" role="alert">{message} Tidak ada pengiriman ulang otomatis.</p>}
    {phase === 'accepted' && job && <div className="resync-action__message" role="status">
      <p>Status server: {labels[job.status] ?? 'Tidak tersedia'} · ID: {job.id}</p>
      {job.message && <p>{job.message}</p>}
      <button type="button" onClick={() => void refresh()}>Perbarui status</button>
    </div>}
    {message && phase !== 'uncertain' && <p className="resync-action__message" role="alert">{message}</p>}
  </section>
}
