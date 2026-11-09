import { useRef, useState } from 'react'
import { chartGeometry, contextHref, formatDecimal } from '../indicators/data'
import type { HistoryPoint } from '../indicators/types'
import { useHistory, useTraceOptions } from './hooks'
import { codes, names, pointMatches, visibleHistory } from './model'

export default function DashboardTrend({ year, allowedCodes }: {year:string;allowedCodes:string[]}) {
  const [requested,setRequested]=useState('pdb')
  const code=allowedCodes.includes(requested)?requested:allowedCodes[0]??'pdb'
  const [granularity,setGranularity]=useState('native')
  const [range,setRange]=useState('5')
  const [selection,setSelection]=useState<{key:string;index:number}|null>(null)
  const [exportStatus,setExportStatus]=useState('')
  const history=useHistory(code,granularity)
  const trace=useTraceOptions(code)
  const rows=visibleHistory(history.data?.points??[],year,range)
  const key=JSON.stringify([code,granularity,range,year,rows])
  const index=selection?.key===key?Math.min(selection.index,rows.length-1):rows.length-1
  const selected=rows[index]??null
  const chart=chartGeometry(rows,rows[0]?.unit??'')
  const points=useRef<(SVGCircleElement|null)[]>([])
  const matches=selected?trace.data?.options.filter(o=>pointMatches(selected,o.reading))??[]:[]
  const bound=matches.length===1?matches[0]:null
  const href=bound?contextHref(bound.reading,bound.guard,true):null
  function selectPoint(i:number,focus=false) {
    if(i<0||i>=rows.length)return
    setSelection({key,index:i})
    if(focus)requestAnimationFrame(()=>points.current[i]?.focus())
  }
  function exportRows() {
    const data={indicatorCode:code,year:year||null,range,granularity,syntheticOrOfficial:'unassessed',immutableSnapshot:false,points:rows,selectedSourceContext:bound?.reading??null}
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}))
    const link=document.createElement('a');link.href=url;link.download=`deksi-${code}-${year||'histori'}.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)
    setExportStatus('JSON berisi baris yang sama dengan tabel, bukan klaim snapshot immutable.')
  }
  const frequencies=[['native','Periode asli'],['Kuartalan','Kuartalan'],['Bulanan','Bulanan'],['Tahunan','Tahunan']]
  const supported=history.data?.granularities??[]
  const status=history.loading?'Memuat histori…':history.error?history.error:rows.length===0?'Belum ada histori untuk pilihan ini.':chart===null?'Seri tidak sebanding. Garis tidak digabungkan; nilai asli tetap ada di tabel.':!chart.points.length?'Nilai histori belum tersedia. Data kosong bukan nol.':null
  function rowGeometry(row:HistoryPoint,i:number) {
    if(!chart)return null
    return chart.points.find(p=>p.period===row.period&&p.value===row.value&&Math.abs(p.x-(rows.length===1?418:120+i*596/(rows.length-1)))<0.01)
  }
  return <section className="dash-trend dash-ink" id="economic-trend" aria-labelledby="trend-heading" aria-busy={history.loading}>
    <div className="dash-container">
      <div className="dash-eyebrow"><span>03 / DERET WAKTU</span><span>BACA PERIODE, BUKAN HANYA ARAH</span></div>
      <div className="dash-trend-heading"><h2 id="trend-heading" className="dash-display">Ekonomi,<br/>dalam gerak.</h2><div className="dash-selected-value"><p>{names[code]}</p><strong id="chart-current-value">{formatDecimal(selected?.value)}</strong><p id="chart-current-period">{selected?.period??'Periode belum tersedia'}{selected?.unit?` · ${selected.unit}`:''}</p><span className="dash-chip">{selected?.dataType??'Jenis data belum tersedia'}</span></div></div>
      <div className="dash-controls">
        <div className="dash-control-group"><span className="dash-kicker" id="series-label">INDIKATOR</span><div className="dash-pills" role="group" aria-labelledby="series-label">{codes.filter(c=>allowedCodes.includes(c)).map(c=><button key={c} type="button" aria-pressed={code===c} onClick={()=>{setRequested(c);setGranularity('native')}}>{names[c]}</button>)}</div></div>
        <div className="dash-control-group"><span className="dash-kicker" id="frequency-label">PERIODE PENAYANGAN</span><div className="dash-pills" role="group" aria-labelledby="frequency-label">{frequencies.map(([value,label])=><button key={value} type="button" aria-pressed={granularity===value} disabled={value!=='native'&&!supported.includes(value)} title={value!=='native'&&!supported.includes(value)?'Tidak ditawarkan backend untuk seri ini':undefined} onClick={()=>setGranularity(value)}>{label}</button>)}</div></div>
        <div className="dash-control-group"><span className="dash-kicker" id="range-label">RENTANG</span><div className="dash-pills" role="group" aria-labelledby="range-label">{['3','5','10','all'].map(value=><button key={value} type="button" aria-pressed={range===value} onClick={()=>setRange(value)}>{value==='all'?'Semua':value+' tahun'}</button>)}</div></div>
      </div>
      <div className="dash-chart-toolbar"><p>Satuan: {rows[0]?.unit??'Belum tersedia'}{year?` · Tahun ${year}`:''}</p><button type="button" className="dash-text-button" disabled={!rows.length||history.loading||!!history.error} onClick={exportRows}>Ekspor JSON ↓</button></div>
      <p id="chart-description" className="dash-chart-description">Gunakan panah kiri/kanan, Home dan End pada titik grafik. Tabel dan ekspor mempertahankan string presisi API. Rentang mengikuti tanggal observasi terakhir, bukan tanggal hari ini.</p>
      <div className="dash-chart-shell">{status?<div className="dash-chart-empty" role={history.error?'alert':'status'}><h3>{status}</h3>{history.error&&<button className="dash-pill" onClick={history.retry}>Coba histori lagi</button>}</div>:<svg id="trend-svg" viewBox="0 0 760 244" role="group" aria-label={`Grafik histori ${names[code]}`} aria-describedby="chart-description">
        {chart?.ticks.map(tick=><g key={tick.y}><line className="dash-grid" x1="120" x2="716" y1={tick.y} y2={tick.y}/><text x="108" y={tick.y+4} textAnchor="end">{tick.label}</text></g>)}
        {chart?.segments.map((points,i)=><polyline key={i} className="dash-line" points={points}/>)}
        {rows.map((row,i)=>{const point=rowGeometry(row,i);return point?<circle key={i} ref={el=>{points.current[i]=el}} cx={point.x} cy={point.y} r="6" className="dash-point" role="button" tabIndex={i===index?0:-1} aria-pressed={i===index} aria-label={`${row.period}: ${formatDecimal(row.value)} ${row.unit}`} onClick={()=>selectPoint(i)} onFocus={()=>selectPoint(i)} onKeyDown={event=>{
          let next=i
          if(event.key==='ArrowLeft')next=Math.max(0,i-1)
          else if(event.key==='ArrowRight')next=Math.min(rows.length-1,i+1)
          else if(event.key==='Home')next=0
          else if(event.key==='End')next=rows.length-1
          else if(event.key==='Enter'||event.key===' '){event.preventDefault();selectPoint(i);return}
          else return
          event.preventDefault();while(next>=0&&next<rows.length&&!rowGeometry(rows[next],next))next+=next>i?1:-1
          if(next>=0&&next<rows.length)selectPoint(next,true)
        }}><title>{row.period}: {formatDecimal(row.value)} {row.unit}</title></circle>:null})}
        <text x="120" y="230">{rows[0]?.period}</text><text x="716" y="230" textAnchor="end">{rows.at(-1)?.period}</text>
      </svg>}</div>
      <div className="dash-point-panel" aria-live="polite"><div><span className="dash-kicker">OBSERVASI TERPILIH</span><strong>{selected?.period??'Belum tersedia'}</strong><small>{selected?.observationDate??'Tanggal belum tersedia'}</small></div><div><span className="dash-kicker">NILAI / SATUAN</span><strong>{formatDecimal(selected?.value)} {selected?.unit??''}</strong></div><div><span className="dash-kicker">JENIS / SUMBER</span><strong>{selected?.dataType??'Belum tersedia'}</strong><small>{selected?.sourceId??'Sumber belum tersedia'}</small></div></div>
      <p className="dash-chart-note">{history.data?.note} Geometri menggunakan pendekatan numerik. Tidak ada target kebijakan atau rata-rata rentang buatan. Garis diputus pada gap kalender yang dikenali; seri sumber, satuan, frekuensi dan jenis data berbeda tidak digabungkan.</p>
      <div className="dash-chart-actions">{href?<a className="dash-text-button" href={href}>Source Trace titik terpilih ↗</a>:<p className="dash-chart-description">{trace.loading?'Memuat konteks sumber…':'Source Trace belum dapat diikat unik pada titik ini; tidak dialihkan ke terbaru.'}{trace.error&&<button type="button" className="dash-text-button" onClick={trace.retry}>Coba sumber lagi</button>}</p>}<a className="dash-text-button" href={'/indikator/'+code}>Detail indikator ↗</a></div>
      <details className="dash-history"><summary>Tabel histori ({rows.length} observasi)</summary><div className="dash-table-scroll" role="region" tabIndex={0} aria-label="Tabel histori"><table><caption>Periode observasi, bukan jurnal revisi immutable</caption><thead><tr><th>Periode</th><th>Nilai</th><th>Satuan</th><th>Sumber / jenis</th></tr></thead><tbody>{rows.map((row,i)=><tr key={i}><th scope="row"><button type="button" className="dash-text-button" onClick={()=>selectPoint(i)}>{row.period}</button></th><td>{formatDecimal(row.value)}</td><td>{row.unit}</td><td>{row.sourceId??'Belum tersedia'} / {row.dataType??'Belum tersedia'}</td></tr>)}</tbody></table></div></details>
      <p role="status" className="dash-chart-description">{exportStatus}</p>
    </div>
  </section>
}
