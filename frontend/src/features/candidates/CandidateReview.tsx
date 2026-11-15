import { useCallback, useEffect, useRef, useState } from 'react'
import { CandidateReviewError, fetchReviewCandidate, fetchReviewCandidates, submitCandidateReview, type CandidatePage, type ReviewCandidate } from '../../api'
import { safeExternalUrl } from '../indicators/data'

type Decision = 'publish' | 'reject'


export default function CandidateReview({ sourceId, onClose, onBusyChange }: { sourceId: string; onClose: () => void; onBusyChange: (busy: boolean) => void }) {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'pending' | 'published' | 'rejected'>('pending')
  const [result, setResult] = useState<CandidatePage | null>(null)
  const [selected, setSelected] = useState<ReviewCandidate | null>(null)
  const [decision, setDecision] = useState<Decision | null>(null)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  const submission = useRef(false)

  useEffect(() => {
    let active = true
    setLoading(true); setError(null); setResult(null); setSelected(null); setDecision(null)
    fetchReviewCandidates(sourceId, page, status).then(data => {
      if (active) setResult(data)
    }).catch(() => {
      if (active) setError('Kandidat tidak dapat dimuat. Periksa sesi, izin, atau koneksi.')
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [sourceId, page, status, reload])

  const refresh = useCallback(() => setReload(n => n + 1), [])
  const submit = async () => {
    if (!selected || !decision || submission.current || (decision === 'reject' && !notes.trim())) return
    submission.current = true
    onBusyChange(true)
    setBusy(true); setError(null); setActionError(null); setMessage(null)
    const id = selected.id
    let accepted = false
    let definiteFailure: string | null = null
    try {
      await submitCandidateReview(sourceId, selected, decision, notes.trim())
      accepted = true
    } catch (error) {
      definiteFailure = error instanceof CandidateReviewError ? error.message : null
      setActionError(definiteFailure ?? 'Hasil review belum dapat dipastikan. Periksa daftar terbaru sebelum mencoba lagi.')
    }
    try {
      const current = await fetchReviewCandidate(sourceId, id)
      setMessage(`Status kandidat #${id} saat diperiksa: ${current.status}. ${accepted ? 'Respons review diterima.' : 'Pastikan riwayat sebelum mengambil tindakan lain.'}`)
    } catch {
      setActionError(accepted ? 'Keputusan diterima, tetapi status kandidat gagal dimuat ulang. Periksa sebelum melanjutkan.' : definiteFailure ? `${definiteFailure} Status kandidat belum dapat dimuat ulang.` : 'Hasil dan status review belum dapat dipastikan. Periksa sebelum mencoba lagi.')
    } finally {
      submission.current = false
      onBusyChange(false)
      setBusy(false); setSelected(null); setDecision(null); setNotes('')
      // Reload is a read, never a repeated mutation.
      setReload(n => n + 1)
    }
  }
  const unavailable = (value: string | null | undefined) => value || 'Tidak tersedia'
  return <section className="trace-panel" aria-label={`Kandidat ${sourceId}`}>
    <h3 className="trace-title">Kandidat sumber {sourceId}</h3>
    <p className="trace-note">Periksa nilai, satuan, periode dan sumber resmi sebelum keputusan. Kandidat belum menjadi data publik. Tautan sumber bukan bukti angka telah diverifikasi.</p>
    <button type="button" className="tab" onClick={onClose} disabled={busy}>Tutup kandidat</button>{' '}
    <button type="button" className="tab" onClick={refresh} disabled={loading || busy}>Muat ulang</button>
    <label> Status kandidat <select value={status} disabled={busy} onChange={event => { setStatus(event.target.value as typeof status); setPage(1) }}>
      <option value="pending">Menunggu review</option><option value="published">Dipublikasikan</option><option value="rejected">Ditolak</option>
    </select></label>
    {loading && <p role="status">Memuat kandidat…</p>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
    {actionError && <p role="alert">{actionError}</p>}
    {result && <>
      <p>{result.total} kandidat · Halaman {result.page}</p>
      {result.items.length === 0 ? <p>Tidak ada kandidat pada halaman ini.</p> : <ul>
        {result.items.map(item => <li key={item.id}>
          <button type="button" className="source-trace-link" disabled={busy} onClick={() => { setSelected(item); setDecision(null); setNotes('') }}>
            {item.indicatorName} · {unavailable(item.period)} · {unavailable(item.value)} {unavailable(item.unit)} · #{item.id}
          </button>
        </li>)}
      </ul>}
      <button type="button" className="tab" disabled={page <= 1 || busy} onClick={() => setPage(n => n - 1)}>Sebelumnya</button>{' '}
      <button type="button" className="tab" disabled={!result.hasNext || busy} onClick={() => setPage(n => n + 1)}>Berikutnya</button>
    </>}
    {selected && <article className="trace-panel" aria-label={`Detail kandidat ${selected.id}`}>
      <h4>{selected.indicatorName} · {unavailable(selected.period)} · #{selected.id}</h4>
      <dl>
        <dt>Nilai dan satuan</dt><dd>{unavailable(selected.value)} {unavailable(selected.unit)}</dd>
        <dt>Observasi sebelumnya pada basis kandidat</dt><dd>{selected.previousValue == null ? 'Tidak tersedia' : `${selected.previousValue} ${unavailable(selected.previousUnit)} · ${unavailable(selected.previousPeriod)}`}</dd>
        <dt>Sumber</dt><dd>{selected.sourceName}</dd>
        <dt>Portal sumber</dt><dd>{safeExternalUrl(selected.sourceUrl) ? <a href={safeExternalUrl(selected.sourceUrl) ?? undefined} target="_blank" rel="noopener noreferrer">Buka portal sumber</a> : 'Tidak tersedia'}</dd>
        <dt>Periode observasi</dt><dd>{unavailable(selected.period)}</dd>
        <dt>Tanggal observasi</dt><dd>{unavailable(selected.observationDate)}</dd>
        <dt>Tanggal rilis</dt><dd>{unavailable(selected.publicationDate)}</dd>
        <dt>Frekuensi / jenis data</dt><dd>{unavailable(selected.frequency)} / {unavailable(selected.dataType)}</dd>
        <dt>Dokumen RAW</dt><dd>{selected.rawFileId == null ? 'Tidak tersedia' : `ID ${selected.rawFileId}`}</dd>
        <dt>Waktu kandidat dibuat</dt><dd>{unavailable(selected.createdAt)}</dd>
        <dt>Status</dt><dd>{selected.status}</dd>
      <dt>Direview oleh / waktu</dt><dd>{unavailable(selected.reviewedBy)} / {unavailable(selected.reviewedAt)}</dd>
      <dt>Catatan review</dt><dd>{unavailable(selected.reviewNotes)}</dd>
      </dl>
      <p>Pastikan angka dan konteksnya sesuai sumber resmi. Tanggal observasi bukan tanggal rilis.</p>
      {selected.status === 'pending' && !decision && <>
        <button type="button" className="tab" disabled={busy} onClick={() => setDecision('publish')}>Setujui untuk publikasi</button>{' '}
        <button type="button" className="tab" disabled={busy} onClick={() => setDecision('reject')}>Tolak kandidat</button>
      </>}
      {decision && <div>
        <p>Konfirmasi {decision === 'publish' ? 'publikasi' : 'penolakan'} kandidat #{selected.id}: {selected.indicatorName}, {unavailable(selected.period)}, {unavailable(selected.value)} {unavailable(selected.unit)}.</p>
        {decision === 'reject' && <label>Alasan penolakan <textarea value={notes} maxLength={500} onChange={event => setNotes(event.target.value)} /></label>}
        <button type="button" className="tab" disabled={busy || (decision === 'reject' && !notes.trim())} onClick={() => void submit()}>{busy ? 'Memproses…' : 'Ya, konfirmasi'}</button>{' '}
        <button type="button" className="tab" disabled={busy} onClick={() => setDecision(null)}>Batal</button>
      </div>}
    </article>}
  </section>
}
