import { useEffect, useState } from 'react'
import type { Gdp } from './economicEngineClient'
import { fetchNarrative, type PreviewNarrative } from './engineNarrativePreviewClient'

export function EngineNarrativePreview({ data }: { data: Gdp }) {
  const [narrative, setNarrative] = useState<PreviewNarrative | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    fetchNarrative(data, controller.signal).then(value => {
      if (!controller.signal.aborted) setNarrative(value)
    }).catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [data, attempt])
  return <EngineNarrativePreviewView narrative={narrative} loading={loading} error={error}
    onRetry={() => {
      setNarrative(null); setLoading(true); setError(false); setAttempt(value => value + 1)
    }} />
}

type Props = { narrative: PreviewNarrative | null; loading: boolean; error: boolean; onRetry: () => void }

export function EngineNarrativePreviewView({ narrative, loading, error, onRetry }: Props) {
  return <article className="engine-narrative" id="engine-narrative-preview" aria-labelledby="engine-narrative-title">
    <header><div><p className="engine-eyebrow">AI MENJELASKAN · BACKEND MENGHITUNG</p>
      <h3 id="engine-narrative-title">Penjelasan Gemini</h3></div>
      <span className="engine-narrative-badge">Draft preview · Belum direview</span></header>
    <p className="engine-meta">Jawaban asli yang sudah disimpan. Membuka atau memuat ulang halaman ini tidak memanggil Gemini.</p>
    {loading && <p className="engine-feedback" role="status">Memuat penjelasan tersimpan…</p>}
    {error && <div className="engine-feedback" role="alert">
      <p>Penjelasan belum dapat dimuat atau tidak cocok dengan perhitungan ini. Angka Economic Engine tetap tersedia.</p>
      <button className="engine-button" type="button" onClick={onRetry}>Muat ulang penjelasan</button></div>}
    {!loading && !error && narrative && <>
      <p className="engine-meta">{narrative.period} · {narrative.model} · Alur review simulasi lokal, bukan publikasi.</p>
      <div className="engine-narrative-copy">
        <section><h4>Ringkasan</h4><p data-narrative-field="summary">{narrative.narrative.summary}</p></section>
        <section><h4>Artinya</h4><p data-narrative-field="meaning">{narrative.narrative.meaning}</p></section>
        <section className="engine-narrative-limitations"><h4>Batasan yang perlu dibaca</h4>
          <p data-narrative-field="limitations">{narrative.narrative.limitations}</p></section>
      </div>
      <p className="engine-meta">Tidak ada pembanding waktu. Narasi ini bukan statistik resmi, persetujuan manusia, atau nasihat investasi.</p>
    </>}
  </article>
}
