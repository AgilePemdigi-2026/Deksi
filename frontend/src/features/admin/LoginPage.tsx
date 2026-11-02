import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { BrandMark } from '../../components/EditorialLanding'
import heroImage from '../../assets/editorial/login-economic.webp'
import { validateLogin } from './validation'
import type { LoginErrors } from './validation'
import './login.css'

export default function LoginPage() {
  const identifier = useRef<HTMLInputElement>(null)
  const password = useRef<HTMLInputElement>(null)
  const info = useRef<HTMLDialogElement>(null)
  const [revealed, setRevealed] = useState(false)
  const [errors, setErrors] = useState<LoginErrors>({})
  const [status, setStatus] = useState('')
  useEffect(() => { document.title = 'Masuk Admin · DEKSI' }, [])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('')
    const nextErrors = validateLogin(identifier.current?.value ?? '', password.current?.value ?? '')
    setErrors(nextErrors)
    if (nextErrors.identifier) identifier.current?.focus()
    else if (nextErrors.password) password.current?.focus()
    else setStatus('Formulir lengkap. Autentikasi Admin belum terhubung; belum ada sesi masuk yang dibuat.')
  }

  function edit(field: keyof LoginErrors) {
    setStatus('')
    if (!errors[field]) return
    const nextErrors = validateLogin(identifier.current?.value ?? '', password.current?.value ?? '')
    setErrors(previous => ({ ...previous, [field]: nextErrors[field] }))
  }

  const openInfo = () => info.current?.showModal()
  return <div className="login-page">
    <a className="skip-link" href="#login-heading">Lewati ke formulir masuk</a>
    <div className="page">
      <header className="login-header">
        <a className="wordmark" href="/" aria-label="DEKSI, kembali ke dashboard publik"><BrandMark /><span>DEKSI</span></a>
        <a className="return-link" href="/"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M18 18 6 6m0 12V6h12" /></svg><span>Dashboard publik</span></a>
      </header>
      <main className="login-main">
        <section className="visual-panel" aria-label="Ilustrasi DEKSI">
          <div className="visual-photo"><img className="hero-photo" src={heroImage} alt="" fetchPriority="high" decoding="async" /></div>
          <p className="art-title" aria-hidden="true"><span>DATA</span><span>DEKSI</span></p>
          <div className="brand-plate"><BrandMark /><span className="brand-name">DEKSI</span><button type="button" className="plate-menu" onClick={openInfo} aria-label="Tentang prototipe DEKSI"><span /><span /></button></div>
        </section>
        <section className="login-form-panel" aria-labelledby="login-heading">
          <p className="eyebrow">AREA PENGELOLA</p><h1 id="login-heading" tabIndex={-1}>Masuk Admin.</h1>
          <p className="form-intro">Untuk tim pengelola DEKSI.<br />Pengunjung dapat membaca data tanpa masuk.</p>
          <form id="login-form" action="#" method="post" noValidate onSubmit={submit} aria-describedby="prototype-note">
            <div className="field"><label htmlFor="identifier">Email atau nama pengguna</label><div className="input-wrap"><input ref={identifier} id="identifier" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} placeholder="nama.pengelola" required aria-invalid={errors.identifier ? true : undefined} aria-describedby="identifier-error" onInput={() => edit('identifier')} /></div><span className="field-error" id="identifier-error" aria-live="polite">{errors.identifier}</span></div>
            <div className="field"><label htmlFor="password">Kata sandi</label><div className="input-wrap password-wrap"><input ref={password} id="password" type={revealed ? 'text' : 'password'} autoComplete="current-password" placeholder="Masukkan kata sandi" required aria-invalid={errors.password ? true : undefined} aria-describedby="password-error" onInput={() => edit('password')} /><button className="password-toggle" id="password-toggle" type="button" aria-controls="password" aria-pressed={revealed} aria-label={revealed ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'} onClick={() => setRevealed(value => !value)}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" /><circle cx="12" cy="12" r="2.8" />{revealed && <path d="m4 3 16 18" />}</svg><span>{revealed ? 'Sembunyikan' : 'Tampilkan'}</span></button></div><span className="field-error" id="password-error" aria-live="polite">{errors.password}</span></div>
            <details className="form-assistance" id="recovery-help"><summary>Lupa kata sandi?</summary><p>Hubungi pengelola akun DEKSI. Pemulihan kata sandi belum tersedia pada prototipe ini.</p></details>
            <button type="submit" className="submit-button" id="login-submit"><span>Masuk</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg></button>
            <p id="form-status" className="form-status" role="status" aria-live="polite" aria-atomic="true">{status}</p>
            <p id="prototype-note" className="prototype-note"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2" aria-hidden="true"><circle cx="8" cy="8" r="6" /><path d="M8 7v4m0-7v1" /></svg><span>Prototipe antarmuka. Autentikasi belum terhubung.<br />Jangan gunakan kredensial akun nyata.</span></p>
          </form>
        </section>
      </main>
      <footer className="login-footer"><p className="footer-name">DEKSI · Deteksi Ekonomi Indonesia</p><div className="footer-links"><a href="/">Publik tanpa akun ↗</a><button type="button" onClick={openInfo}>Tentang prototipe</button></div></footer>
    </div>
    <dialog ref={info} className="info-dialog" id="prototype-info" aria-labelledby="info-title" aria-describedby="info-body">
      <div className="dialog-top"><h2 id="info-title">Tentang prototipe.</h2><button type="button" className="dialog-close" id="close-info" aria-label="Tutup informasi prototipe" onClick={() => info.current?.close()}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6" /></svg></button></div>
      <p id="info-body">Halaman ini adalah <strong>preview desain Login Admin</strong>, bukan sistem autentikasi. Pemeriksaan formulir hanya berjalan lokal: tidak ada kredensial yang dikirim atau disimpan oleh aplikasi, dan tidak ada sesi masuk yang dibuat.</p>
      <p>Pengunjung publik tidak perlu akun. Tidak tersedia pendaftaran, pemulihan akun, atau akses dashboard Admin sungguhan pada preview ini.</p>
      <p>Kolase ilustratif dari foto <a href="https://www.pexels.com/photo/jakarta-s-bustling-financial-district-skyline-35808558/" target="_blank" rel="noopener noreferrer">gedung bisnis Jakarta</a> dan <a href="https://www.pexels.com/photo/a-person-holding-indonesian-money-8463694/" target="_blank" rel="noopener noreferrer">uang rupiah</a>. Sumber: Pexels, dengan <a href="https://www.pexels.com/license/" target="_blank" rel="noopener noreferrer">Pexels License</a>. Foto dipotong, diubah ke monokrom, dan digabungkan; bukan grafik atau data indikator ekonomi. Tidak menyiratkan afiliasi atau dukungan pihak yang tergambar.</p>
    </dialog>
  </div>
}
