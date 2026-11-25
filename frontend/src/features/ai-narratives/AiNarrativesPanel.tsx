import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchNarrativeCapabilities, fetchNarrativeDraft, fetchNarrativeDrafts, fetchNarrativeObservations,
  lookupNarrativeRequest, NarrativeApiError, reconcileNarrativeDraft, requestNarrativeDraft, reviewNarrativeDraft,
} from './api'
import type { NarrativeCapabilities, NarrativeDecision, NarrativeDraft, NarrativeObservation } from './types'
import './ai-narratives.css'

const safeMessages = {
  capabilities: 'Hak akses narasi tidak dapat dipastikan. Bagian ini dikunci.',
  read: 'Data draft atau observasi tidak dapat dimuat.',
  request: 'Hasil permintaan belum dapat dipastikan. Gunakan kunci permintaan yang sama untuk memeriksa kembali.',
  review: 'Keputusan belum dapat dipastikan. Periksa kembali detail dan digest draft.',
  reconcile: 'Rekonsiliasi belum dapat dipastikan. Periksa detail draft.',
}
const generationLabels: Record<NarrativeDraft['generationStatus'], string> = {
  queued: 'Dalam antrean', running: 'Sedang diproses', ready: 'Draft siap', failed: 'Generasi gagal', unknown: 'Status belum diketahui',
}
const reviewLabels: Record<NarrativeDraft['reviewStatus'], string> = {
  pending: 'Menunggu review', approved: 'Disetujui — belum tampil publik', needs_revision: 'Perlu revisi', rejected: 'Ditolak',
}
const formatObservation = (item: NarrativeObservation) => `#${item.id} · ${item.period} · ${item.value} ${item.unit} · observasi ${item.observationDate}`
type UncertainAction = { kind: 'review'; id: number; digest: string; decision: NarrativeDecision } | { kind: 'reconcile'; id: number }

export function NarrativeText({ value }: { value: string }) {
  return <p>{value}</p>
}

export default function AiNarrativesPanel({ onUnsettledChange }: { onUnsettledChange?: (unsettled: boolean) => void }) {
  const [capabilities, setCapabilities] = useState<NarrativeCapabilities | null>(null)
  const [observations, setObservations] = useState<NarrativeObservation[]>([])
  const [observationPage, setObservationPage] = useState(1)
  const [observationHasNext, setObservationHasNext] = useState(false)
  const [drafts, setDrafts] = useState<NarrativeDraft[]>([])
  const [draftPage, setDraftPage] = useState(1)
  const [draftHasNext, setDraftHasNext] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<NarrativeDraft | null>(null)
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [comparisonId, setComparisonId] = useState<number | null>(null)
  const [parentId, setParentId] = useState<number | null>(null)
  const [pendingKey, setPendingKey] = useState<string | null>(null)
  const [pendingInput, setPendingInput] = useState<{ observationId: number; comparisonId: number | null; parentId: number | null } | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [reviewNotes, setReviewNotes] = useState('')
  const [reconcileNotes, setReconcileNotes] = useState('')
  const [reviewBusy, setReviewBusy] = useState(false)
  const [uncertainAction, setUncertainAction] = useState<UncertainAction | null>(null)
  const selectedRef = useRef(selectedId)
  const selectDraft = useCallback((id: number | null) => {
    selectedRef.current = id
    setSelectedId(id); setDetail(null); setReviewNotes(''); setReconcileNotes('')
  }, [])
  const blocked = busy || reviewBusy || pendingKey !== null || uncertainAction !== null
  const canGenerate = capabilities?.canRead === true && capabilities.canGenerate && capabilities.generationConfigured
  useEffect(() => { onUnsettledChange?.(blocked) }, [blocked, onUnsettledChange])
  useEffect(() => () => onUnsettledChange?.(false), [onUnsettledChange])

  const loadObservations = useCallback(async (page: number) => {
    try {
      const result = await fetchNarrativeObservations(page)
      setObservations(result.items); setObservationPage(result.page); setObservationHasNext(result.hasNext); setMessage(null)
    } catch { setMessage(safeMessages.read) }
  }, [])
  const loadDrafts = useCallback(async (page: number) => {
    try {
      const result = await fetchNarrativeDrafts(page)
      setDrafts(result.items); setDraftPage(result.page); setDraftHasNext(result.hasNext)
    } catch { setMessage(safeMessages.read) }
  }, [])

  useEffect(() => {
    let active = true
    fetchNarrativeCapabilities().then(value => {
      if (!active) return
      setCapabilities(value)
      if (value.canRead) {
        void fetchNarrativeObservations(1).then(result => {
          if (active) { setObservations(result.items); setObservationPage(result.page); setObservationHasNext(result.hasNext) }
        }).catch(() => { if (active) setMessage(safeMessages.read) })
        void fetchNarrativeDrafts(1).then(result => {
          if (active) { setDrafts(result.items); setDraftPage(result.page); setDraftHasNext(result.hasNext) }
        }).catch(() => { if (active) setMessage(safeMessages.read) })
      }
    }).catch(() => { if (active) { setCapabilities(null); setMessage(safeMessages.capabilities) } })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let active = true
    fetchNarrativeDraft(selectedId).then(result => {
      if (active && result.draft.id === selectedId) setDetail(result.draft)
    }).catch(() => { if (active) setMessage(safeMessages.read) })
    return () => { active = false }
  }, [selectedId])

  async function resolveRequest(key: string) {
    setBusy(true); setMessage(null)
    try {
      const found = await lookupNarrativeRequest(key)
      if (!found.draft) { setMessage(safeMessages.request); return }
      const exact = await fetchNarrativeDraft(found.draft.id)
      if (exact.draft.requestKey !== key || exact.draft.id !== found.draft.id) { setMessage(safeMessages.request); return }
      selectDraft(exact.draft.id); setDetail(exact.draft); setPendingKey(null); setPendingInput(null); setParentId(null)
      setMessage(exact.draft.generationStatus === 'queued'
        ? 'Permintaan diterima dalam antrean. Pemrosesan memerlukan operator runner; status antrean bukan bukti AI sedang berjalan.'
        : null)
      await loadDrafts(draftPage)
    } catch { setMessage(safeMessages.request) }
    finally { setBusy(false) }
  }

  async function refresh() {
    if (blocked || !capabilities?.canRead) return
    await Promise.all([loadObservations(observationPage), loadDrafts(draftPage)])
    if (selectedId !== null) {
      try { const result = await fetchNarrativeDraft(selectedId); if (selectedRef.current === selectedId) setDetail(result.draft) }
      catch { setMessage(safeMessages.read) }
    }
  }

  async function submitRequest() {
    if (!canGenerate || blocked || currentId === null || !window.crypto?.randomUUID) return
    const key = window.crypto.randomUUID()
    const input = { observationId: currentId, comparisonId, parentId }
    setPendingKey(key); setPendingInput(input); setBusy(true); setMessage(null)
    try { await requestNarrativeDraft({ requestKey: key, ...input }) } catch { /* Check the same key; never submit a replacement automatically. */ }
    finally { setBusy(false) }
    await resolveRequest(key)
  }

  async function readAction(action: UncertainAction, rejectionMessage: string | null = null) {
    setReviewBusy(true)
    try {
      const { draft } = await fetchNarrativeDraft(action.id)
      setDetail(draft)
      const confirmed = action.kind === 'review'
        ? draft.contentDigest === action.digest && draft.review?.contentDigest === action.digest
        : draft.generationStatus === 'unknown' && draft.reconciledAt !== null && !draft.active
      if (confirmed) {
        setUncertainAction(null)
        setMessage(action.kind === 'review'
          ? draft.review?.decision === action.decision
            ? 'Keputusan tersimpan pada versi ini; draft belum tampil publik.'
            : 'Versi ini sudah memiliki keputusan yang berbeda. Periksa keputusan tersimpan; draft belum tampil publik.'
          : 'Slot sudah dilepas setelah pemeriksaan. Generasi tidak dijalankan ulang.')
      } else {
        if (rejectionMessage) setUncertainAction(null)
        setMessage(rejectionMessage ?? safeMessages.review)
      }
    } catch {
      if (rejectionMessage) setUncertainAction(null)
      setMessage(rejectionMessage ? `${rejectionMessage} Detail terbaru belum dapat dimuat.` : safeMessages.review)
    } finally { setReviewBusy(false) }
  }

  async function review(decision: NarrativeDecision) {
    if (!detail || !capabilities?.canReview || !detail.contentDigest || blocked || (decision !== 'approved' && !reviewNotes.trim())) return
    const action: UncertainAction = { kind: 'review', id: detail.id, digest: detail.contentDigest, decision }
    setUncertainAction(action); setReviewBusy(true); setMessage(null)
    let rejectionMessage: string | null = null
    try { await reviewNarrativeDraft(detail.id, { contentDigest: action.digest, decision, notes: reviewNotes }) }
    catch (error) { if (error instanceof NarrativeApiError && [400, 401, 403, 409].includes(error.status)) rejectionMessage = error.message }
    await readAction(action, rejectionMessage)
    await loadDrafts(draftPage)
  }

  async function reconcile() {
    if (!detail || detail.generationStatus !== 'unknown' || !capabilities?.canGenerate || !reconcileNotes.trim() || blocked) return
    const action: UncertainAction = { kind: 'reconcile', id: detail.id }
    setUncertainAction(action); setReviewBusy(true); setMessage(null)
    let rejectionMessage: string | null = null
    try { await reconcileNarrativeDraft(detail.id, { acknowledged: true, notes: reconcileNotes }) }
    catch (error) { if (error instanceof NarrativeApiError && [400, 401, 403, 409].includes(error.status)) rejectionMessage = error.message }
    await readAction(action, rejectionMessage)
    await loadDrafts(draftPage)
  }

  const option = (item: NarrativeObservation) => <option key={item.id} value={item.id}>{formatObservation(item)}</option>
  return <section className="ai-narratives" aria-labelledby="ai-narratives-title">
    <header className="ai-narratives__header">
      <div><p className="ai-narratives__eyebrow">BATCH 2 / REVIEW NARASI</p><h2 id="ai-narratives-title">Narasi AI — draft dan review</h2></div>
      <button type="button" onClick={() => void refresh()} disabled={blocked || !capabilities?.canRead}>Muat ulang</button>
    </header>
    <p className="ai-narratives__notice">Narasi adalah penjelasan atas fakta snapshot, bukan sumber angka. Persetujuan review tidak memublikasikan draft.</p>
    {(busy || reviewBusy) && <p role="status">Tunggu hingga permintaan dan pemeriksaan hasil selesai sebelum berpindah halaman.</p>}
    {uncertainAction && !reviewBusy && <div role="alert">
      <p>Hasil tindakan belum dipastikan. Status menunggu pada satu pemeriksaan tidak membuktikan server sudah berhenti. Jangan kirim ulang.</p>
      <button type="button" disabled={busy || reviewBusy} onClick={() => void readAction(uncertainAction)}>Periksa keputusan lagi</button>
    </div>}
    {message && <p className="ai-narratives__message" role="status">{message}</p>}
    {!capabilities && <p role="status">Izin belum diketahui; akses dinonaktifkan sampai pemeriksaan berhasil.</p>}
    {capabilities && !capabilities.canRead && <p role="status">Akses baca tidak diberikan. Draft dan observasi disembunyikan.</p>}
    {capabilities?.canRead && <>
      <div className="ai-narratives__columns">
        <section aria-labelledby="ai-create-title">
          <h3 id="ai-create-title">Minta draft baru</h3>
          <p>Pilih ID observasi resmi BPS PDB. Nilai nol tetap ditampilkan sebagai teks resmi, bukan data hilang.</p>
          <label>Observasi utama<select value={currentId ?? ''} disabled={blocked || observations.length === 0} onChange={event => setCurrentId(event.target.value ? Number(event.target.value) : null)}>
            <option value="">Pilih ID observasi</option>{observations.map(option)}</select></label>
          <label>Pembanding opsional<select value={comparisonId ?? ''} disabled={blocked || observations.length === 0} onChange={event => setComparisonId(event.target.value ? Number(event.target.value) : null)}>
            <option value="">Tanpa pembanding</option>{observations.filter(item => item.id !== currentId).map(option)}</select></label>
          <div className="ai-narratives__pager"><span>Halaman observasi {observationPage}</span>
            <button type="button" disabled={blocked || observationPage <= 1} onClick={() => void loadObservations(observationPage - 1)}>Sebelumnya</button>
            <button type="button" disabled={blocked || !observationHasNext} onClick={() => void loadObservations(observationPage + 1)}>Berikutnya</button></div>
          {parentId !== null && <p>Revisi baru dari draft #{parentId}; hasil lama tetap tersimpan dan persetujuannya tidak diwariskan.</p>}
          <button type="button" disabled={!canGenerate || blocked || currentId === null || !window.crypto?.randomUUID} onClick={() => void submitRequest()}>{pendingKey ? 'Permintaan belum terselesaikan' : 'Minta draft'}</button>
          {!capabilities.generationConfigured && <p>Generasi dinonaktifkan: backend belum dikonfigurasi.</p>}
          {capabilities.generationConfigured && capabilities.canGenerate && <p>Permintaan masuk antrean; operator runner diperlukan untuk menjalankan generasi.</p>}
          {pendingKey && <div className="ai-narratives__warning" role="alert"><strong>Hasil permintaan belum dipastikan.</strong>
            <p>Kunci dan pilihan ID dipertahankan. Jangan membuat permintaan baru; pemeriksaan ulang tidak mengulang generasi.</p>
            <button type="button" disabled={busy} onClick={() => void resolveRequest(pendingKey)}>Periksa lagi dengan kunci yang sama</button>
            <p className="ai-narratives__mono">Kunci: {pendingKey} · input: #{pendingInput?.observationId}, pembanding #{pendingInput?.comparisonId ?? '—'}</p></div>}
        </section>
        <section aria-labelledby="ai-history-title"><h3 id="ai-history-title">Riwayat draft tersimpan</h3>
          {drafts.length === 0 && <p>Draf dan keputusan yang tersimpan akan muncul di sini.</p>}
          <ul className="ai-narratives__list">{drafts.map(item => <li key={item.id}><button type="button" disabled={blocked} aria-pressed={selectedId === item.id} onClick={() => selectDraft(item.id)}>
            <strong>Draft #{item.id}</strong><span>{item.factPackage.facts.current.period} · {item.factPackage.facts.current.value} {item.factPackage.facts.current.unit}</span>
            <span>{generationLabels[item.generationStatus]} · {reviewLabels[item.reviewStatus]}</span></button></li>)}</ul>
          <div className="ai-narratives__pager"><span>{drafts.length} draft · Halaman {draftPage}</span>
            <button type="button" disabled={blocked || draftPage <= 1} onClick={() => void loadDrafts(draftPage - 1)}>Sebelumnya</button>
            <button type="button" disabled={blocked || !draftHasNext} onClick={() => void loadDrafts(draftPage + 1)}>Berikutnya</button></div>
        </section>
      </div>
      {detail && detail.id === selectedId && <article className="ai-narratives__detail" aria-labelledby="ai-detail-title">
        <header><div><p className="ai-narratives__eyebrow">DRAFT #{detail.id} · parent #{detail.parentId ?? '—'}</p><h3 id="ai-detail-title">Snapshot fakta dan narasi</h3></div>
          <div><span className="ai-narratives__status">{generationLabels[detail.generationStatus]}</span> <span className="ai-narratives__status">{reviewLabels[detail.reviewStatus]}</span></div></header>
        <p>Fakta resmi di bawah berasal dari snapshot ini; angka ditampilkan dari fact package, bukan disimpulkan dari narasi.</p>
        <dl><dt>Observasi utama</dt><dd>#{detail.factPackage.facts.current.observationId} · {detail.factPackage.facts.current.indicatorName} · {detail.factPackage.facts.current.value} {detail.factPackage.facts.current.unit} · {detail.factPackage.facts.current.period}</dd>
          <dt>Tanggal observasi / rilis</dt><dd>{detail.factPackage.facts.current.observationDate} / {detail.factPackage.facts.current.publicationDate ?? 'Tidak tersedia'}</dd>
          <dt>Sumber / verifikasi</dt><dd>{detail.factPackage.facts.current.source.institution} · {detail.factPackage.facts.current.source.sourceName} · belum diperiksa secara independen · {detail.factPackage.facts.current.evidence.status}</dd>
          <dt>ID RAW (file bukti mentah) / SHA-256</dt><dd>{detail.factPackage.facts.current.evidence.rawFileId ?? 'Tidak tersedia'} / {detail.factPackage.facts.current.evidence.checksumSha256 ?? 'Tidak tersedia'}</dd>
          <dt>Pembanding</dt><dd>{detail.factPackage.facts.comparison ? `#${detail.factPackage.facts.comparison.observationId} · ${detail.factPackage.facts.comparison.value} ${detail.factPackage.facts.comparison.unit} · ${detail.factPackage.facts.comparison.period}` : 'Tidak tersedia dalam snapshot'}</dd>
          <dt>Perubahan terhitung</dt><dd>{detail.factPackage.comparisons.length ? detail.factPackage.comparisons.map(item => `${item.value} poin persentase`).join(' · ') : 'Tidak tersedia'}. Ini selisih dua angka pertumbuhan tahunan, bukan pertumbuhan dari triwulan sebelumnya.</dd>
          <dt>Digest input / konten</dt><dd className="ai-narratives__mono">{detail.inputDigest} / {detail.contentDigest ?? 'Belum tersedia'}</dd>
          <dt>Model / versi prompt-validator</dt><dd>{detail.requestedModel} / {detail.reportedModel ?? 'belum dilaporkan'} · {detail.promptVersion} / {detail.validatorVersion}</dd></dl>
        <p><strong>Data yang tidak tersedia:</strong> {detail.factPackage.missingData.length ? detail.factPackage.missingData.join(' · ') : 'Tidak ada catatan data hilang pada snapshot ini.'}</p>
        <p><strong>Batasan snapshot:</strong> {detail.factPackage.limitations.length ? detail.factPackage.limitations.join(' · ') : 'Tidak ada batasan tambahan yang dicatat.'}</p>
        {detail.generationStatus === 'queued' && <p role="status">Dalam antrean. Generasi memerlukan operator runner; antrean bukan bukti model sedang berjalan.</p>}
        {(detail.errorCode || detail.errorMessage) && <p>Generasi berstatus {generationLabels[detail.generationStatus]}. Detail teknis tidak ditampilkan.</p>}
        {detail.narrative && <section className="ai-narratives__narrative" aria-label="Teks draft narasi"><h4>Ringkasan</h4><NarrativeText value={detail.narrative.summary} />
          <h4>Makna</h4><NarrativeText value={detail.narrative.meaning} />{detail.narrative.comparison !== null && <><h4>Perbandingan</h4><NarrativeText value={detail.narrative.comparison} /></>}
          <h4>Batasan</h4><NarrativeText value={detail.narrative.limitations} />
          <p><strong>Rujukan fakta:</strong> {detail.narrative.factRefs.length ? detail.narrative.factRefs.join(' · ') : 'Tidak dicantumkan'}</p>
          <p className="ai-narratives__note">Teks ini adalah keluaran draft dan bukan sumber angka atau status verifikasi.</p></section>}
        <section aria-label="Keputusan review tersimpan"><h4>Keputusan review tersimpan</h4>
          {detail.review ? <p>{reviewLabels[detail.review.decision]} · {detail.review.reviewedAt} · {detail.review.notes || 'Tanpa catatan'} · digest {detail.review.contentDigest}</p> : <p>Belum ada keputusan review untuk versi ini.</p>}
        </section>
        {detail.generationStatus === 'ready' && detail.reviewStatus === 'pending' && capabilities.canReview && <section aria-label="Review draft"><h4>Keputusan review</h4>
          <label>Catatan (wajib untuk perlu revisi atau ditolak)<textarea value={reviewNotes} disabled={blocked} onChange={event => setReviewNotes(event.target.value)} /></label>
          <div className="ai-narratives__actions"><button type="button" disabled={blocked || !detail.contentDigest} onClick={() => void review('approved')}>Setujui draft — belum tampil publik</button>
            <button type="button" disabled={blocked || !reviewNotes.trim()} onClick={() => void review('needs_revision')}>Perlu revisi</button>
            <button type="button" disabled={blocked || !reviewNotes.trim()} onClick={() => void review('rejected')}>Tolak draft</button></div></section>}
        {detail.generationStatus === 'unknown' && capabilities.canGenerate && !detail.reconciledAt && <section className="ai-narratives__warning"><h4>Status tidak diketahui — jangan kirim ulang otomatis</h4>
          <p>Inferensi mungkin sudah terjadi. Rekonsiliasi melepas slot tidak diketahui dan tidak menjalankan generasi ulang.</p>
          <label>Catatan pemeriksaan wajib<textarea value={reconcileNotes} disabled={blocked} onChange={event => setReconcileNotes(event.target.value)} /></label>
          <button type="button" disabled={blocked || !reconcileNotes.trim()} onClick={() => void reconcile()}>Saya paham, rekonsiliasi tanpa mengulang generasi</button></section>}
        <button type="button" disabled={blocked} onClick={() => { setParentId(detail.id); setCurrentId(detail.factPackage.facts.current.observationId); setComparisonId(detail.factPackage.facts.comparison?.observationId ?? null); setMessage('ID snapshot disalin untuk permintaan revisi baru. Draft lama tidak diubah.') }}>Gunakan ID fakta ini untuk revisi baru</button>
        <p>Draft lama, snapshot, dan keputusan tetap tersimpan; revisi adalah permintaan baru dengan parent ID eksplisit.</p>
      </article>}
    </>}
  </section>
}
