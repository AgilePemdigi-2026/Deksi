import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { BrandMark } from '../../components/EditorialLanding'
import heroImage from '../../assets/editorial/login-economic.webp'
import { validateLogin } from './validation'
import type { LoginErrors } from './validation'
import { AuthError, authOrigin, createAuthClient } from './auth'
import type { AdminUser } from './auth'
import './login.css'

export default function LoginPage() {
  const identifier = useRef<HTMLInputElement>(null)
  const password = useRef<HTMLInputElement>(null)
  const info = useRef<HTMLDialogElement>(null)
  const [revealed, setRevealed] = useState(false)
  const [errors, setErrors] = useState<LoginErrors>({})
  const [status, setStatus] = useState('Memeriksa status sesi…')
  const [auth] = useState(() => createAuthClient(authOrigin()))
  const [user, setUser] = useState<AdminUser | null>(null)
  const [checking, setChecking] = useState(true)
  const [ready, setReady] = useState(false)
  const [pending, setPending] = useState(false)
  const [authError, setAuthError] = useState<AuthError | null>(null)
  const request = useRef<AbortController | null>(null)
  const inFlight = useRef(false)
  useEffect(() => { document.title = 'Masuk Admin · DEKSI' }, [])

  const loadSession = useCallback((controller: AbortController) => auth.session(controller.signal).then(current => {
    if (controller.signal.aborted) return
    setUser(current)
    setReady(true)
    if (current) {
      if (password.current) password.current.value = ''
      setRevealed(false)
    }
    setStatus(current ? 'Sesi Admin aktif.' : '')
  }).catch(error => {
    if (controller.signal.aborted) return
    const failure = error instanceof AuthError ? error : new AuthError('invalid_response')
    setUser(null)
    setAuthError(failure)
    setReady(failure.code === 'forbidden')
    setStatus(failure.message)
  }).finally(() => {
    if (!controller.signal.aborted) setChecking(false)
  }), [auth])
  function refreshSession() {
    if (inFlight.current) return
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setChecking(true)
    setReady(false)
    setAuthError(null)
    setStatus('Memeriksa status sesi…')
    void loadSession(controller)
  }
  useEffect(() => {
    const controller = new AbortController()
    request.current = controller
    void loadSession(controller)
    return () => request.current?.abort()
  }, [loadSession])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current || checking || !ready) return
    setStatus('')
    const nextErrors = validateLogin(identifier.current?.value ?? '', password.current?.value ?? '')
    setErrors(nextErrors)
    if (nextErrors.identifier) identifier.current?.focus()
    else if (nextErrors.password) password.current?.focus()
    else {
      inFlight.current = true
      const controller = new AbortController()
      request.current = controller
      setPending(true)
      setAuthError(null)
      setStatus('Memproses permintaan masuk…')
      try {
        const current = await auth.login(identifier.current?.value ?? '', password.current?.value ?? '', controller.signal)
        if (controller.signal.aborted) return
        if (password.current) password.current.value = ''
        setRevealed(false)
        setUser(current)
        setStatus('Berhasil masuk. Sesi Admin telah dikonfirmasi server.')
      } catch (error) {
        if (controller.signal.aborted) return
        const failure = error instanceof AuthError ? error : new AuthError('invalid_response')
        setAuthError(failure)
        setStatus(failure.message)
        if (['unavailable', 'invalid_response', 'invalid_configuration'].includes(failure.code)) setReady(false)
        if (failure.code === 'invalid_credentials') password.current?.focus()
      } finally {
        inFlight.current = false
        if (!controller.signal.aborted) setPending(false)
      }
    }
  }

  function edit(field: keyof LoginErrors) {
    if (!authError) setStatus('')
    if (!errors[field]) return
    const nextErrors = validateLogin(identifier.current?.value ?? '', password.current?.value ?? '')
    setErrors(previous => ({ ...previous, [field]: nextErrors[field] }))
  }

  async function logout() {
    if (inFlight.current || checking) return
    inFlight.current = true
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setAuthError(null)
    setStatus('Mengakhiri sesi…')
    try {
      await auth.logout(controller.signal)
      if (controller.signal.aborted) return
      setUser(null)
      setReady(true)
      setErrors({})
      if (password.current) password.current.value = ''
      setRevealed(false)
      setStatus('Anda telah keluar.')
      requestAnimationFrame(() => identifier.current?.focus())
    } catch (error) {
      if (controller.signal.aborted) return
      const failure = error instanceof AuthError ? error : new AuthError('invalid_response')
      setAuthError(failure)
      setStatus(failure.message)
    } finally {
      inFlight.current = false
      if (!controller.signal.aborted) setPending(false)
    }
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
          <div className="brand-plate"><BrandMark /><span className="brand-name">DEKSI</span><button type="button" className="plate-menu" onClick={openInfo} aria-label="Tentang DEKSI"><span /><span /></button></div>
        </section>
        <section className="login-form-panel" aria-labelledby="login-heading">
          <p className="eyebrow">AREA PENGELOLA</p><h1 id="login-heading" tabIndex={-1}>Masuk Admin.</h1>
          <p className="form-intro">Untuk tim pengelola DEKSI.<br />Pengunjung dapat membaca data tanpa masuk.</p>
          <form id="login-form" action="#" method="post" noValidate onSubmit={submit} aria-describedby="prototype-note" hidden={user !== null} aria-busy={pending}>
            <div className="field"><label htmlFor="identifier">Email atau nama pengguna</label><div className="input-wrap"><input ref={identifier} id="identifier" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} placeholder="nama.pengelola" required aria-invalid={errors.identifier ? true : undefined} aria-describedby="identifier-error" onInput={() => edit('identifier')} /></div><span className="field-error" id="identifier-error" aria-live="polite">{errors.identifier}</span></div>
            <div className="field"><label htmlFor="password">Kata sandi</label><div className="input-wrap password-wrap"><input ref={password} id="password" type={revealed ? 'text' : 'password'} autoComplete="current-password" placeholder="Masukkan kata sandi" required aria-invalid={errors.password ? true : undefined} aria-describedby="password-error" onInput={() => edit('password')} /><button className="password-toggle" id="password-toggle" type="button" aria-controls="password" aria-pressed={revealed} aria-label={revealed ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'} onClick={() => setRevealed(value => !value)}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" /><circle cx="12" cy="12" r="2.8" />{revealed && <path d="m4 3 16 18" />}</svg><span>{revealed ? 'Sembunyikan' : 'Tampilkan'}</span></button></div><span className="field-error" id="password-error" aria-live="polite">{errors.password}</span></div>
            <div className="form-assistance"><a id="recovery-help" href="/admin/forgot-password">Lupa kata sandi?</a></div>
            <button type="submit" className="submit-button" id="login-submit" disabled={pending || checking || !ready}><span>{pending ? 'Memproses…' : 'Masuk'}</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg></button>
            <p id="prototype-note" className="prototype-note"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2" aria-hidden="true"><circle cx="8" cy="8" r="6" /><path d="M8 7v4m0-7v1" /></svg><span>Autentikasi menggunakan sesi server.<br />Pengunjung publik tetap tidak memerlukan akun.</span></p>
          </form>
          {user && <section id="admin-session" className="session-panel" aria-label="Sesi Admin"><p>Masuk sebagai <strong id="session-user">{user.username}</strong>.</p><p>Sesi dikelola server. Halaman ini tidak membuat dashboard Admin baru.</p></section>}
          <p id="form-status" className="form-status" role="status" aria-live="polite" aria-atomic="true">{status}</p>
          {(user || authError?.code === 'forbidden') && <button id="auth-logout" className="submit-button" type="button" disabled={checking || pending} onClick={() => void logout()}>{pending ? 'Memproses…' : 'Keluar'}</button>}
          {(authError || user) && <button id="session-refresh" type="button" className="session-refresh" disabled={checking || pending} onClick={() => void refreshSession()}>Periksa status sesi</button>}
        </section>
      </main>
      <footer className="login-footer"><p className="footer-name">DEKSI · Deteksi Ekonomi Indonesia</p><div className="footer-links"><a href="/">Publik tanpa akun ↗</a><button type="button" onClick={openInfo}>Tentang Login Admin</button></div></footer>
    </div>
    <dialog ref={info} className="info-dialog" id="prototype-info" aria-labelledby="info-title" aria-describedby="info-body">
      <div className="dialog-top"><h2 id="info-title">Tentang Login Admin.</h2><button type="button" className="dialog-close" id="close-info" aria-label="Tutup informasi Login Admin" onClick={() => info.current?.close()}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6" /></svg></button></div>
      <p id="info-body">Halaman <strong>Login Admin DEKSI</strong> mengirim kredensial ke backend Django untuk membuat sesi server. Token sesi tidak disimpan di localStorage atau sessionStorage. Gunakan koneksi HTTPS pada deployment.</p>
      <p>Pengunjung publik tidak perlu akun. Tautan Lupa kata sandi membuka prototype pemulihan; pengiriman email dan perubahan kata sandi belum terhubung. Pendaftaran dan dashboard Admin React tidak disediakan melalui halaman ini.</p>
      <p>Kolase ilustratif dari foto <a href="https://www.pexels.com/photo/jakarta-s-bustling-financial-district-skyline-35808558/" target="_blank" rel="noopener noreferrer">gedung bisnis Jakarta</a> dan <a href="https://www.pexels.com/photo/a-person-holding-indonesian-money-8463694/" target="_blank" rel="noopener noreferrer">uang rupiah</a>. Sumber: Pexels, dengan <a href="https://www.pexels.com/license/" target="_blank" rel="noopener noreferrer">Pexels License</a>. Foto dipotong, diubah ke monokrom, dan digabungkan; bukan grafik atau data indikator ekonomi. Tidak menyiratkan afiliasi atau dukungan pihak yang tergambar.</p>
    </dialog>
  </div>
}
