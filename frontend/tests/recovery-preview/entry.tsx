import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from '../../src/App'
import { RecoveryError, unavailableRecovery } from '../../src/features/admin/recovery'
import type { RecoveryService } from '../../src/features/admin/recovery'
import '../../src/index.css'
import './preview.css'

// Only this test entry injects successful synthetic recovery; production has no fixture fallback.
const scenario = new URLSearchParams(location.search).get('scenario') || 'ready'
const counters = { request:0, check:0, confirm:0 }
Object.defineProperty(window, '__resetPreviewCounts', {value:counters})
function pause(signal?: AbortSignal) {
  return new Promise<void>((resolve,reject)=>{
    if(signal?.aborted){reject(new DOMException('Aborted','AbortError'));return}
    const done=()=>{signal?.removeEventListener('abort',abort);resolve()}
    const timer=setTimeout(done,600)
    const abort=()=>{clearTimeout(timer);signal?.removeEventListener('abort',abort);reject(new DOMException('Aborted','AbortError'))}
    signal?.addEventListener('abort',abort,{once:true})
  })
}
function failure() {
  if(['rate_limited','csrf_failed','unavailable','invalid_response'].includes(scenario))throw new RecoveryError(scenario)
}
const service: RecoveryService = {
  async request(_email,signal){counters.request++;await pause(signal);failure()},
  async check(credentials,signal){counters.check++;await pause(signal);failure();if(credentials.uid!=='demo-user'||credentials.token!=='demo-token')throw new RecoveryError('invalid_reset_link')},
  async confirm(_credentials,_password,_confirmation,signal){
    counters.confirm++;await pause(signal);failure()
    if(scenario==='confirm-uncertain')throw new RecoveryError('invalid_response')
    if(scenario==='password-error')throw new RecoveryError('password_validation_failed',{newPassword:['password_too_common']})
    if(scenario==='password-unknown-code')throw new RecoveryError('password_validation_failed',{newPassword:['constructor']})
  },
}

const props = { resetService: scenario === 'disconnected-preview' ? unavailableRecovery : service }
createRoot(document.getElementById('root')!).render(<StrictMode>
  <aside className="reset-preview-toolbar" aria-label="Kontrol prototype">
    <p><strong>PREVIEW SINTETIS</strong> · Tidak mengirim email atau mengubah kata sandi. Gunakan data contoh.</p>
    <details><summary>Skenario review</summary><nav aria-label="State prototype">
      <a href="/admin/forgot-password">Minta tautan</a>
      <a href="/admin/reset-password#uid=demo-user&token=demo-token">Password baru</a>
      <a href="/admin/reset-password#uid=demo-user&token=demo-invalid">Tautan tidak valid</a>
      <a href="/admin/forgot-password?scenario=rate_limited">Batas percobaan</a>
      <a href="/admin/forgot-password?scenario=unavailable">Server tidak tersedia</a>
      <a href="/admin/reset-password?scenario=password-error#uid=demo-user&token=demo-token">Validasi server</a>
      <a href="/admin/reset-password?scenario=confirm-uncertain#uid=demo-user&token=demo-token">Hasil perubahan tidak pasti</a>
      <a href="/admin/forgot-password?scenario=disconnected-preview">Service sengaja tidak terhubung</a>
      <a href="/admin/login">Login existing</a>
    </nav></details>
  </aside>
  <App {...props} />
</StrictMode>)
