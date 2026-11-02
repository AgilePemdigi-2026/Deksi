import type { SummaryCard, SummaryResponse } from '../api'
import heroImage from '../assets/editorial/hero-business.webp'
import marketImage from '../assets/editorial/stat-market.webp'
import portImage from '../assets/editorial/feature-logistics.webp'
import harvestImage from '../assets/editorial/portrait-agriculture.webp'
import skyline from '../assets/editorial/activity-skyline.webp'
import port from '../assets/editorial/activity-port.webp'
import food from '../assets/editorial/activity-food.webp'
import harvest from '../assets/editorial/activity-harvest.webp'
import market from '../assets/editorial/activity-market.webp'
import bank from '../assets/editorial/activity-bank.webp'
import agriculture from '../assets/editorial/activity-agriculture.webp'
import distribution from '../assets/editorial/activity-distribution.webp'

export function BrandMark({ className = 'brand-symbol' }: { className?: string }) {
  return <svg className={className} viewBox="0 0 42 34" aria-hidden="true"><path d="M0 31 16 3l8 14-8 14Z" /><path d="m21 31 8-14 9 14Z" /></svg>
}

export function Arrow() {
  return <svg className="arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg>
}

type LandingProps = {
  cards: SummaryCard[]
  summary: SummaryResponse | null
  loading: boolean
  error: string | null
  onInfo: () => void
}

export function EditorialLanding({ cards, summary, loading, error, onInfo }: LandingProps) {
  const ready = !loading && !error && summary !== null
  const primary = cards.find(card => card.id === 'pdb')
  const historyCount = ready ? cards.filter(card => card.sparkline?.length > 1).length : '—'
  const period = primary?.period ?? primary?.latestPeriod ?? 'Periode belum tersedia'
  return <div className="editorial-landing">
    <section className="hero" id="dashboard" aria-labelledby="hero-title">
      <nav className="segmented-nav" aria-label="Navigasi utama">
        <span className="nav-slider" aria-hidden="true" />
        <a className="is-active" href="#dashboard" aria-current="page">Beranda</a>
        <a href="#indikator">Indikator</a><a href="#analisis">Tren</a>
        <button type="button" onClick={onInfo}>Sumber</button>
      </nav>
      <p className="hero-date"><span>{loading ? 'MEMUAT DATA /' : error ? 'API BELUM TERHUBUNG /' : 'RESPONS API /'}</span><span>{period}</span></p>
      <button type="button" className="button contact" onClick={onInfo} aria-label="Buka informasi sumber"><span className="contact-label">Sumber</span><Arrow /></button>
      <div className="title-group"><h1 className="display-title" id="hero-title"><span className="title-mask"><span className="title-line">DATA</span></span><span className="title-mask"><span className="title-line">DEKSI</span></span></h1><span className="title-year">(PUBLIK)</span></div>
      <div className="about"><p className="about-label">● (TENTANG)</p><p className="about-copy">Indikator ekonomi dalam konteks,<br />dengan sumber yang bisa ditelusuri.</p><a className="button book" href="#indikator">Lihat Data<Arrow /></a></div>
      <figure className="portrait-stage" aria-label="Foto perkotaan sebagai ilustrasi, bukan bukti data ekonomi">
        <div className="hero-photo-wrap"><img className="hero-photo" src={heroImage} alt="" fetchPriority="high" decoding="async" /></div>
        <div className="brand-plate"><BrandMark /><span className="brand-name">DEKSI</span><button type="button" className="plate-menu" onClick={onInfo} aria-label="Tentang DEKSI"><span /><span /></button></div>
        <div className="jacket-logos" aria-label="Konteks data"><span>Observasi</span><span>Periode</span><span>Sumber</span></div>
      </figure>
      <div className="stats-frame">
        <article className="mini-card inventory-card"><p className="mini-value">{historyCount}</p><p className="mini-label">Indikator dengan histori<br />dalam respons API</p><div className="tiny-marks" aria-label="Sudut pandang ekonomi"><span>✳ PDB</span><span>◇ IHK</span><span>⌁ APBN</span><span>◒ Investasi</span><span>↗ BI-Rate</span><span>△ TPT</span></div><a className="mini-button" href="#indikator">Telusuri data<Arrow /></a></article>
        <article className="mini-card photo-stat"><img src={marketImage} alt="" decoding="async" /><p className="photo-feed">{ready ? period : 'Menunggu respons API'}</p><div className="photo-stat-copy"><p className="mini-value">{ready ? primary?.value ?? '—' : '—'}</p><p className="mini-label">{primary?.name ?? 'Pertumbuhan PDB'}<br />{primary?.unit ?? 'Satuan belum tersedia'}</p></div></article>
      </div>
      <div className="status-row"><div className="growth"><span className="check-disc" aria-hidden="true">{ready ? '✓' : '○'}</span><span>{loading ? 'Memuat' : error ? 'API belum siap' : 'Respons API'}</span></div><p className="availability"><span>Akses publik</span><span><small aria-hidden="true">●</small> tanpa akun</span></p></div>
      <article className="feature"><div className="feature-meta"><span>Periode</span><span>{ready ? period : 'Belum tersedia'}</span></div><h2>{primary?.name ?? 'Pertumbuhan PDB'}</h2><div className="feature-media"><img src={portImage} alt="" decoding="async" /><a className="feature-arrow" href="#indikator" aria-label="Baca daftar indikator"><Arrow /></a><div className="feature-progress" aria-hidden="true"><span /></div></div></article>
    </section>
    <section className="manifesto-section" id="statement" aria-label="Prinsip membaca data DEKSI">
      <div className="black-bar"><p>DATA <em>DEKSI</em></p><a className="scroll-call" href="#manifesto">GULIR KE BAWAH<span className="scroll-circle"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v16M5 13l7 7 7-7" /></svg></span></a><p className="bar-right">BACA DALAM KONTEKS</p></div>
      <div className="statement-body"><h2 className="manifesto" id="manifesto"><span className="manifesto-line">Ekonomi lebih mudah dipahami saat</span><span className="manifesto-line">angka dibaca bersama konteksnya.</span><span className="manifesto-line">Telusuri periode, satuan, dan sumber</span><span className="manifesto-line">sebelum menarik kesimpulan. Nama</span><span className="manifesto-line">institusi bukan bukti verifikasi angka.</span></h2><p className="sub-line">Nilai dan metadata mengikuti respons backend.<br /><span>Data hilang tidak diganti dengan nol.</span></p></div>
    </section>
  </div>
}

export function EditorialContext({ cards, loading, error }: Pick<LandingProps, 'cards' | 'loading' | 'error'>) {
  const inflation = cards.find(card => card.id === 'inflasi')
  const missing = loading || error ? '—' : cards.filter(card => card.value === null || !card.available).length
  return <div className="editorial-landing"><section className="trust-section" id="context" aria-labelledby="trust-title"><div className="trust-panel">
    <div className="trust-intro"><h2 id="trust-title"><span>Ekonomi,</span><span>beserta</span><span>konteks</span><span>datanya.</span></h2><p>Nilai, satuan, dan periode<br />dibaca bersama sumbernya.<br />Foto hanya sebagai ilustrasi.</p><div className="glass-tile tile-star" aria-hidden="true"><svg viewBox="0 0 48 48"><path d="M24 4v40M4 24h40M10 10l28 28M10 38 38 10" /></svg></div><div className="glass-tile tile-dots" aria-hidden="true"><div className="dot-mark"><i /><i /><i /><i /></div></div></div>
    <div className="trust-cards"><article className="trust-card avatar-card"><div className="avatar-grid" aria-hidden="true" title="Ilustrasi aktivitas ekonomi, bukan responden atau tim DEKSI">{[skyline, port, food, harvest, market, bank, agriculture, distribution].map(src => <img key={src} src={src} alt="" loading="lazy" />)}</div><p className="trust-value">{loading || error ? '—' : inflation?.value ?? '—'}</p><p className="trust-label">{inflation?.name ?? 'Inflasi IHK'} · {inflation?.period ?? 'Periode belum tersedia'}</p></article>
    <article className="trust-card awards-card"><p className="trust-value">{missing}</p><p className="trust-label">Indikator tanpa nilai pada API</p><div className="missing-symbol" aria-hidden="true">∅ ≠ 0</div><p className="awards-note">Data hilang bukan nol.<br />Ketersediaan tidak sama dengan verifikasi.</p></article>
    <figure className="trust-card portrait-card" title="Ilustrasi pertanian, bukan bukti angka observasi"><img src={harvestImage} alt="" loading="lazy" decoding="async" /></figure></div>
  </div></section></div>
}
