import { useEffect, useRef, useState } from 'react'
import RecoveryLayout, { RecoveryAction } from './RecoveryLayout'
import { RecoveryError, unavailableRecovery } from './recovery'
import type { RecoveryService } from './recovery'

function requestMessage(error: unknown) {
  const code = error instanceof RecoveryError ? error.code : 'unavailable'
  if (code === 'rate_limited') return 'Terlalu banyak permintaan. Tunggu beberapa saat sebelum mencoba kembali.'
  if (code === 'csrf_failed') return 'Pemeriksaan keamanan gagal. Silakan coba kembali.'
  if (code === 'not_connected') return 'Pengiriman email belum terhubung pada tahap prototype ini. Belum ada permintaan yang dikirim.'
  return 'Permintaan belum dapat dipastikan. Coba kembali nanti atau hubungi pengelola akun.'
}

export default function ForgotPasswordPage({ service = unavailableRecovery }: { service?: RecoveryService }) {
  const email = useRef<HTMLInputElement>(null)
  const inFlight = useRef(false)
  const controller = useRef<AbortController | null>(null)
  const [value, setValue] = useState('')
  const [accepted, setAccepted] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  useEffect(() => {
    document.title = 'Lupa kata sandi · DEKSI'
    return () => controller.current?.abort()
  }, [])

  async function sendRequest() {
    if (inFlight.current) return
    const invalid = !value.trim() ? 'Masukkan email akun Admin.' : email.current?.validity.typeMismatch || value.length > 254 ? 'Masukkan alamat email yang valid.' : ''
    setError(invalid)
    if (invalid) { email.current?.focus(); return }
    inFlight.current = true
    const request = new AbortController()
    controller.current = request
    setPending(true)
    setStatus('Memproses permintaan…')
    try {
      await service.request(value.trim(), request.signal)
      if (request.signal.aborted) return
      setAccepted(true)
      setStatus('Permintaan diterima. Periksa email dan folder spam Anda.')
      requestAnimationFrame(() => document.getElementById('recovery-heading')?.focus())
    } catch (failure) {
      if (!request.signal.aborted) setStatus(requestMessage(failure))
    } finally {
      inFlight.current = false
      if (!request.signal.aborted) setPending(false)
    }
  }

  return <RecoveryLayout title={accepted ? 'Periksa email Anda.' : 'Lupa kata sandi?'}>
    <p className="form-intro">{accepted ? 'Jika alamat tersebut terkait akun Admin yang memenuhi syarat, instruksi pemulihan akan dikirim.' : 'Masukkan email akun Admin untuk meminta tautan pemulihan.'}</p>
    <form id="recovery-request-form" noValidate hidden={accepted} aria-busy={pending} onSubmit={event => { event.preventDefault(); void sendRequest() }} aria-describedby="recovery-boundary">
      <div className="field"><label htmlFor="recovery-email">Email akun Admin</label><div className="input-wrap"><input ref={email} id="recovery-email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} placeholder="admin@contoh.id" required value={value} onChange={event => { setValue(event.target.value); setError('') }} aria-invalid={error ? true : undefined} aria-describedby="recovery-email-error" disabled={pending} /></div><span className="field-error" id="recovery-email-error" aria-live="polite">{error}</span></div>
      <RecoveryAction id="recovery-request-submit" disabled={pending}>{pending ? 'Memproses…' : 'Kirim tautan reset'}</RecoveryAction>
    </form>
    {accepted && <div id="recovery-accepted">
      <p className="recovery-note">Belum menerima instruksi? Periksa folder spam atau pastikan alamat email yang Anda masukkan sudah benar.</p>
      <button type="button" id="recovery-resend" className="submit-button" disabled={pending} onClick={() => void sendRequest()}>{pending ? 'Memproses…' : 'Kirim ulang tautan'}</button>
      <button type="button" id="recovery-edit-email" className="recovery-secondary" disabled={pending} onClick={() => { setAccepted(false); setStatus(''); requestAnimationFrame(() => email.current?.focus()) }}>Ubah alamat email</button>
    </div>}
    <p className="recovery-status" role="status" aria-live="polite" aria-atomic="true" id="recovery-status">{status}</p>
  </RecoveryLayout>
}
