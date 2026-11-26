import { useEffect, useState } from 'react'
import { AdminNavigation } from '../../components/AdminNavigation'
import { fetchPublicEngineAIReviews, submitPublicEngineAIReview, type PublicEngineAIReview } from '../dashboard/publicEngineAIClient'
import '../dashboard/public-engine-ai.css'

function readable(value: unknown): string {
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return 'Konten tidak dapat ditampilkan.' }
}

export function AdminPublicEngineAIPage() {
  const [items, setItems] = useState<PublicEngineAIReview[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true); setError(''); setNotice('')
    fetchPublicEngineAIReviews().then(result => { if (active) setItems(result) })
      .catch(reason => { if (active) { setItems([]); setError(reason instanceof Error ? reason.message : 'Daftar review gagal dimuat.') } })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])

  async function decide(item: PublicEngineAIReview, decision: 'approved' | 'rejected') {
    if (busyId !== null) return
    setBusyId(item.id); setError(''); setNotice('')
    try {
      await submitPublicEngineAIReview(item, decision, notes[item.id] ?? '')
      setNotice(decision === 'approved' ? `Narasi ${item.period} disetujui.` : `Narasi ${item.period} ditolak.`)
      setReload(value => value + 1)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Review tidak dapat dipastikan.') }
    finally { setBusyId(null) }
  }

  return <main className="admin-engine-ai" aria-labelledby="admin-engine-ai-title">
    <header><p className="admin-analysis__eyebrow">AREA PENGELOLA · REVIEW WAJIB</p><h1 id="admin-engine-ai-title">Review narasi Economic Engine AI</h1>
      <p>Bandingkan snapshot metrik dan narasi sebelum menyetujui atau menolak. Narasi belum tampil untuk publik hingga keputusan disimpan.</p></header>
    <AdminNavigation active="engine-ai" busy={busyId !== null} />
    {loading && <p role="status">Memuat narasi yang menunggu review…</p>}
    {error && <div className="admin-engine-ai__error" role="alert"><p>{error}</p><button type="button" disabled={busyId !== null} onClick={() => setReload(value => value + 1)}>Muat ulang daftar</button></div>}
    {notice && <p role="status">{notice}</p>}
    {!loading && !error && items.length === 0 && <p role="status">Tidak ada narasi yang memenuhi syarat untuk direview.</p>}
    {!loading && items.map(item => <article className="admin-engine-ai__panel" key={item.id} aria-labelledby={`engine-ai-${item.id}`}>
      <header><p className="admin-analysis__eyebrow">PERIODE · {item.period}</p><h2 id={`engine-ai-${item.id}`}>Narasi Economic Engine</h2></header>
      <section aria-label="Snapshot angka"><h3>Snapshot perhitungan</h3><pre className="admin-engine-ai__detail">{readable(item.snapshot)}</pre></section>
      <section aria-label="Narasi yang dihasilkan"><h3>Narasi</h3><pre className="admin-engine-ai__detail">{readable(item.narrative)}</pre></section>
      <p className="admin-engine-ai__digest"><strong>Digest hasil:</strong> {item.resultDigest}<br/><strong>Digest konten review:</strong> {item.contentDigest}</p>
      <details className="admin-engine-ai__snapshot"><summary>Catatan review (opsional)</summary>
        <label htmlFor={`engine-ai-notes-${item.id}`}>Catatan (maksimum 500 karakter)</label>
        <textarea id={`engine-ai-notes-${item.id}`} maxLength={500} value={notes[item.id] ?? ''}
          onChange={event => setNotes(value => ({ ...value, [item.id]: event.target.value }))} /></details>
      <div className="admin-engine-ai__actions">
        <button type="button" disabled={busyId !== null} onClick={() => void decide(item, 'approved')}>{busyId === item.id ? 'Menyimpan…' : 'Setujui publikasi'}</button>
        <button type="button" disabled={busyId !== null} onClick={() => void decide(item, 'rejected')}>{busyId === item.id ? 'Menyimpan…' : 'Tolak narasi'}</button>
      </div>
    </article>)}
  </main>
}
