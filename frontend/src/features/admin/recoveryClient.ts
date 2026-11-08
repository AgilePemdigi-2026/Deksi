import { RecoveryError } from './recovery'
import type { PasswordErrors, RecoveryService } from './recovery'

const maxBytes = 16 * 1024
const fieldCodes = new Set(['password_too_short', 'password_too_common', 'password_too_similar', 'password_entirely_numeric', 'password_unchanged', 'password_mismatch', 'password_invalid'])
const errorCodes: Record<number, string[]> = {
  400: ['invalid_request', 'invalid_reset_link', 'password_validation_failed'],
  403: ['csrf_failed'], 413: ['request_too_large'], 415: ['unsupported_media_type'],
  429: ['rate_limited'], 503: ['reset_unavailable'],
}
function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}
function safeFields(value: unknown): PasswordErrors {
  const fields = object(value)
  const result: PasswordErrors = {}
  for (const field of ['newPassword', 'confirmPassword'] as const) {
    const codes = fields?.[field]
    if (Array.isArray(codes) && codes.length) result[field] = codes.slice(0, 8).map(code => typeof code === 'string' && fieldCodes.has(code) ? code : 'password_invalid')
  }
  return result
}

export function createRecoveryClient(origin: string, fetcher: typeof fetch = fetch, timeoutMs = 10000): RecoveryService {
  let csrfToken = ''
  async function request(route: string, payload?: unknown, signal?: AbortSignal) {
    let base = ''
    try {
      if (origin) {
        const url = new URL(origin)
        if (/[\s@\\]/.test(origin) || !/^https?:\/\//i.test(origin) || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error()
        base = url.origin
      }
    } catch { throw new RecoveryError('invalid_configuration') }
    const encoded = payload === undefined ? undefined : JSON.stringify(payload)
    if (encoded !== undefined && new TextEncoder().encode(encoded).byteLength > maxBytes) throw new RecoveryError('request_too_large')
    const controller = new AbortController()
    const abort = () => controller.abort()
    if (signal?.aborted) abort()
    signal?.addEventListener('abort', abort, { once:true })
    const timeout = setTimeout(abort, timeoutMs)
    let received = false
    try {
      if (controller.signal.aborted) throw new RecoveryError('unavailable')
      const response = await fetcher(`${base}/api/auth/${route}/`, {
        method: encoded === undefined ? 'GET' : 'POST', credentials:'include', cache:'no-store', redirect:'error', signal:controller.signal,
        headers: encoded === undefined ? {} : {'Content-Type':'application/json', 'X-CSRFToken':csrfToken}, body:encoded,
      })
      received = true
      if (response.headers.get('content-type')?.split(';')[0]?.trim().toLowerCase() !== 'application/json' || !response.body) {
        void response.body?.cancel().catch(() => {})
        throw new RecoveryError('invalid_response')
      }
      const reader = response.body.getReader()
      const cancel = () => { void reader.cancel().catch(() => {}) }
      controller.signal.addEventListener('abort', cancel, { once:true })
      let text = '', bytes = 0
      const decoder = new TextDecoder('utf-8', {fatal:true})
      try {
        while (true) {
          if (controller.signal.aborted) throw new RecoveryError('unavailable')
          const chunk = await reader.read()
          if (controller.signal.aborted) throw new RecoveryError('unavailable')
          if (chunk.done) break
          bytes += chunk.value.byteLength
          if (bytes > maxBytes) { cancel(); throw new RecoveryError('invalid_response') }
          text += decoder.decode(chunk.value, {stream:true})
        }
        text += decoder.decode()
      } catch (error) {
        cancel()
        throw error
      } finally {
        controller.signal.removeEventListener('abort', cancel)
        reader.releaseLock()
      }
      let body: Record<string, unknown> | null
      try { body = object(JSON.parse(text)) } catch { throw new RecoveryError('invalid_response') }
      if (!body) throw new RecoveryError('invalid_response')
      if (!response.ok) {
        const code = typeof body.code === 'string' && errorCodes[response.status]?.includes(body.code) ? body.code : 'invalid_response'
        if (code === 'csrf_failed') csrfToken = ''
        throw new RecoveryError(code, code === 'password_validation_failed' ? safeFields(body.fields) : {})
      }
      return { body, status:response.status }
    } catch (error) {
      if (error instanceof RecoveryError) throw error
      throw new RecoveryError(received && !controller.signal.aborted ? 'invalid_response' : 'unavailable')
    } finally {
      controller.abort()
      clearTimeout(timeout)
      signal?.removeEventListener('abort', abort)
    }
  }
  async function csrf(signal?: AbortSignal) {
    if (!csrfToken) {
      const { body, status } = await request('csrf', undefined, signal)
      if (status !== 200 || typeof body.csrfToken !== 'string' || !body.csrfToken) throw new RecoveryError('invalid_response')
      csrfToken = body.csrfToken
    }
  }
  async function post(route: string, payload: unknown, signal?: AbortSignal) {
    // Reject oversized inputs before sending either a credential POST or CSRF bootstrap.
    if (new TextEncoder().encode(JSON.stringify(payload)).byteLength > maxBytes) throw new RecoveryError('request_too_large')
    await csrf(signal)
    return request(`password-reset/${route}`, payload, signal)
  }
  return {
    async request(email, signal) {
      const { body, status } = await post('request', {email}, signal)
      if (status !== 202 || body.accepted !== true || body.code !== 'reset_request_accepted') throw new RecoveryError('invalid_response')
    },
    async check(credentials, signal) {
      const { body, status } = await post('check', credentials, signal)
      if (status !== 200 || body.valid !== true) throw new RecoveryError('invalid_response')
    },
    async confirm(credentials, newPassword, confirmPassword, signal) {
      const { body, status } = await post('confirm', {...credentials, newPassword, confirmPassword}, signal)
      if (status !== 200 || body.code !== 'reset_complete' || body.authenticated !== false) throw new RecoveryError('invalid_response')
    },
  }
}
