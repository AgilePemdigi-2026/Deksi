import { useEffect, useRef, useState } from 'react'
import { fetchDetail, parseReading } from '../indicators/api'
import { contextGuard, contextHref, formatDecimal } from '../indicators/data'
import { fetchGdp, matchesInput } from './economicEngineClient'
import type { Gdp, Input } from './economicEngineClient'
import { EngineNarrativePreview } from './EngineNarrativePreview'
import { PublicEngineAIRequest } from './PublicEngineAIRequest'
import './economic-engine.css'

export function EconomicEngine() {
  const [data, setData] = useState<Gdp | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const [traceStatus, setTraceStatus] = useState('')
  const [navigating, setNavigating] = useState(false)
  const navigation = useRef<AbortController | null>(null)
  const reload = () => {
    navigation.current?.abort(); setNavigating(false); setTraceStatus('')
    setLoading(true); setError(false); setData(null); setAttempt(n => n + 1)
  }
  useEffect(() => () => navigation.current?.abort(), [])
  const openTrace = async (code: string, input: Input) => {
    navigation.current?.abort()
    const controller = new AbortController(); navigation.current = controller
    setNavigating(true); setTraceStatus('Memeriksa kesesuaian sumber…')
    try {
      const detail = await fetchDetail(code, null, controller.signal)
      const snapshot = parseReading(input.trace, code)
      if (!matchesInput(code, input, snapshot)) throw new Error('Konteks tidak cocok')
      const guard = await contextGuard(snapshot)
      const matches = detail.options.filter(option => option.guard === guard && matchesInput(code, input, option.reading))
      if (controller.signal.aborted) return
      if (matches.length !== 1) throw new Error('Konteks tidak cocok')
      window.location.assign(contextHref(matches[0].reading, matches[0].guard, true))
    } catch {
      if (!controller.signal.aborted) setTraceStatus('Sumber berubah, tidak tersedia, atau ambigu. Muat ulang sebelum membuka Source Trace.')
    } finally { if (!controller.signal.aborted) setNavigating(false) }
  }
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    fetchGdp(controller.signal).then(body => {
      if (active && !controller.signal.aborted) setData(body)
    }).catch(() => { if (active && !controller.signal.aborted) setError(true) })
      .finally(() => { if (active && !controller.signal.aborted) setLoading(false) })
    return () => { active = false; controller.abort() }
  }, [attempt])
  return <EconomicEngineView data={data} error={error} loading={loading} navigating={navigating}
    traceStatus={traceStatus} onRetry={reload} onOpenTrace={openTrace}
    previewNarrativeEnabled={import.meta.env.DEV && import.meta.env.VITE_ENGINE_NARRATIVE_PREVIEW === '1'} />
}

type ViewProps = { data: Gdp | null; error: boolean; loading: boolean; navigating: boolean; traceStatus: string;
  onRetry: () => void; onOpenTrace: (code: string, input: Input) => void; previewNarrativeEnabled?: boolean }

// Presentation only: keep source precision and digest inputs untouched.
function formatInput(value: string): string {
  return formatDecimal(value.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, ''))
}

export function EconomicEngineView({ data, error, loading, navigating, traceStatus, onRetry, onOpenTrace, previewNarrativeEnabled }: ViewProps) {
  return <section className="dash-paper" id="economic-engine" aria-labelledby="economic-engine-title">
    <div className="dash-container">
      <header className="engine-header">
        <div>
          <p className="engine-eyebrow">PERHITUNGAN DEKSI · DATA BPS</p>
          <h2 id="economic-engine-title">Struktur ekonomi.</h2>
          <p className="engine-intro">Melihat porsi pembentukan modal tetap dan konsumsi rumah tangga dalam total PDB (Produk Domestik Bruto).</p>
          <p className="engine-meta">Periode terbaru yang tersedia untuk PDB nominal, tidak mengikuti filter di atas. Hasil perhitungan, bukan narasi AI atau statistik resmi baru.</p>
        </div>
        {!loading && !error && <button className="engine-button" type="button" onClick={onRetry}>Perbarui perhitungan</button>}
      </header>
      {loading && <p className="engine-feedback" role="status">Memuat perhitungan…</p>}
      {error && <div className="engine-feedback" role="alert"><p>Perhitungan belum dapat dimuat.</p><button className="engine-button" type="button" onClick={onRetry}>Coba lagi</button></div>}
      {data && !Object.keys(data.metrics).length && <p className="engine-feedback" role="status">{data.reason || 'Data belum tersedia.'}</p>}
      {data && <div className="engine-grid">{Object.entries(data.metrics).map(([id, metric]) => {
        const isPmtb = id === 'pmtb_share'
        const numerator = isPmtb ? 'pmtb_nominal' : 'konsumsi_rumah_tangga'
        const name = isPmtb ? 'PMTB' : 'Konsumsi rumah tangga'
        const quarter = /^Q([1-4]) (\d{4})$/.exec(metric.period)
        const period = quarter ? `Triwulan ${['I', 'II', 'III', 'IV'][Number(quarter[1]) - 1]} ${quarter[2]}` : metric.period
        const inputs = Object.entries(metric.inputs)
        const releaseDates = [...new Set(inputs.map(([, input]) => input.publicationDate ?? 'Belum tersedia'))]
        return <article className="engine-card" key={id} aria-labelledby={`engine-${id}-title`}>
          <p className="engine-eyebrow">Perhitungan DEKSI · Data BPS</p>
          <h3 id={`engine-${id}-title`}>{metric.name}</h3>
          <p className={metric.available ? 'engine-value' : 'engine-unavailable'}>{metric.available && metric.value !== null
            ? <>{formatDecimal(metric.value)}<span className="engine-unit">{metric.unit}</span></> : 'Belum tersedia'}</p>
          <p className="engine-period">{period} · {metric.priceBasis === 'current_prices' ? 'Harga berlaku' : 'Dasar harga belum memenuhi syarat'}</p>
          <p className="engine-definition">{isPmtb
            ? 'Membandingkan nilai Pembentukan Modal Tetap Bruto (PMTB) dengan total PDB pada triwulan yang sama.'
            : 'Membandingkan nilai konsumsi rumah tangga dengan total PDB pada triwulan yang sama.'}</p>
          {metric.reason && <p className="engine-warning" role="note">{metric.reason}</p>}
          <div className="engine-formula-block">
            <h4>Cara menghitung</h4>
            <p className="engine-formula" role="math" aria-label={`${name} dibagi total PDB, dikali 100 persen`}>
              <span className="engine-fraction" aria-hidden="true"><span>{name}</span><span>Total PDB</span></span>
              <span aria-hidden="true">× 100%</span>
            </p>
          </div>
          <div className="engine-warning" role="note">
            <p>{metric.revisionNote}</p>
            <p className="engine-meta">Tanggal rilis: {releaseDates.length ? releaseDates.join(' · ') : 'Belum tersedia'}</p>
          </div>
          <details className="engine-details">
            <summary>Lihat angka pembentuk dan sumber</summary>
            {inputs.length ? <>
              <div className="engine-table-scroll" tabIndex={0} role="region" aria-label={`Angka pembentuk ${metric.name}`}>
                <table>
                  <caption>{period} · Nilai dalam miliar rupiah · {metric.priceBasis === 'current_prices' ? 'Harga berlaku' : 'Dasar harga belum memenuhi syarat'}</caption>
                  <thead><tr><th scope="col">Input</th><th scope="col">Nilai</th><th scope="col">Sumber</th></tr></thead>
                  <tbody>{inputs.map(([code, input]) => {
                    const label = code === 'pdb_nominal' ? 'Total PDB' : name
                    return <tr key={code}><th scope="row">{label}<small>{code === 'pdb_nominal' ? 'Penyebut' : 'Pembilang'}</small></th>
                      <td>{formatInput(input.value)}</td><td><button className="engine-source" data-input-code={code} type="button" disabled={navigating}
                        onClick={() => onOpenTrace(code, input)}>Source Trace {label} ↗</button></td></tr>
                  })}</tbody>
                </table>
              </div>
              <p className="engine-substitution">({formatInput(metric.inputs[numerator].value)} ÷ {formatInput(metric.inputs.pdb_nominal.value)}) × 100%
                {metric.available && <> = {formatDecimal(metric.value)}%</>}</p>
              <p className="engine-meta">Sumber input: BPS. Pembilang dan penyebut memakai periode serta satuan yang sama. Hasil dihitung oleh backend DEKSI.</p>
            </> : <p>Angka pembentuk belum tersedia atau belum memenuhi syarat perhitungan.</p>}
          </details>
          <details className="engine-details engine-audit">
            <summary>Detail teknis perhitungan</summary>
            <p>Rumus asli: <code>{metric.formula}</code></p>
            <p>Metode: <code>{metric.methodVersion}</code></p>
            <p>Identitas hasil: <code>{metric.resultDigest}</code></p>
            <p>Identitas input: <code>{metric.inputDigest}</code></p>
            {inputs.map(([code, input]) => <div className="engine-audit-input" key={code}>
              <p><code>{code}</code> · {input.sourceId} · {input.period} · {input.unit}</p>
              <p>Tanggal rilis: {input.publicationDate ?? 'Belum tersedia'}</p>
              <p>Bukti: {input.evidenceStatus === 'integrity_ok' ? 'file dan checksum cocok'
                : input.evidenceStatus === 'missing' ? 'belum tersedia' : 'file tidak tersedia atau tidak valid'}</p>
              <p>Kaitan RAW: {input.bindingStatus === 'matched' ? 'cocok dengan input terpilih'
                : input.bindingStatus === 'mismatch' ? 'isi tidak cocok dengan input terpilih' : 'belum dapat diperiksa'}.</p>
              <p>SHA-256: <code>{input.evidenceChecksumSha256 ?? 'Belum tersedia'}</code></p>
            </div>)}
            <p>{metric.note} Snapshot respons ini bukan riwayat revisi immutable.</p>
            <p>Checksum menunjukkan keutuhan file, bukan bukti kebenaran angka atau verifikasi resmi.</p>
          </details>
        </article>
      })}</div>}
      {import.meta.env.DEV && previewNarrativeEnabled && data && !loading && !error && <EngineNarrativePreview data={data}
        key={Object.values(data.metrics).map(metric => `${metric.period}:${metric.inputDigest}:${metric.resultDigest}`).join('|')} />}
      {data && !loading && !error && <PublicEngineAIRequest data={data}
        key={Object.values(data.metrics).map(metric => `${metric.period}:${metric.inputDigest}:${metric.resultDigest}`).join('|')} />}
      <p className="engine-trace-status" role="status">{traceStatus}</p>
      <article className="engine-trade"><h3>Perdagangan barang</h3><p>Belum tersedia: kesesuaian metodologi ekspor dan impor masih perlu diverifikasi.</p></article>
    </div>
  </section>
}
