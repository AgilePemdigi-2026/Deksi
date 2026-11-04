import { useCallback, useEffect, useRef, useState } from 'react'
import RecoveryLayout, { RecoveryAction } from './RecoveryLayout'
import { parseResetCredentials, RecoveryError, unavailableRecovery } from './recovery'
import type { RecoveryService } from './recovery'

type Stage = 'checking' | 'valid' | 'invalid' | 'unavailable' | 'complete'
type Errors = { newPassword?: string; confirmPassword?: string }
function clearCapabilityFromAddress() {
  const url = new URL(window.location.href)
  url.hash = ''
  url.searchParams.delete('uid')
  url.searchParams.delete('token')
  window.history.replaceState(window.history.state, '', url.pathname + url.search)
}
const passwordMessages: Record<string, string> = {
  password_too_short: 'Kata sandi terlalu pendek. Ikuti ketentuan dari pengelola akun.',
  password_too_common: 'Kata sandi terlalu umum. Pilih kata sandi yang lebih sulit ditebak.',
  password_too_similar: 'Kata sandi terlalu mirip dengan informasi akun.',
  password_entirely_numeric: 'Kata sandi tidak boleh hanya berupa angka.',
  password_unchanged: 'Gunakan kata sandi yang berbeda dari kata sandi saat ini.',
  password_mismatch: 'Konfirmasi kata sandi belum cocok.',
}

export default function ResetPasswordPage({ service = unavailableRecovery }: { service?: RecoveryService }) {
  const [credentials, setCredentials] = useState(() => parseResetCredentials(typeof window === 'undefined' ? '' : window.location.hash))
  const [stage, setStage] = useState<Stage>(credentials ? 'checking' : 'invalid')
  const [errors, setErrors] = useState<Errors>({})
  const [status, setStatus] = useState('')
  const [pending, setPending] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const password = useRef<HTMLInputElement>(null)
  const confirmation = useRef<HTMLInputElement>(null)
  const inFlight = useRef(false)
  const request = useRef<AbortController | null>(null)

  const check = useCallback((controller: AbortController) => {
    if (!credentials) return Promise.resolve()
    return service.check(credentials, controller.signal).then(() => {
      if (!controller.signal.aborted) setStage('valid')
    }).catch(error => {
      if (controller.signal.aborted) return
      setStage(error instanceof RecoveryError && error.code === 'invalid_reset_link' ? 'invalid' : 'unavailable')
    })
  }, [credentials, service])

  useEffect(() => {
    document.title = 'Atur ulang kata sandi · DEKSI'
    clearCapabilityFromAddress()
    const controller = new AbortController()
    request.current = controller
    void check(controller)
    return () => controller.abort()
  }, [check])
  useEffect(() => {
    function consumeNewFragment() {
      request.current?.abort()
      inFlight.current = false
      const next = parseResetCredentials(window.location.hash)
      clearCapabilityFromAddress()
      if (password.current) password.current.value = ''
      if (confirmation.current) confirmation.current.value = ''
      setCredentials(next)
      setStage(next ? 'checking' : 'invalid')
      setErrors({})
      setStatus('')
      setPending(false)
      setUncertain(false)
      setShowPassword(false)
      setShowConfirm(false)
    }
    window.addEventListener('hashchange', consumeNewFragment)
    return () => window.removeEventListener('hashchange', consumeNewFragment)
  }, [])
  useEffect(() => () => request.current?.abort(), [])

  function retryCheck() {
    if (inFlight.current || !credentials) return
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setStage('checking')
    void check(controller)
  }

  async function submit() {
    if (inFlight.current || !credentials || stage !== 'valid' || uncertain) return
    const first = password.current?.value ?? ''
    const second = confirmation.current?.value ?? ''
    const next: Errors = {}
    if (!first) next.newPassword = 'Masukkan kata sandi baru.'
    if (!second) next.confirmPassword = 'Masukkan konfirmasi kata sandi.'
    else if (first !== second) next.confirmPassword = 'Konfirmasi kata sandi belum cocok.'
    setErrors(next)
    if (next.newPassword) { password.current?.focus(); return }
    if (next.confirmPassword) { confirmation.current?.focus(); return }
    inFlight.current = true
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setStatus('Menyimpan kata sandi…')
    try {
      await service.confirm(credentials, first, second, controller.signal)
      if (controller.signal.aborted) return
      if (password.current) password.current.value = ''
      if (confirmation.current) confirmation.current.value = ''
      setCredentials(null)
      setStage('complete')
      setStatus('Silakan masuk kembali dengan kata sandi baru.')
      requestAnimationFrame(() => document.getElementById('recovery-heading')?.focus())
    } catch (error) {
      if (controller.signal.aborted) return
      const code = error instanceof RecoveryError ? error.code : 'unavailable'
      if (code === 'invalid_reset_link') { setStage('invalid'); setCredentials(null); return }
      if (code === 'password_validation_failed' && error instanceof RecoveryError) {
        const fields: Errors = {}
        for (const field of ['newPassword', 'confirmPassword'] as const) {
          const codes = error.fields[field]
          if (Array.isArray(codes) && codes.length) fields[field] = typeof codes[0] === 'string' && Object.hasOwn(passwordMessages, codes[0]) ? passwordMessages[codes[0]] : 'Kata sandi belum memenuhi ketentuan server.'
        }
        setErrors(fields)
        setStatus('Periksa kembali kata sandi yang Anda masukkan.')
        requestAnimationFrame(() => {
          if (fields.newPassword) password.current?.focus()
          else confirmation.current?.focus()
        })
      } else if (code === 'csrf_failed') setStatus('Pemeriksaan keamanan gagal. Silakan coba kembali.')
      else if (code === 'rate_limited') setStatus('Terlalu banyak percobaan. Tunggu beberapa saat sebelum mencoba kembali.')
      else {
        setUncertain(true)
        setStatus(code === 'not_connected' ? 'Perubahan kata sandi belum terhubung pada tahap prototype ini.' : 'Hasil perubahan belum dapat dipastikan. Jangan mengirim ulang otomatis. Coba Login atau minta tautan baru.')
      }
    } finally {
      inFlight.current = false
      if (!controller.signal.aborted) setPending(false)
    }
  }

  const title = stage === 'complete' ? 'Kata sandi diperbarui.' : stage === 'invalid' ? 'Tautan tidak dapat digunakan.' : stage === 'unavailable' ? 'Belum dapat memeriksa tautan.' : stage === 'checking' ? 'Memeriksa tautan.' : 'Buat kata sandi baru.'
  return <RecoveryLayout title={title}>
    {stage === 'checking' && <p className="form-intro" role="status">Mohon tunggu, tautan pemulihan sedang diperiksa.</p>}
    {stage === 'invalid' && <><p className="form-intro">Tautan mungkin tidak valid, kedaluwarsa, atau sudah digunakan.</p><a id="recovery-new-link" className="recovery-cta-link" href="/admin/forgot-password">Minta tautan baru <span aria-hidden="true">↗</span></a></>}
    {stage === 'unavailable' && <><p className="form-intro">Status tautan belum dapat dipastikan. Periksa koneksi atau coba kembali nanti.</p><button type="button" className="submit-button" id="recovery-recheck" onClick={retryCheck}>Periksa kembali</button><a className="recovery-secondary" href="/admin/forgot-password">Minta tautan baru</a></>}
    {stage === 'complete' && <><p className="form-intro">Kata sandi akun Admin telah diperbarui. Silakan masuk kembali melalui halaman Login.</p><a id="recovery-login" className="recovery-cta-link" href="/admin/login">Kembali ke Login <span aria-hidden="true">↗</span></a></>}
    {stage === 'valid' && <>
      <p className="form-intro">Pilih kata sandi yang berbeda dari sebelumnya untuk melanjutkan akses akun Admin.</p>
      <form id="recovery-confirm-form" noValidate aria-busy={pending} aria-describedby="recovery-boundary" onSubmit={event => { event.preventDefault(); void submit() }}>
        <div className="field"><label htmlFor="recovery-new-password">Kata sandi baru</label><div className="input-wrap password-wrap"><input ref={password} id="recovery-new-password" name="newPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Masukkan kata sandi baru" required disabled={pending} aria-invalid={errors.newPassword ? true : undefined} aria-describedby="recovery-password-help recovery-new-error" onInput={() => setErrors(previous => ({ ...previous, newPassword:undefined }))} /><button type="button" className="password-toggle" id="recovery-new-toggle" aria-controls="recovery-new-password" aria-pressed={showPassword} aria-label={showPassword ? 'Sembunyikan kata sandi baru' : 'Tampilkan kata sandi baru'} disabled={pending} onClick={() => setShowPassword(previous => !previous)}>{showPassword ? 'Sembunyikan' : 'Tampilkan'}</button></div><span className="field-error" id="recovery-new-error" aria-live="polite">{errors.newPassword}</span></div>
        <div className="field"><label htmlFor="recovery-confirm-password">Konfirmasi kata sandi</label><div className="input-wrap password-wrap"><input ref={confirmation} id="recovery-confirm-password" name="confirmPassword" type={showConfirm ? 'text' : 'password'} autoComplete="new-password" placeholder="Ulangi kata sandi baru" required disabled={pending} aria-invalid={errors.confirmPassword ? true : undefined} aria-describedby="recovery-confirm-error" onInput={() => setErrors(previous => ({ ...previous, confirmPassword:undefined }))} /><button type="button" className="password-toggle" id="recovery-confirm-toggle" aria-controls="recovery-confirm-password" aria-pressed={showConfirm} aria-label={showConfirm ? 'Sembunyikan konfirmasi kata sandi' : 'Tampilkan konfirmasi kata sandi'} disabled={pending} onClick={() => setShowConfirm(previous => !previous)}>{showConfirm ? 'Sembunyikan' : 'Tampilkan'}</button></div><span className="field-error" id="recovery-confirm-error" aria-live="polite">{errors.confirmPassword}</span></div>
        <p className="recovery-password-help" id="recovery-password-help">Gunakan kata sandi yang panjang dan sulit ditebak. Ketentuan kata sandi akan diperiksa oleh server.</p>
        <RecoveryAction id="recovery-confirm-submit" disabled={pending || uncertain}>{pending ? 'Memproses…' : 'Simpan kata sandi'}</RecoveryAction>
      </form>
      {uncertain && <a className="recovery-secondary" href="/admin/forgot-password">Minta tautan baru</a>}
    </>}
    <p className="recovery-status" id="recovery-status" role="status" aria-live="polite" aria-atomic="true">{status}</p>
  </RecoveryLayout>
}
