import { useRef } from 'react'
import type { ReactNode } from 'react'
import { BrandMark } from '../../components/EditorialLanding'
import heroImage from '../../assets/editorial/login-economic.webp'
import './login.css'
import './recovery.css'

export default function RecoveryLayout({ title, children }: { title: string; children: ReactNode }) {
  const info = useRef<HTMLDialogElement>(null)
  return <div className="login-page recovery-page">
    <a className="skip-link" href="#recovery-heading">Lewati ke pemulihan akun</a>
    <div className="page">
      <header className="login-header">
        <a className="wordmark" href="/" aria-label="DEKSI, kembali ke dashboard publik"><BrandMark /><span>DEKSI</span></a>
        <a className="return-link" href="/"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M18 18 6 6m0 12V6h12" /></svg><span>Dashboard publik</span></a>
      </header>
      <main className="login-main">
        <section className="visual-panel" aria-label="Ilustrasi DEKSI">
          <div className="visual-photo"><img className="hero-photo" src={heroImage} alt="" fetchPriority="high" decoding="async" /></div>
          <p className="art-title" aria-hidden="true"><span>DATA</span><span>DEKSI</span></p>
          <div className="brand-plate"><BrandMark /><span className="brand-name">DEKSI</span><button type="button" className="plate-menu" onClick={() => info.current?.showModal()} aria-label="Tentang pemulihan akun DEKSI"><span /><span /></button></div>
        </section>
        <section className="login-form-panel" aria-labelledby="recovery-heading">
          <p className="eyebrow">PEMULIHAN AKUN ADMIN</p>
          <h1 id="recovery-heading" tabIndex={-1}>{title}</h1>
          {children}
          <a className="recovery-back" href="/admin/login"><span aria-hidden="true">↖</span> Kembali ke Login</a>
          <p className="prototype-note" id="recovery-boundary">Pemulihan hanya untuk akun Admin. Permintaan diterima tidak menjamin email sudah tiba.</p>
        </section>
      </main>
      <footer className="login-footer"><p className="footer-name">DEKSI · Deteksi Ekonomi Indonesia</p><div className="footer-links"><a href="/">Publik tanpa akun ↗</a><button type="button" onClick={() => info.current?.showModal()}>Tentang pemulihan akun</button></div></footer>
    </div>
    <dialog ref={info} className="info-dialog" id="recovery-info" aria-labelledby="recovery-info-title">
      <div className="dialog-top"><h2 id="recovery-info-title">Pemulihan akun.</h2><button type="button" className="dialog-close" aria-label="Tutup informasi pemulihan" onClick={() => info.current?.close()}>×</button></div>
      <p>Tautan pemulihan bersifat pribadi. Jangan bagikan tautan atau kata sandi kepada orang lain. Keberhasilan permintaan tidak mengonfirmasi sebuah email terdaftar. Publik tetap dapat membaca data tanpa akun.</p>
      <p>Ilustrasi menggunakan kolase foto <a href="https://www.pexels.com/photo/jakarta-s-bustling-financial-district-skyline-35808558/" target="_blank" rel="noopener noreferrer">gedung bisnis Jakarta</a> dan <a href="https://www.pexels.com/photo/a-person-holding-indonesian-money-8463694/" target="_blank" rel="noopener noreferrer">uang rupiah</a> dari Pexels, sesuai catatan sumber Login. <a href="https://www.pexels.com/license/" target="_blank" rel="noopener noreferrer">Pexels License</a>.</p>
    </dialog>
  </div>
}

export function RecoveryAction({ children, disabled = false, id }: { children: ReactNode; disabled?: boolean; id: string }) {
  return <button id={id} type="submit" className="submit-button" disabled={disabled}><span>{children}</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg></button>
}
