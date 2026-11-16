import { useCallback, useEffect, useRef, useState } from 'react'
import { CandidateReviewError, fetchReviewCandidate, fetchReviewCandidates, submitCandidateReview, type CandidatePage, type ReviewCandidate } from '../../api'
import { safeExternalUrl } from '../indicators/data'
import './candidate-review.css'

type Decision = 'publish' | 'reject'

// Only candidate IDs are retained; the marker is not an authorization or a server lock.
const transientUncertain = new Map<string, number[]>()

const uncertainKey = (sourceId: string) => `deksi-review-uncertain:${encodeURIComponent(sourceId)}`
function readUncertain(sourceId: string): { ids: number[]; stored: boolean } {
  if (typeof window === 'undefined') return { ids: [], stored: false }
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(uncertainKey(sourceId)) || '[]')
    if (!Array.isArray(parsed) || !parsed.every(id => Number.isSafeInteger(id) && id > 0)) throw new Error('invalid session marker')
    return { ids: [...new Set([...parsed, ...(transientUncertain.get(sourceId) || [])])], stored: true }
  } catch {
    return { ids: transientUncertain.get(sourceId) || [], stored: false }
  }
}
function writeUncertain(sourceId: string, ids: number[]): boolean {
  transientUncertain.set(sourceId, ids)
  try {
    if (ids.length) {
      const serialized = JSON.stringify(ids)
      window.sessionStorage.setItem(uncertainKey(sourceId), serialized)
      if (window.sessionStorage.getItem(uncertainKey(sourceId)) !== serialized) throw new Error('session readback failed')
    } else window.sessionStorage.removeItem(uncertainKey(sourceId))
    transientUncertain.delete(sourceId)
    return true
  } catch { return false }
}

export default function CandidateReview({ sourceId, onClose, onBusyChange }: { sourceId: string; onClose: () => void; onBusyChange: (busy: boolean) => void }) {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'pending' | 'published' | 'rejected'>('pending')
  const [result, setResult] = useState<CandidatePage | null>(null)
  const [selected, setSelected] = useState<ReviewCandidate | null>(null)
  const [decision, setDecision] = useState<Decision | null>(null)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [initialUncertain] = useState(() => readUncertain(sourceId))
  const [initialReadOk] = useState(initialUncertain.stored)
  const [uncertain, setUncertain] = useState(initialUncertain.ids)
  const [stored, setStored] = useState(initialUncertain.stored)
  const [acknowledged, setAcknowledged] = useState(false)
  const [sourceChecked, setSourceChecked] = useState(false)
  const uncertainRef = useRef(initialUncertain.ids)

  const submission = useRef(false)
  const queryKey = JSON.stringify([sourceId, page, status, reload])
  const [previousQuery, setPreviousQuery] = useState(queryKey)
  if (previousQuery !== queryKey) {
    setPreviousQuery(queryKey)
    setLoading(true); setError(null); setResult(null); setSelected(null); setDecision(null)
  }

  useEffect(() => {
    let active = true
    fetchReviewCandidates(sourceId, page, status).then(data => {
      if (active) setResult(data)
    }).catch((error: unknown) => {
      if (active) setError(error instanceof CandidateReviewError ? error.message : 'Kandidat tidak dapat dimuat. Periksa sesi, izin, atau koneksi.')
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [sourceId, page, status, reload])

  const refresh = useCallback(() => setReload(n => n + 1), [])
  const markUncertain = (id: number, value: boolean) => {
    const ids = uncertainRef.current.filter(item => item !== id)
    if (value) ids.push(id)
    const persisted = writeUncertain(sourceId, ids)
    if (value && !persisted) {
      transientUncertain.set(sourceId, uncertainRef.current)
      setStored(false)
      return false
    }
    uncertainRef.current = ids
    setUncertain(ids)
    setStored(persisted)
    return persisted
  }
  const submit = async () => {
    if (!selected || !decision || !initialReadOk || submission.current || uncertainRef.current.includes(selected.id) || (decision === 'reject' && !notes.trim()) || (decision === 'publish' && !sourceChecked)) return
    const id = selected.id
    const currentMarkers = readUncertain(sourceId)
    if (!currentMarkers.stored) {
      setActionError('Penyimpanan sesi tidak tersedia. Keputusan tidak dikirim. Aktifkan penyimpanan browser dan coba lagi setelah memeriksa riwayat.')
      return
    }
    uncertainRef.current = [...new Set([...uncertainRef.current, ...currentMarkers.ids])]
    setUncertain(uncertainRef.current)
    if (uncertainRef.current.includes(id)) {
      setDecision(null)
      setActionError('Keputusan sebelumnya belum pasti. Periksa riwayat sebelum melanjutkan.')
      return
    }
    // Do not dispatch if a same-tab reload could erase the in-flight warning.
    if (!markUncertain(id, true)) {
      setActionError('Penyimpanan sesi tidak tersedia. Keputusan tidak dikirim. Aktifkan penyimpanan browser dan coba lagi setelah memeriksa riwayat.')
      return
    }
    submission.current = true
    onBusyChange(true)
    setBusy(true); setError(null); setActionError(null); setMessage(null)
    let accepted = false
    let definiteFailure: string | null = null
    try {
      await submitCandidateReview(sourceId, selected, decision, notes.trim())
      accepted = true
    } catch (error) {
      definiteFailure = error instanceof CandidateReviewError ? error.message : null
      setActionError(definiteFailure ?? 'Hasil review belum dapat dipastikan. Status menunggu tidak menjamin proses server sudah selesai; periksa riwayat sebelum mencoba lagi.')
    }
    try {
      const current = await fetchReviewCandidate(sourceId, id)
      if (current.status === 'published' || current.status === 'rejected') markUncertain(id, false)
      setMessage(`Status kandidat #${id} saat diperiksa: ${current.status}. ${accepted ? 'Respons review diterima.' : 'Pastikan riwayat sebelum mengambil tindakan lain.'}`)
    } catch {
      if (accepted) markUncertain(id, true)
      setActionError(accepted ? 'Keputusan diterima, tetapi status kandidat gagal dimuat ulang. Periksa sebelum melanjutkan.' : definiteFailure ? `${definiteFailure} Status kandidat belum dapat dimuat ulang.` : 'Hasil dan status review belum dapat dipastikan. Proses server mungkin masih berjalan; periksa riwayat sebelum mencoba lagi.')
    } finally {
      submission.current = false
      onBusyChange(false)
      setBusy(false); setSelected(null); setDecision(null); setNotes(''); setSourceChecked(false)
      // Reload is a read, never a repeated mutation.
      setReload(n => n + 1)
    }
  }
  const recheckUncertain = async (allowRetry: boolean) => {
    if (!selected || !initialReadOk || submission.current || (allowRetry && !acknowledged)) return
    submission.current = true
    onBusyChange(true); setBusy(true); setActionError(null)
    try {
      const current = await fetchReviewCandidate(sourceId, selected.id)
      setSelected(current)
      const terminal = current.status === 'published' || current.status === 'rejected'
      setMessage(`Status saat ini: ${current.status}. ${current.status === 'pending' ? 'Status ini tidak membuktikan proses sebelumnya sudah selesai.' : terminal ? 'Status terminal berhasil dibaca.' : 'Status ini belum dapat dipastikan.'}`)
      if (terminal || (current.status === 'pending' && allowRetry)) {
        markUncertain(current.id, false)
        setAcknowledged(false)
      }
    } catch {
      setActionError('Status kandidat belum dapat dipastikan. Pemeriksaan tidak membuka keputusan ulang.')
    } finally {
      submission.current = false
      onBusyChange(false); setBusy(false)
    }
  }
  const unavailable = (value: string | null | undefined) => value || 'Tidak tersedia'
  return <section className="trace-panel candidate-review" aria-label={`Kandidat ${sourceId}`}>
    <header className="candidate-review__header">
      <div>
        <h3 className="trace-title">Kandidat sumber {sourceId}</h3>
        <p className="trace-note">Periksa nilai, satuan, periode dan sumber resmi sebelum keputusan. Kandidat yang menunggu review belum menjadi data publik. Tautan sumber bukan bukti angka telah diverifikasi.</p>
      </div>
      <div className="candidate-review__header-actions">
        <button type="button" className="tab" onClick={refresh} disabled={loading || busy}>Muat ulang</button>
        <button type="button" className="tab" onClick={onClose} disabled={busy}>Tutup kandidat</button>
      </div>
    </header>
    <div className="candidate-review__toolbar">
      <label className="candidate-review__filter">Status kandidat <select value={status} disabled={busy} onChange={event => { setStatus(event.target.value as typeof status); setPage(1) }}>
        <option value="pending">Menunggu review</option><option value="published">Dipublikasikan</option><option value="rejected">Ditolak</option>
      </select></label>
      {result && <p className="candidate-review__count">{result.total} kandidat · Halaman {result.page}</p>}
    </div>
    {loading && <p role="status">Memuat kandidat…</p>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
    {actionError && <p role="alert">{actionError}</p>}
    {!initialReadOk && <p role="alert">Penanda keputusan sebelumnya tidak dapat dibaca. Keputusan diblokir; periksa penyimpanan browser dan riwayat, lalu tutup dan buka kembali panel ini.</p>}
    {result && <>
      {result.items.length === 0 ? <p className="candidate-review__empty">Tidak ada kandidat pada halaman ini.</p> : <ul className="candidate-review__list">
        {result.items.map(item => <li key={item.id}>
          <button type="button" className="candidate-review__item" aria-pressed={selected?.id === item.id} disabled={busy} onClick={() => { setSelected(item); setDecision(null); setNotes(''); setAcknowledged(false); setSourceChecked(false) }}>
            <span className="candidate-review__item-name">{item.indicatorName}</span>{' '}
            <span className="candidate-review__item-meta">{unavailable(item.period)} · #{item.id}</span>{' '}
            <span className="candidate-review__item-value">{unavailable(item.value)} {unavailable(item.unit)}</span>
          </button>
        </li>)}
      </ul>}
      <div className="candidate-review__pagination">
        <button type="button" className="tab" disabled={page <= 1 || busy} onClick={() => setPage(n => n - 1)}>Sebelumnya</button>
        <button type="button" className="tab" disabled={!result.hasNext || busy} onClick={() => setPage(n => n + 1)}>Berikutnya</button>
      </div>
    </>}
    {selected && <article className="trace-panel candidate-review__detail" aria-label={`Detail kandidat ${selected.id}`}>
      <h4>{selected.indicatorName} · {unavailable(selected.period)} · #{selected.id}</h4>
      <dl>
        <dt>Nilai dan satuan</dt><dd>{unavailable(selected.value)} {unavailable(selected.unit)}</dd>
        <dt>Observasi sebelumnya pada basis kandidat</dt><dd>{selected.previousValue == null ? 'Tidak tersedia' : `${selected.previousValue} ${unavailable(selected.previousUnit)} · ${unavailable(selected.previousPeriod)}`}</dd>
        <dt>Sumber saat kandidat dibuat</dt><dd>{unavailable(selected.sourceName)}</dd>
        <dt>Portal saat kandidat dibuat</dt><dd>{safeExternalUrl(selected.sourceUrl) ? <a href={safeExternalUrl(selected.sourceUrl) ?? undefined} target="_blank" rel="noopener noreferrer">Buka portal sumber</a> : 'Tidak tersedia'}</dd>
        <dt>Periode observasi</dt><dd>{unavailable(selected.period)}</dd>
        <dt>Tanggal observasi</dt><dd>{unavailable(selected.observationDate)}</dd>
        <dt>Tanggal rilis</dt><dd>{unavailable(selected.publicationDate)}</dd>
        <dt>Frekuensi / jenis data</dt><dd>{unavailable(selected.frequency)} / {unavailable(selected.dataType)}</dd>
        <dt>Dokumen RAW</dt><dd>{selected.rawFileId == null ? 'Tidak tersedia' : `ID ${selected.rawFileId}`}</dd>
        <dt>Nama dokumen tersimpan</dt><dd>{unavailable(selected.rawEvidence?.documentName)}</dd>
        <dt>Periode dokumen</dt><dd>{unavailable(selected.rawEvidence?.periodLabel)}</dd>
        <dt>Waktu pengambilan dokumen</dt><dd>{unavailable(selected.rawEvidence?.retrievedAt)}</dd>
        <dt>Checksum dokumen</dt><dd>{unavailable(selected.rawEvidence?.checksumSha256)}</dd>
        <dt>Waktu kandidat dibuat</dt><dd>{unavailable(selected.createdAt)}</dd>
        <dt>Status</dt><dd>{selected.status}</dd>
      <dt>Direview oleh / waktu</dt><dd>{unavailable(selected.reviewedBy)} / {unavailable(selected.reviewedAt)}</dd>
      <dt>Catatan review</dt><dd>{unavailable(selected.reviewNotes)}</dd>
      </dl>
      <p>Pastikan angka dan konteksnya sesuai sumber resmi. Tanggal observasi bukan tanggal rilis.</p>
      <p>Metadata dokumen di atas adalah snapshot saat kandidat dibuat, bukan bukti bahwa angka telah diverifikasi. Jika tidak tersedia, periksa sumber resmi secara terpisah.</p>
      {initialReadOk && selected.status === 'pending' && uncertain.includes(selected.id) && <div className="candidate-review__warning" role="alert">
        <p>Keputusan sebelumnya belum pasti. Status pending tidak membuktikan proses server selesai. Periksa status dan riwayat bersama pengelola sebelum keputusan ulang.</p>
        <p>Peringatan ini bukan kunci server dan tidak menjamin perlindungan pada tab atau perangkat lain.</p>
        {!stored && <p>Peringatan hanya tersimpan di halaman ini; penyimpanan sesi tidak tersedia. Setelah memuat ulang, periksa kandidat secara manual.</p>}
        <button type="button" className="tab" disabled={busy} onClick={() => void recheckUncertain(false)}>Periksa status kandidat</button>
        <label><input type="checkbox" checked={acknowledged} disabled={busy} onChange={event => setAcknowledged(event.target.checked)} /> Saya telah memeriksa riwayat dan memahami bahwa proses sebelumnya mungkin masih berjalan.</label>
        <button type="button" className="tab" disabled={busy || !acknowledged} onClick={() => void recheckUncertain(true)}>Izinkan keputusan ulang</button>
      </div>}
      {initialReadOk && selected.status === 'pending' && !uncertain.includes(selected.id) && !decision && <div className="candidate-review__decision-actions">
        <button type="button" className="tab" disabled={busy} onClick={() => setDecision('publish')}>Setujui untuk publikasi</button>{' '}
        <button type="button" className="tab" disabled={busy} onClick={() => setDecision('reject')}>Tolak kandidat</button>
      </div>}
      {decision && <div className="candidate-review__confirmation">
        <p>Konfirmasi {decision === 'publish' ? 'publikasi' : 'penolakan'} kandidat #{selected.id}: {selected.indicatorName}, {unavailable(selected.period)}, {unavailable(selected.value)} {unavailable(selected.unit)}.</p>
        {decision === 'publish' && <label className="candidate-review__source-check"><input type="checkbox" checked={sourceChecked} disabled={busy} onChange={event => setSourceChecked(event.target.checked)} /> Saya telah membandingkan indikator, nilai, satuan dan periode dengan sumber resmi.</label>}
        {decision === 'reject' && <label>Alasan penolakan <textarea value={notes} maxLength={500} onChange={event => setNotes(event.target.value)} /></label>}
        <button type="button" className="tab" disabled={busy || (decision === 'reject' && !notes.trim()) || (decision === 'publish' && !sourceChecked)} onClick={() => void submit()}>{busy ? 'Memproses…' : 'Ya, konfirmasi'}</button>{' '}
        <button type="button" className="tab" disabled={busy} onClick={() => { setDecision(null); setSourceChecked(false) }}>Batal</button>
      </div>}
    </article>}
  </section>
}
