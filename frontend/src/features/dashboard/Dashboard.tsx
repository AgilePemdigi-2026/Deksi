import { useEffect, useRef, useState } from 'react'
import { BrandMark } from '../../components/EditorialLanding'
import { DashboardFilter } from '../../components/DashboardFilter'
import { FeedbackForm } from '../../components/FeedbackForm'
import { fetchDetail } from '../indicators/api'
import { contextHref, formatDecimal } from '../indicators/data'
import { useDashboard } from './hooks'
import type { DashboardCard, DashboardFilters } from './client'
import { codes, names, errorMessage } from './model'
import DashboardTrend from './DashboardTrend'
import hero from '../../assets/prototype-2/hero-business.webp'
import stat from '../../assets/prototype-2/stat-market.webp'
import logistics from '../../assets/prototype-2/feature-logistics.webp'
import portrait from '../../assets/prototype-2/portrait-agriculture.webp'
import skyline from '../../assets/prototype-2/activity-skyline.webp'
import port from '../../assets/prototype-2/activity-port.webp'
import food from '../../assets/prototype-2/activity-food.webp'
import harvest from '../../assets/prototype-2/activity-harvest.webp'
import market from '../../assets/prototype-2/activity-market.webp'
import bank from '../../assets/prototype-2/activity-bank.webp'
import agriculture from '../../assets/prototype-2/activity-agriculture.webp'
import distribution from '../../assets/prototype-2/activity-distribution.webp'
import './prototype-base.css'
import './prototype-dashboard.css'
import './team-features.css'
import './dashboard.css'

const photos=[skyline,port,food,harvest,market,bank,agriculture,distribution]
function Arrow() {return <svg className="arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12"/></svg>}
function amount(card: DashboardCard|undefined) {return card?.available?formatDecimal(card.value):'Belum tersedia'}
function Card({card,index,onNavigate}:{card:DashboardCard;index:number;onNavigate:(card:DashboardCard,source?:boolean)=>void}) {
  const values=card.sparkline
  const min=values.length?Math.min(...values):0,max=values.length?Math.max(...values):0
  return <article className="dash-indicator" data-indicator={card.id}>
    <div className="dash-card-top"><p className="dash-kicker">{String(index+1).padStart(2,'0')} / {card.category||'Kategori belum tersedia'}</p><span className="dash-chip">{card.available?'TERSEDIA DI API':'BELUM TERSEDIA'}</span></div>
    <h3>{card.name||names[card.id]}</h3><p className="dash-card-value">{amount(card)}</p><p className="dash-card-period">{card.unit??'Satuan belum tersedia'} · {card.period??'Periode belum tersedia'}</p>
    {values.length>0?<svg className="dash-spark" viewBox="0 0 330 78" role="img" aria-label="Sparkline sebanding dari backend, tanpa sumbu tanggal"><polyline fill="none" stroke="currentColor" strokeWidth="2" points={values.map((v,i)=>`${values.length===1?165:5+i*320/(values.length-1)},${max===min?39:68-(v-min)/(max-min)*58}`).join(' ')}/></svg>:<p className="dash-no-history">Sparkline belum tersedia. Tidak ada garis atau nol pengganti.</p>}
    <p className="dash-card-note">{card.delta??'Pembanding belum tersedia.'}</p><small className="dash-card-reference">{card.note??'Baca periode, jenis pengukuran dan satuan sebelum membandingkan.'}</small>
    <div className="dash-card-bottom"><span>{card.source??'Institusi belum tersedia'}<br/>Rilis: {card.publicationDate??'Belum tersedia'}</span><button type="button" className="dash-text-button" onClick={()=>onNavigate(card)}>Detail ↗</button></div>
    <button type="button" className="dash-text-button p2-source-link" onClick={()=>onNavigate(card,true)} disabled={!card.available}>Source Trace angka ini ↗</button>
  </article>
}
export default function Dashboard() {
  const [filters,setFilters]=useState<DashboardFilters>({category:'',year:''})
  const dashboard=useDashboard(filters)
  const cards=dashboard.data?.indicators??[]
  const [search,setSearch]=useState('')
  const [dialogContent,setDialogContent]=useState('')
  const dialog=useRef<HTMLDialogElement>(null)
  const previousFocus=useRef<HTMLElement|null>(null)
  const navigation=useRef<AbortController|null>(null)
  const [navigationStatus,setNavigationStatus]=useState('')
  const [navigating,setNavigating]=useState(false)
  const root=useRef<HTMLDivElement>(null)
  const pdb=cards.find(c=>c.id==='pdb'),inflasi=cards.find(c=>c.id==='inflasi')
  const selected=cards.filter(c=>c.available).slice(0,3)
  const filtered=cards.filter(c=>[c.name,c.category,c.source??''].join(' ').toLocaleLowerCase('id-ID').includes(search.toLocaleLowerCase('id-ID')))
  const allowedCodes=filters.category?cards.map(c=>c.id):[...codes]
  useEffect(()=>{document.title='DEKSI · Deteksi Ekonomi Indonesia';return()=>navigation.current?.abort()},[])
  useEffect(()=>{
    const area=root.current
    if(!area||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return
    let frame=0
    const scroll=()=>{if(frame)return;frame=requestAnimationFrame(()=>{area.style.setProperty('--drift',`${Math.min(window.scrollY*.04,30)}px`);frame=0})}
    window.addEventListener('scroll',scroll,{passive:true});return()=>{window.removeEventListener('scroll',scroll);cancelAnimationFrame(frame)}
  },[])
  function info(content:string) {previousFocus.current=document.activeElement as HTMLElement;setDialogContent(content);dialog.current?.showModal()}
  function updateFilters(next:DashboardFilters) {
    navigation.current?.abort();setNavigationStatus('');setNavigating(false);setFilters(next)
  }
  async function navigate(card:DashboardCard,source=false) {
    navigation.current?.abort()
    if(!card.available){window.location.assign('/indikator/'+card.id);return}
    const controller=new AbortController();navigation.current=controller;setNavigating(true);setNavigationStatus('Mencocokkan konteks angka dan sumber…')
    try {
      const data=await fetchDetail(card.id,null,controller.signal)
      const matches=data.options.filter(({reading:r})=>r.observationDate===card.observationDate&&r.frequency===card.frequency&&r.dataType===card.dataType&&r.source?.sourceId===card.sourceId&&r.period===card.period&&r.unit===card.unit&&r.value===card.value&&r.publicationDate===card.publicationDate&&(r.rawFile?.retrievedAt??null)===card.retrievedAt)
      if(controller.signal.aborted)return
      if(matches.length!==1)throw new Error('Konteks ringkasan belum cocok unik dengan Source Trace. Tidak dialihkan ke nilai terbaru. Muat ulang ringkasan atau pilih titik histori.')
      window.location.assign(contextHref(matches[0].reading,matches[0].guard,source))
    } catch(error) {if(!controller.signal.aborted)setNavigationStatus(errorMessage(error))}
    finally {if(!controller.signal.aborted)setNavigating(false)}
  }
  return <div className="p2-dashboard" ref={root}>
    <a className="skip" href="#economic-overview">Lewati ke ringkasan ekonomi</a>
    <main className="artboard" aria-busy={navigating}>
      <section className="hero" id="hero" aria-labelledby="hero-title">
        <nav className="segmented-nav" aria-label="Navigasi utama"><a className="is-active" href="#hero" aria-current="page">Beranda</a><a href="#economic-indicators">Indikator</a><a href="#economic-trend">Tren</a><a href="#feedback-section">Feedback</a></nav>
        <p className="hero-date"><span>PERIODE OBSERVASI /</span><span>{pdb?.period??'Belum tersedia'}</span></p><a className="button contact" href="/admin/login"><span className="contact-label">Admin</span><Arrow/></a>
        <div className="title-group"><h1 className="display-title" id="hero-title"><span className="title-mask"><span className="title-line">DATA</span></span><span className="title-mask"><span className="title-line">DEKSI</span></span></h1><span className="title-year">(ID)</span></div>
        <div className="about"><p className="about-label">● (TENTANG)</p><p className="about-copy">Indikator ekonomi dalam konteks,<br/>dengan sumber yang bisa ditelusuri.</p><a className="button book" href="#economic-indicators">Lihat Data<Arrow/></a></div>
        <figure className="portrait-stage" aria-label="Foto perkotaan dari pengguna, sebagai ilustrasi"><div className="hero-photo-wrap"><img className="hero-photo" src={hero} alt="" fetchPriority="high"/></div><div className="brand-plate"><BrandMark/><span className="brand-name">DEKSI</span><button className="plate-menu" type="button" aria-label="Tentang DEKSI" onClick={()=>info('DEKSI menampilkan nilai, periode dan asal data. Publik tidak memerlukan akun. Foto adalah ilustrasi, bukan bukti angka atau dukungan institusi.')}><span/><span/></button></div><div className="jacket-logos"><span>Observasi</span><span>Periode</span><span>Sumber</span></div></figure>
        <div className="stats-frame"><article className="mini-card inventory-card"><p className="mini-value">{dashboard.loading?'…':cards.filter(c=>c.available).length}</p><p className="mini-label">Indikator tersedia pada respons</p><div className="tiny-marks">{codes.map(c=><span key={c}><i aria-hidden="true">◇</i>{names[c]}</span>)}</div><a className="mini-button" href="#economic-indicators">Telusuri data<Arrow/></a></article><article className="mini-card photo-stat"><img src={stat} alt=""/><p className="photo-feed">{pdb?.period??'Periode belum tersedia'}</p><div className="photo-stat-copy"><p className="mini-value">{amount(pdb)}</p><p className="mini-label">{pdb?.unit??''}<br/>{pdb?.name??'PDB'}</p></div></article></div>
        <div className="status-row"><div className="growth"><span className="check-disc" aria-hidden="true">↗</span><span>{dashboard.loading?'Memuat API':dashboard.error?'API belum tersedia':'Respons API'}</span></div><p className="availability"><span>Akses publik</span><span><small aria-hidden="true">●</small> tanpa akun</span></p></div>
        <article className="feature"><div className="feature-meta"><span>Konteks indikator</span><span>{pdb?.frequency??'Belum tersedia'}</span></div><h2>{pdb?.name??'Produk Domestik Bruto'}</h2><div className="feature-media"><img src={logistics} alt=""/><button className="feature-arrow" type="button" aria-label="Buka detail PDB" onClick={()=>pdb?navigate(pdb):window.location.assign('/indikator/pdb')}><Arrow/></button></div></article>
      </section>
      <section className="manifesto-section" id="statement" aria-label="Prinsip membaca data"><div className="black-bar"><p>DATA <em>DALAM KONTEKS</em></p><a className="scroll-call" href="#economic-overview">GULIR KE BAWAH<span className="scroll-circle">↓</span></a><p className="bar-right">PERIODE / SATUAN / SUMBER</p></div><div className="statement-body"><h2 className="manifesto"><span className="manifesto-line">Ekonomi lebih mudah dipahami saat</span><span className="manifesto-line">angka dibaca bersama konteksnya.</span><span className="manifesto-line">Telusuri periode, satuan, dan sumber</span><span className="manifesto-line">sebelum menarik kesimpulan.</span></h2><p className="sub-line">Bukan hanya angka yang terlihat.<br/><span>Perhatikan juga yang belum tersedia.</span></p></div></section>
      <div className="deksi-extension" id="dashboard">
        <section className="dash-overview dash-paper" id="economic-overview" aria-labelledby="overview-heading"><div className="dash-container"><div className="dash-eyebrow"><span>01 / MEMBACA EKONOMI</span><span>DEKSI · RESPONS API</span></div><div className="dash-overview-heading"><h2 className="dash-display" id="overview-heading">Angka. Lalu<br/>konteksnya.</h2><p className="dash-intro">Ikhtisar, indikator dan jejak sumber.<br/>Satu tempat untuk membaca gambaran besarnya.</p></div><div className="dash-metadata"><p><span>PILIHAN TAHUN</span><strong>{filters.year||'Terbaru per indikator'}</strong></p><p><span>PEMBARUAN TERSIMPAN</span><strong>{dashboard.data?.updatedAtFormatted??'Belum tersedia'}</strong></p><p><span>STATUS DATA</span><strong>{dashboard.loading?'Memuat…':dashboard.error?'Gagal memuat':'Sesuai respons API'}</strong></p></div><p className="dash-disclaimer">Periode tiap indikator dapat berbeda. Timestamp pembaruan global bukan tanggal rilis semua angka. Status publikasi dan nama institusi bukan bukti verifikasi resmi. Tidak ada angka atau narasi demo pengganti.</p><div className="dash-summary-grid"><div><p className="dash-kicker">IKHTISAR INDIKATOR</p><div className="dash-summary-copy"><p>Nilai ekonomi dibaca bersama satuan, periode dan jenis pengukurannya.</p><p>Narasi analisis terverifikasi belum disediakan kontrak API Sprint 1. Angka tidak ditafsirkan otomatis sebagai kondisi baik atau buruk.</p></div><button className="dash-text-button" type="button" onClick={()=>info('Metrik dan pembanding dihitung backend. Data kosong bukan nol. Histori lintas sumber atau jenis data tidak digabungkan. Publikasi, waktu pengambilan dan periode observasi adalah metadata yang berbeda. Formula versi dan jurnal revisi immutable belum tersedia.')}>Cara membaca data ini ↗</button></div><aside className="dash-callouts" aria-label="Nilai dari respons API">{selected.length?selected.map(card=><div className="dash-callout" key={card.id}><p className="dash-kicker">{card.name}</p><strong>{amount(card)}</strong><small>{card.unit} · {card.period}</small></div>):<div className="dash-callout"><strong>Belum tersedia</strong><small>Tidak ada angka contoh pengganti.</small></div>}</aside></div></div></section>
        <section className="dash-catalogue dash-paper" id="economic-indicators" aria-labelledby="indicators-heading"><div className="dash-container"><div className="dash-section-top"><div><p className="dash-kicker">02 / INDIKATOR UTAMA</p><h2 className="dash-section-title" id="indicators-heading">Enam sudut pandang.</h2></div><label className="dash-search"><span className="dash-sr">Cari indikator atau institusi</span><span aria-hidden="true">⌕</span><input type="search" id="indicator-search" placeholder="Cari indikator atau institusi…" value={search} onChange={e=>setSearch(e.target.value)}/></label></div><DashboardFilter filters={filters} onChange={updateFilters}/><div className="dash-catalogue-caption"><p role="status">{dashboard.loading?'Memuat indikator…':`${filtered.length} indikator pada pilihan ini`}</p><p>Nilai kosong bukan nol.</p></div>{dashboard.error?<div className="dash-empty" role="alert"><h3>Ringkasan belum tersedia.</h3><p>{dashboard.error}</p><button className="dash-pill" type="button" onClick={dashboard.retry}>Coba ringkasan lagi</button></div>:dashboard.loading?<p role="status">Memuat ringkasan dari API…</p>:filtered.length?<div className="dash-indicator-grid">{filtered.map((card,i)=><Card key={card.id} card={card} index={i} onNavigate={navigate}/>)}</div>:<div className="dash-empty"><h3>Belum ada yang cocok.</h3><p>Coba indikator, kategori atau institusi lain.</p><button className="dash-pill" type="button" onClick={()=>{setSearch('');updateFilters({category:'',year:''})}}>Reset pencarian dan filter ↗</button></div>}<p className="p2-navigation-status" role="status">{navigationStatus}</p></div></section>
        <DashboardTrend year={filters.year} allowedCodes={allowedCodes}/>
        <section className="dash-insights dash-paper" id="economic-insights" aria-labelledby="insights-heading"><div className="dash-container"><div className="dash-section-top"><div><p className="dash-kicker">04 / MEMBACA KONTEKS</p><h2 className="dash-section-title" id="insights-heading">Lebih dari sebuah angka.</h2></div><p className="dash-intro">Panduan membaca.<br/>Bukan narasi AI atau diagnosis ekonomi.</p></div><div className="dash-insight-list">{[['Periode bukan tanggal rilis.','Tanggal observasi, publikasi dan waktu akuisisi tidak saling menggantikan. Nilai lama tidak otomatis menggambarkan kondisi terkini.'],['Satuan menentukan makna.','Persen, poin persentase dan nilai nominal berbeda. Kenaikan angka tidak diberi label baik atau buruk tanpa analisis yang ditinjau.'],['Sumber mengikuti observasi.','Source Trace diikat pada angka, periode, satuan dan sumber terpilih. URL institusi serta checksum bukan verifikasi resmi angka.']].map(([title,body],i)=><article className="dash-insight" key={title}><p className="dash-insight-index">0{i+1} / KONTEKS</p><h3>{title}</h3><p className="dash-insight-body">{body}</p></article>)}</div></div></section>
        <section className="dash-provenance dash-ink" id="economic-sources" aria-labelledby="sources-heading"><div className="dash-container"><p className="dash-kicker">05 / DARI ANGKA KE SUMBER</p><div className="dash-provenance-grid"><h2 className="dash-display" id="sources-heading">Bisa dibaca.<br/>Bisa ditelusuri.</h2><div><p className="dash-large-copy">Pisahkan nilai, periode, publikasi, dan interpretasi. Nama institusi saja belum membuktikan sebuah angka sudah diverifikasi.</p><p className="dash-muted">Buka Source Trace dari kartu atau titik histori yang sama. Tidak ada katalog atau manajemen sumber Sprint 2 yang ditambahkan.</p><div className="dash-source-buttons"><a href="#economic-indicators" className="dash-pill">Pilih angka untuk ditelusuri ↗</a><button type="button" className="dash-pill" onClick={()=>info('Source Trace menyajikan hubungan observasi, institusi, publikasi dan RAW jika tersedia. Metadata yang hilang tetap belum tersedia. Backend belum menyediakan versi immutable atau formula/input berversi.')}>Baca metodologi ↗</button></div></div></div></div></section>
      </div>
      <section className="trust-section" id="trust" aria-labelledby="trust-title"><div className="trust-panel"><div className="trust-intro"><h2 id="trust-title"><span>Ekonomi,</span><span>beserta</span><span>konteks</span><span>datanya.</span></h2><p>Angka mengikuti respons API.<br/>Periksa periode tiap observasi.<br/>Verifikasi resmi tidak diasumsikan.</p><div className="glass-tile tile-star" aria-hidden="true">✳</div></div><div className="trust-cards"><article className="trust-card avatar-card"><div className="avatar-grid" aria-hidden="true" title="Foto ilustratif aktivitas ekonomi, bukan tim atau responden">{photos.map((photo,i)=><img key={i} src={photo} alt="" loading="lazy"/>)}</div><p className="trust-value">{amount(inflasi)}</p><p className="trust-label">{inflasi?.name??'Inflasi'} · {inflasi?.period??'Periode belum tersedia'} {inflasi?.unit??''}</p></article><article className="trust-card awards-card"><p className="trust-value">{cards.filter(c=>c.available).length}</p><p className="trust-label">Indikator tersedia pada respons</p><div className="p2-data-seal" aria-label="Respons API, bukan sertifikasi"><BrandMark/><strong>DEKSI</strong><span>PERIODE / SATUAN / SUMBER</span></div><p className="awards-note">Tidak menyiratkan dukungan institusi<br/>atau verifikasi resmi angka.</p></article><figure className="trust-card portrait-card"><img src={portrait} alt="Foto ilustratif pertanian, bukan bukti nilai observasi" loading="lazy"/></figure></div></div></section>
      <section id="feedback-section" className="deksi-extension dash-paper p2-feedback" aria-labelledby="feedback-title"><div className="dash-container"><p className="dash-kicker">06 / UMPAN BALIK</p><h2 className="dash-section-title" id="feedback-title">Bantu perbaiki pembacaan.</h2><p className="dash-intro">Sampaikan koreksi atau saran. Identitas opsional, tanpa akun. Kiriman menunggu review pengelola.</p><FeedbackForm/></div></section>
    </main>
    <footer className="deksi-extension dash-footer dash-paper"><div className="dash-container"><div className="dash-footer-main"><div><a className="dash-wordmark" href="#hero">DEKSI ↗</a><p>Deteksi Ekonomi Indonesia.<br/>Data, konteks dan sumber dibaca bersama.</p><p className="dash-footer-fine">Publik tanpa akun. Foto ilustratif tidak menyiratkan afiliasi, dukungan atau akurasi ekonomi.</p></div><div><h2>SPRINT 1</h2><a href="#economic-overview">Ringkasan indikator ↗</a><a href="#economic-trend">Grafik tren ↗</a><a href="#economic-indicators">Detail & Source Trace ↗</a><a href="#feedback-section">Feedback ↗</a></div><div><h2>TRANSPARANSI & AKSES</h2><button onClick={()=>info('Teks API diperlakukan sebagai data. Angka resmi, metrik turunan dan interpretasi tidak disamakan. Formula/input berversi dan jurnal immutable belum tersedia. Data di lingkungan uji adalah sintetis dan tidak mewakili ekonomi terkini.')} type="button">Cara membaca data ↗</button><button onClick={()=>info('Nama dan email feedback opsional. Jangan masukkan kata sandi atau data sensitif. Kiriman diproses pengelola; ini bukan jaminan kebijakan retensi produksi. Foto dari baseline pilihan dipertahankan beserta provenance/lisensi lokalnya; tidak ada foto baru yang diambil.')} type="button">Privasi & ilustrasi ↗</button><a href="/admin/login">Login Admin ↗</a><a href="/admin/forgot-password">Reset Password ↗</a></div></div><div className="dash-footer-bottom"><p>DEKSI · Periode dan sumber mengikuti API.</p><a href="#hero">Kembali ke atas ↑</a></div></div></footer>
    <dialog ref={dialog} className="p2-info" aria-labelledby="p2-info-title" onClose={()=>previousFocus.current?.focus()}><div className="p2-info-top"><h2 id="p2-info-title">Membaca DEKSI.</h2><button type="button" aria-label="Tutup informasi" onClick={()=>dialog.current?.close()}>×</button></div><p>{dialogContent}</p></dialog>
  </div>
}
