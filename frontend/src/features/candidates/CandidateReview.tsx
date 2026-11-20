import { useCallback, useEffect, useRef, useState } from 'react'
import { CandidateReviewError, confirmBulkReview, createBulkPreview, fetchActiveBulkReview, fetchBulkReview, fetchReviewCandidate, fetchReviewCandidates, reconcileBulkReview, submitAdminAnalysisDecision, type AnalysisDecision, type BulkPreview, type BulkReviewResult, type CandidatePage, type ReviewCandidate } from '../../api'
import { safeExternalUrl } from '../indicators/data'
import './candidate-review.css'

type Decision = AnalysisDecision

const decisionLabels: Record<Decision, string> = {
  publish: 'Layak Publikasi',
  needs_revision: 'Perlu Revisi',
  reject: 'Ditolak',
}

const bulkReasons: Record<string, string> = {
  raw_file_unavailable: 'Berkas bukti tidak tersedia',
  raw_file_invalid: 'Ukuran atau checksum bukti tidak cocok',
}
const bulkReason = (reason: string | null | undefined) => bulkReasons[reason ?? ''] ?? reason ?? 'metadata tidak tersedia'

// Only candidate IDs are retained; the marker is not an authorization or a server lock.
const transientUncertain = new Map<string, number[]>()

const uncertainKey = (sourceId: string) => `deksi-review-uncertain:${encodeURIComponent(sourceId)}`
function readUncertain(sourceId: string): { ids: number[]; stored: boolean } {
  if (typeof window === 'undefined') return { ids: [], stored: false }
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(uncertainKey(sourceId)) ?? '[]')
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
    } else {
      window.sessionStorage.removeItem(uncertainKey(sourceId))
      if (window.sessionStorage.getItem(uncertainKey(sourceId)) !== null) throw new Error('session removal failed')
    }
    transientUncertain.delete(sourceId)
    return true
  } catch { return false }
}

export default function CandidateReview({ sourceId, onClose, onBusyChange }: { sourceId: string; onClose: () => void; onBusyChange: (busy: boolean) => void }) {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<'pending' | 'published' | 'needs_revision' | 'rejected'>('pending')
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
  const [initialReadOk, setInitialReadOk] = useState(initialUncertain.stored)
  const [storageAcknowledged, setStorageAcknowledged] = useState(false)
  const [uncertain, setUncertain] = useState(initialUncertain.ids)
  const [stored, setStored] = useState(initialUncertain.stored)
  const [acknowledged, setAcknowledged] = useState(false)
  const [sourceChecked, setSourceChecked] = useState(false)
  const [bulkPreview, setBulkPreview] = useState<BulkPreview | null>(null)
  const [bulkResult, setBulkResult] = useState<BulkReviewResult | null>(null)
  const [bulkChecked, setBulkChecked] = useState(false)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [bulkLoading, setBulkLoading] = useState(true)
  const [bulkUncertain, setBulkUncertain] = useState(false)
  const [bulkError, setBulkError] = useState<string | null>(null)
  const [resolutionReason, setResolutionReason] = useState('')
  const [resolutionAcknowledged, setResolutionAcknowledged] = useState(false)
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
  useEffect(() => {
    let active = true
    fetchActiveBulkReview(sourceId).then(batch => {
      if (active) { setBulkResult(batch); setBulkUncertain(false) }
    }).catch(() => {
      if (active) { setBulkUncertain(true); setBulkError('Riwayat operasi massal tidak dapat diperiksa. Jangan memulai keputusan baru sampai statusnya diketahui.') }
    }).finally(() => { if (active) setBulkLoading(false) })
    return () => { active = false }
  }, [sourceId])
  const batchBlocksDecisions = bulkLoading || bulkUncertain || (bulkResult != null && bulkResult.status !== 'completed' && !bulkResult.resolvedAt)
  const previewBulk = async () => {
    if (!initialReadOk || uncertainRef.current.length || busy || bulkBusy || batchBlocksDecisions) return
    setBulkBusy(true); onBusyChange(true); setBulkError(null)
    try { setBulkPreview(await createBulkPreview(sourceId)); setBulkResult(null); setBulkChecked(false) }
    catch (error) { setBulkError(error instanceof CandidateReviewError ? error.message : 'Pratinjau gagal. Tidak ada publikasi dimulai. Periksa status sebelum mencoba lagi.') }
    finally { setBulkBusy(false); onBusyChange(false) }
  }
  const readBulk = async (id: string) => {
    setBulkBusy(true); onBusyChange(true); setBulkError(null)
    try {
      const current = await fetchBulkReview(sourceId, id)
      setBulkResult(current); setBulkUncertain(false)
      if (current.status === 'completed') refresh()
    } catch {
      setBulkUncertain(true)
      setBulkError('Hasil operasi belum dapat dipastikan. Jangan mengulangi konfirmasi. Periksa bersama pengelola.')
    } finally { setBulkBusy(false); onBusyChange(false) }
  }
  const submitBulk = async () => {
    if (!bulkPreview || !bulkChecked || bulkBusy || busy || batchBlocksDecisions || bulkPreview.eligible === 0) return
    const id = bulkPreview.id
    setBulkBusy(true); onBusyChange(true); setBulkError(null)
    try {
      const current = await confirmBulkReview(sourceId, id)
      setBulkResult(current); setBulkPreview(null); setBulkChecked(false)
      if (current.status === 'completed') refresh()
    } catch {
      setBulkUncertain(true)
      setBulkError('Konfirmasi mungkin sudah diproses. Jangan mengulanginya; baca status operasi di server.')
    } finally { setBulkBusy(false); onBusyChange(false) }
  }
  const reconcileBulk = async () => {
    if (!bulkResult || bulkResult.status === 'completed' || bulkResult.resolvedAt || !resolutionAcknowledged ||
        !resolutionReason.trim() || resolutionReason.trim().length > 500 || bulkBusy || busy) return
    setBulkBusy(true); onBusyChange(true); setBulkError(null)
    try {
      const current = await reconcileBulkReview(sourceId, bulkResult.id, resolutionReason)
      setBulkResult(current); setBulkPreview(null); setBulkChecked(false)
      setResolutionReason(''); setResolutionAcknowledged(false); refresh()
    } catch {
      setBulkUncertain(true)
      setBulkError('Penutupan operasi belum dapat dipastikan. Baca statusnya; jangan kirim tindakan ini ulang otomatis.')
    } finally { setBulkBusy(false); onBusyChange(false) }
  }
  const recoverStorage = () => {
    if (!storageAcknowledged || submission.current) return
    try {
      const raw = window.sessionStorage.getItem(uncertainKey(sourceId))
      let valid = raw === null
      if (raw !== null) {
        try {
          const parsed: unknown = JSON.parse(raw)
          valid = Array.isArray(parsed) && parsed.every(id => Number.isSafeInteger(id) && id > 0)
        } catch { valid = false }
      }
      // Never discard a valid marker that became readable after the failure.
      if (!valid) {
        window.sessionStorage.removeItem(uncertainKey(sourceId))
        if (window.sessionStorage.getItem(uncertainKey(sourceId)) !== null) throw new Error('removal failed')
      }
      const recovered = readUncertain(sourceId)
      if (!recovered.stored) throw new Error('storage unavailable')
      uncertainRef.current = recovered.ids
      setUncertain(recovered.ids)
      setStored(true)
      setInitialReadOk(true)
      setStorageAcknowledged(false)
      setActionError(null)
      setMessage('Penyimpanan penanda dapat digunakan kembali. Tetap periksa riwayat sebelum keputusan.')
    } catch {
      setActionError('Penyimpanan penanda belum dapat dipulihkan. Keputusan tetap diblokir.')
    }
  }
  const markUncertain = (id: number, value: boolean) => {
    const latest = readUncertain(sourceId)
    if (!latest.stored) {
      setStored(false)
      return false
    }
    const existing = [...new Set([...uncertainRef.current, ...latest.ids])]
    const ids = existing.filter(item => item !== id)
    if (value) ids.push(id)
    const persisted = writeUncertain(sourceId, ids)
    if (!persisted) {
      transientUncertain.set(sourceId, existing)
      setStored(false)
      return false
    }
    uncertainRef.current = ids
    setUncertain(ids)
    setStored(persisted)
    return persisted
  }
  const submit = async () => {
    if (!selected || !decision || !initialReadOk || submission.current || batchBlocksDecisions || bulkBusy || uncertainRef.current.includes(selected.id) || (decision !== 'publish' && !notes.trim()) || (decision === 'publish' && !sourceChecked)) return
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
      await submitAdminAnalysisDecision(selected, decision, notes.trim())
      accepted = true
    } catch (error) {
      definiteFailure = error instanceof CandidateReviewError ? error.message : null
      setActionError(definiteFailure ?? 'Hasil review belum dapat dipastikan. Status menunggu tidak menjamin proses server sudah selesai; periksa riwayat sebelum mencoba lagi.')
    }
    try {
      const current = await fetchReviewCandidate(sourceId, id)
      if ((current.status === 'published' || current.status === 'needs_revision' || current.status === 'rejected') && !markUncertain(id, false)) {
        setActionError('Status kandidat telah dibaca, tetapi penanda belum bisa diperbarui. Periksa penyimpanan sebelum melanjutkan.')
      }
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
      const terminal = current.status === 'published' || current.status === 'needs_revision' || current.status === 'rejected'
      setMessage(`Status saat ini: ${current.status}. ${current.status === 'pending' ? 'Status ini tidak membuktikan proses sebelumnya sudah selesai.' : terminal ? 'Status terminal berhasil dibaca.' : 'Status ini belum dapat dipastikan.'}`)
      if (terminal || (current.status === 'pending' && allowRetry)) {
        if (markUncertain(current.id, false)) setAcknowledged(false)
        else setActionError('Status kandidat telah dibaca, tetapi penanda belum bisa diperbarui. Periksa penyimpanan sebelum melanjutkan.')
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
        <button type="button" className="tab" onClick={refresh} disabled={loading || busy || bulkBusy}>Muat ulang</button>
        <button type="button" className="tab" onClick={onClose} disabled={busy || bulkBusy}>Tutup kandidat</button>
      </div>
    </header>
    <div className="candidate-review__toolbar">
      <label className="candidate-review__filter">Status kandidat <select value={status} disabled={busy || bulkBusy} onChange={event => { setStatus(event.target.value as typeof status); setPage(1) }}>
        <option value="pending">Menunggu review</option><option value="published">Layak publikasi</option><option value="needs_revision">Perlu revisi</option><option value="rejected">Ditolak</option>
      </select></label>
      {result && <p className="candidate-review__count">{result.total} kandidat · Halaman {result.page}</p>}
    </div>
    <div className="candidate-review__bulk">
      <p>Persetujuan massal memerlukan bukti RAW. Kandidat BPS boleh tanpa tanggal rilis; sumber lain tetap memerlukan tanggal rilis. Kandidat yang tidak lengkap tetap dapat direview satu per satu.</p>
      <button type="button" className="tab" disabled={busy || bulkBusy || batchBlocksDecisions || !initialReadOk || uncertain.length > 0 || status !== 'pending'} onClick={() => void previewBulk()}>Pratinjau kandidat yang memenuhi syarat</button>
      {bulkLoading && <p role="status">Memeriksa operasi massal sebelumnya…</p>}
      {bulkError && <p role="alert">{bulkError}</p>}
      {bulkPreview && <div className="candidate-review__bulk-preview" aria-label="Pratinjau persetujuan massal">
        <p role="status">Total pending: {bulkPreview.total}. Memenuhi syarat: {bulkPreview.eligible}. Dikecualikan: {bulkPreview.excluded}. Pratinjau berlaku hingga {bulkPreview.expiresAt}.</p>
        <p>Periksa setiap nilai, periode, satuan, sumber dan perubahan observasi sebelum konfirmasi. Pratinjau tidak mempublikasikan data.</p>
        {bulkPreview.items.some(item => item.eligible && item.sourceId === 'BPS' && item.publicationDate == null) && <p role="alert">Pengingat: sebagian kandidat BPS tidak memiliki tanggal rilis. Tanggal observasi bukan tanggal rilis; waktu data tersedia dan riwayat revisinya belum dipastikan. Periksa sumber sebelum menyetujui.</p>}
        <ol tabIndex={0} aria-label="Semua kandidat dalam snapshot">{bulkPreview.items.map(item => <li key={item.id}>
          #{item.id} · {unavailable(item.indicatorName)} · {unavailable(item.period)} · {unavailable(item.value)} {unavailable(item.unit)}
          {' · '}Sumber: {unavailable(item.sourceName)}
          {' · '}Tanggal observasi: {unavailable(item.observationDate)}
          {safeExternalUrl(item.sourceUrl) && <> · <a href={safeExternalUrl(item.sourceUrl) ?? undefined} target="_blank" rel="noopener noreferrer">Buka portal sumber</a></>}
          {' · '}Tanggal rilis: {unavailable(item.publicationDate)}
          {' · '}Dokumen RAW: {unavailable(item.rawEvidence?.documentName)} (ID {unavailable(item.rawFileId?.toString())})
          {' · '}Checksum RAW: {unavailable(item.rawEvidence?.checksumSha256)}
          {item.previousValue != null && <> · Revisi dari {item.previousValue} {unavailable(item.previousUnit)}</>}
          {' · '}{item.eligible ? 'Memenuhi syarat' : `Dikecualikan: ${bulkReason(item.exclusionReason)}`}
        </li>)}</ol>
        {bulkPreview.eligible > 0 && <label><input type="checkbox" checked={bulkChecked} disabled={bulkBusy || batchBlocksDecisions} onChange={event => setBulkChecked(event.target.checked)} /> Saya telah membandingkan seluruh kandidat yang memenuhi syarat dengan sumber resmi dan memahami bahwa konfirmasi mempublikasikannya.</label>}
        <div className="candidate-review__decision-actions">
          <button type="button" className="tab" disabled={bulkBusy || batchBlocksDecisions || !bulkChecked || bulkPreview.eligible === 0} onClick={() => void submitBulk()}>Setujui semua kandidat yang memenuhi syarat</button>
          <button type="button" className="tab" disabled={bulkBusy} onClick={() => { setBulkPreview(null); setBulkChecked(false) }}>Batal</button>
        </div>
      </div>}
      {bulkResult && <div className="candidate-review__bulk-result" aria-label="Hasil persetujuan massal">
        <p role="status">Operasi {bulkResult.status}: berhasil {bulkResult.counts.published}, dilewati {bulkResult.counts.skipped}, dikecualikan {bulkResult.counts.excluded}, belum diproses {bulkResult.counts.pending}, belum pasti {bulkResult.counts.unknown}.</p>
        {bulkResult.resolvedAt ? <p role="status">Ditinjau {bulkResult.resolvedBy} · {bulkResult.resolvedAt} · {bulkResult.resolutionReason}. Hasil yang belum pasti tetap perlu diperiksa per kandidat.</p> :
          bulkResult.status !== 'completed' && <p role="alert">Proses dapat masih berjalan atau terputus. Jangan memulai operasi lain sampai statusnya jelas.</p>}
        <ol>{bulkResult.items.map(item => <li key={item.id}>#{item.id} · {item.status}{item.reason ? ` · ${bulkReason(item.reason)}` : ''}</li>)}</ol>
        <button type="button" className="tab" disabled={bulkBusy} onClick={() => void readBulk(bulkResult.id)}>Periksa status operasi</button>
        {bulkResult.status !== 'completed' && !bulkResult.resolvedAt && <div className="candidate-review__bulk-reconcile">
          <p>Periksa hasil setiap kandidat dan pastikan tidak ada proses lama yang perlu ditunggu. Penutupan tidak mengulang publikasi; item belum pasti tetap ditandai belum pasti. Proses yang masih berjalan dibatasi sebelum item berikutnya, bukan dibatalkan di tengah item.</p>
          <label>Alasan pemeriksaan <input type="text" value={resolutionReason} maxLength={500} onChange={event => setResolutionReason(event.target.value)} /></label>
          <label><input type="checkbox" checked={resolutionAcknowledged} onChange={event => setResolutionAcknowledged(event.target.checked)} /> Saya sudah memeriksa hasil dan memahami proses sebelumnya mungkin masih berjalan.</label>
          <button type="button" className="tab" disabled={bulkBusy || busy || !resolutionAcknowledged || !resolutionReason.trim()} onClick={() => void reconcileBulk()}>Tutup operasi setelah pemeriksaan manual</button>
        </div>}
      </div>}
      {bulkUncertain && bulkPreview && <button type="button" className="tab" disabled={bulkBusy} onClick={() => void readBulk(bulkPreview.id)}>Periksa status operasi</button>}
    </div>
    {loading && <p role="status">Memuat kandidat…</p>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
    {actionError && <p role="alert">{actionError}</p>}
    {!initialReadOk && <div className="candidate-review__storage-recovery" role="alert">
      <p>Penanda keputusan sebelumnya tidak dapat dibaca. Keputusan diblokir. Pemulihan menghapus hanya penanda yang rusak; daftar keputusan yang belum pasti mungkin tidak dapat dipulihkan.</p>
      <label><input type="checkbox" checked={storageAcknowledged} onChange={event => setStorageAcknowledged(event.target.checked)} /> Saya telah memeriksa semua kandidat dan riwayat sumber, dan memahami proses sebelumnya mungkin masih berjalan.</label>{' '}
      <button type="button" className="tab" disabled={!storageAcknowledged} onClick={recoverStorage}>Pulihkan penyimpanan penanda</button>
    </div>}
    {result && <>
      {result.items.length === 0 ? <p className="candidate-review__empty">Tidak ada kandidat pada halaman ini.</p> : <ul className="candidate-review__list">
        {result.items.map(item => <li key={item.id}>
          <button type="button" className="candidate-review__item" aria-pressed={selected?.id === item.id} disabled={busy || bulkBusy} onClick={() => { setSelected(item); setDecision(null); setNotes(''); setAcknowledged(false); setSourceChecked(false) }}>
            <span className="candidate-review__item-name">{unavailable(item.indicatorName)}</span>{' '}
            <span className="candidate-review__item-meta">{unavailable(item.period)} · #{item.id}</span>{' '}
            <span className="candidate-review__item-value">{unavailable(item.value)} {unavailable(item.unit)}</span>
          </button>
        </li>)}
      </ul>}
      <div className="candidate-review__pagination">
        <button type="button" className="tab" disabled={page <= 1 || busy || bulkBusy} onClick={() => setPage(n => n - 1)}>Sebelumnya</button>
        <button type="button" className="tab" disabled={!result.hasNext || busy || bulkBusy} onClick={() => setPage(n => n + 1)}>Berikutnya</button>
      </div>
    </>}
    {selected && <article className="trace-panel candidate-review__detail" aria-label={`Detail kandidat ${selected.id}`}>
      <h4>{unavailable(selected.indicatorName)} · {unavailable(selected.period)} · #{selected.id}</h4>
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
      {selected.reviewHistory && selected.reviewHistory.length > 0 && <section aria-label="Riwayat audit keputusan">
        <h5>Riwayat keputusan</h5>
        <ol className="candidate-review__audit-list">
          {selected.reviewHistory.map((entry, index) => (
            <li key={`${entry.fingerprint}-${entry.reviewedAt}-${index}`}>
              <strong>{decisionLabels[entry.decision as Decision] ?? entry.decision}</strong>
              <span>{entry.reviewedAt} · {unavailable(entry.reviewedBy)}</span>
              <p>{entry.notes || 'Tanpa catatan.'}</p>
            </li>
          ))}
        </ol>
      </section>}
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
      {initialReadOk && !batchBlocksDecisions && selected.status === 'pending' && !uncertain.includes(selected.id) && !decision && <div className="candidate-review__decision-actions">
        {(Object.keys(decisionLabels) as Decision[]).map(value => (
          <button type="button" className="tab" disabled={busy} key={value} onClick={() => setDecision(value)}>
            {decisionLabels[value]}
          </button>
        ))}
      </div>}
      {decision && <div className="candidate-review__confirmation">
        <p>Konfirmasi keputusan “{decisionLabels[decision]}” untuk kandidat #{selected.id}: {unavailable(selected.indicatorName)}, {unavailable(selected.period)}, {unavailable(selected.value)} {unavailable(selected.unit)}.</p>
        {decision === 'publish'
          ? <p>Versi ini akan menjadi data publik setelah validasi berhasil.</p>
          : <p>Versi ini tidak dipublikasikan. Catatan wajib diisi untuk tindak lanjut.</p>}
        {decision === 'publish' && <label className="candidate-review__source-check"><input type="checkbox" checked={sourceChecked} disabled={busy} onChange={event => setSourceChecked(event.target.checked)} /> Saya telah membandingkan indikator, nilai, satuan dan periode dengan sumber resmi.</label>}
        {decision !== 'publish' && <label>Catatan keputusan <span>(wajib)</span><textarea value={notes} maxLength={500} onChange={event => setNotes(event.target.value)} /></label>}
        <button type="button" className="tab" disabled={busy || bulkBusy || batchBlocksDecisions || (decision !== 'publish' && !notes.trim()) || (decision === 'publish' && !sourceChecked)} onClick={() => void submit()}>{busy ? 'Memproses…' : 'Ya, konfirmasi'}</button>{' '}
        <button type="button" className="tab" disabled={busy} onClick={() => { setDecision(null); setSourceChecked(false) }}>Batal</button>
      </div>}
    </article>}
  </section>
}
