import { useRef, useState } from 'react'
import type { Gdp } from './economicEngineClient'
import { createPublicEngineAIRequest, getPublicEngineAIRequest, matchesMetricBindings, quarterLabel, type PublicEngineAIRequest } from './publicEngineAIClient'
import './public-engine-ai.css'

function narrativeText(value: unknown): string {
  if (typeof value === 'string') return value
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return Object.entries(value as Record<string, unknown>).filter(([, text]) => typeof text === 'string')
      .map(([label, text]) => `${label}: ${text}`).join('\n\n')
  }
  return ''
}

const labels: Record<string, string> = {
  queued: 'Menunggu antrean', running: 'Sedang diproses', ready: 'Menunggu review Admin',
  failed: 'Proses gagal', unknown: 'Hasil proses belum dapat dipastikan', approved: 'Disetujui Admin',
  rejected: 'Ditolak Admin', stale: 'Data berubah; narasi tidak lagi sesuai',
}

export function PublicEngineAIRequest({ data }: { data: Gdp }) {
  const available = Object.values(data.metrics).filter(metric => metric.available)
  const quarter = available[0]?.inputs.pdb_nominal.observationDate
  const [request, setRequest] = useState<PublicEngineAIRequest | null>(null)
  const keyRef = useRef<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const periodKey = available.map(metric => `${metric.id}:${metric.period}:${metric.inputDigest}:${metric.resultDigest}`).join('|')
  const matchesCurrent = request !== null && request.period === (quarter ? quarterLabel(quarter) : '') && periodKey.length > 0
  const approvedText = request?.status === 'approved' && matchesCurrent && matchesMetricBindings(request.metricsBinding, data) ? narrativeText(request.narrative) : ''

  async function submit() {
    if (!quarter || busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      let result = await createPublicEngineAIRequest(quarter, fetch, undefined, () => {
        keyRef.current = crypto.randomUUID()
        return keyRef.current
      }, keyRef.current ?? undefined)
      setRequest(result)
      if (result.status === 'approved') result = await getPublicEngineAIRequest(result.requestKey)
      setRequest(result)
      setNotice(result.status === 'approved' ? 'Menampilkan penjelasan tersimpan untuk versi data ini.'
        : 'Permintaan tersimpan. Penjelasan baru ditampilkan setelah proses dan review Admin selesai.')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Permintaan narasi gagal.') }
    finally { setBusy(false) }
  }

  async function refresh() {
    if (!request || busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await getPublicEngineAIRequest(request.requestKey)
      if (result.period !== quarterLabel(quarter ?? '')) {
        setRequest({ ...result, status: 'stale' })
        setNotice('Periode narasi berbeda dari perhitungan yang tampil. Narasi disembunyikan.')
      } else {
        setRequest(result)
        setNotice('Status tersimpan diperiksa ulang. Perhitungan tetap tersedia.')
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Status permintaan tidak dapat diperiksa.') }
    finally { setBusy(false) }
  }

  return <article className="engine-public-ai" aria-labelledby="engine-public-ai-title">
    <div className="engine-public-ai__heading"><div><p className="engine-eyebrow">PERMINTAAN PUBLIK · REVIEW SEBELUM PUBLIKASI</p>
      <h3 id="engine-public-ai-title">Penjelasan Economic Engine</h3></div>
      {request && <span className="engine-public-ai__status">{labels[request.status]}</span>}</div>
    <p className="engine-meta">Angka dihitung backend. Narasi hanya diminta setelah tombol ditekan dan hanya ditampilkan setelah disetujui Admin. Memuat halaman tidak memanggil provider.</p>
    {!quarter && <p className="engine-feedback" role="status">Narasi belum dapat diminta karena periode atau metrik yang memenuhi syarat tidak tersedia.</p>}
    {quarter && !request && <button className="engine-button" type="button" disabled={busy} onClick={() => void submit()}>
      {busy ? 'Memeriksa penjelasan…' : 'Lihat penjelasan sederhana'}</button>}
    {request && !approvedText && <div className="engine-public-ai__result" aria-live="polite">
      <p>{labels[request.status] ?? 'Status belum diketahui'}</p>
      {request.status === 'ready' && <p>Narasi tersedia dan menunggu persetujuan manusia. Teks belum ditampilkan untuk publik.</p>}
      {request.status === 'approved' && <p>Status persetujuan diterima; ambil ulang narasi tersimpan untuk memverifikasi snapshot.</p>}
      {request.status === 'rejected' && <p>Narasi tidak disetujui untuk publikasi.</p>}
      {request.status === 'stale' && <p>Hasil lama disembunyikan karena snapshot data berubah.</p>}
      <button className="engine-button" type="button" disabled={busy} onClick={() => void refresh()}>{busy ? 'Memeriksa…' : 'Periksa status tersimpan'}</button>
    </div>}
    {approvedText && <div className="engine-public-ai__narrative"><h4>Narasi yang disetujui</h4><p>{approvedText}</p><p className="engine-meta">Periode {request?.period} · Narasi ditinjau Admin, bukan statistik resmi atau pengganti angka.</p></div>}
    {notice && <p className="engine-public-ai__notice" role="status">{notice}</p>}
    {error && <div className="engine-feedback" role="alert"><p>{error}</p>{request && <button className="engine-button" type="button" disabled={busy} onClick={() => void refresh()}>Periksa status sebelum tindakan lain</button>}</div>}
  </article>
}
