export type AdminUser = { id: number; username: string; isAdmin: true }

const messages: Record<string, string> = {
  invalid_credentials: 'Email/nama pengguna atau kata sandi tidak valid.',
  invalid_request: 'Data masuk tidak valid. Periksa kembali formulir.',
  csrf_failed: 'Pemeriksaan keamanan gagal. Silakan coba kembali.',
  forbidden: 'Akun ini tidak lagi memiliki akses Admin.',
  rate_limited: 'Terlalu banyak percobaan masuk. Tunggu beberapa saat sebelum mencoba kembali.',
  unavailable: 'Server autentikasi belum dapat dihubungi. Periksa status sesi sebelum mencoba kembali.',
  invalid_response: 'Respons autentikasi belum dapat dipastikan. Periksa kembali status sesi.',
  invalid_configuration: 'Konfigurasi server autentikasi tidak valid. Hubungi pengelola.',
}

export class AuthError extends Error {
  code: string
  status: number
  constructor(code: string, status = 0) {
    super(messages[code] ?? messages.invalid_response)
    this.code = code
    this.status = status
  }
}

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

function sessionUser(value: unknown): AdminUser | null {
  const body = object(value)
  if (body?.authenticated === false && body.user === null) return null
  const user = object(body?.user)
  if (body?.authenticated !== true || !user || user.isAdmin !== true || !Number.isSafeInteger(user.id) || (user.id as number) <= 0 || typeof user.username !== 'string' || !user.username) {
    throw new AuthError('invalid_response')
  }
  return { id: user.id as number, username: user.username, isAdmin: true }
}

export function authOrigin() {
  const configured = import.meta.env.VITE_AUTH_API_ORIGIN as string | undefined
  if (configured) return configured.replace(/\/$/, '')
  return ''
}

export function createAuthClient(origin: string, fetcher: typeof fetch = fetch) {
  let csrfToken = ''
  async function request(route: string, method = 'GET', payload?: unknown, signal?: AbortSignal) {
    const controller = new AbortController()
    const abort = () => controller.abort()
    if (signal?.aborted) abort()
    signal?.addEventListener('abort', abort, { once: true })
    const timeout = setTimeout(abort, 10000)
    try {
      let base = ''
      if (origin) {
        try {
          const url = new URL(origin)
          if (/[\s@\\]/.test(origin) || !/^https?:\/\//i.test(origin) || !['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error()
          base = url.origin
        } catch {
          throw new AuthError('invalid_configuration')
        }
      }
      const headers: Record<string, string> = {}
      if (method === 'POST') {
        headers['Content-Type'] = 'application/json'
        headers['X-CSRFToken'] = csrfToken
      }
      const response = await fetcher(`${base}/api/auth/${route}/`, {
        method, headers, credentials: 'include', cache: 'no-store', redirect: 'error', signal: controller.signal,
        body: method === 'POST' ? JSON.stringify(payload) : undefined,
      })
      const body = await response.json().catch(() => null)
      if (!response.ok) {
        const accepted: Record<number, string[]> = {
          400: ['invalid_request'], 401: ['invalid_credentials'],
          403: ['csrf_failed', 'forbidden'], 429: ['rate_limited'],
        }
        const candidate = object(body)?.code
        const code = typeof candidate === 'string' && accepted[response.status]?.includes(candidate) ? candidate : 'invalid_response'
        if (code === 'csrf_failed') csrfToken = ''
        throw new AuthError(code, response.status)
      }
      return body as unknown
    } catch (error) {
      if (error instanceof AuthError) throw error
      throw new AuthError('unavailable')
    } finally {
      clearTimeout(timeout)
      signal?.removeEventListener('abort', abort)
    }
  }
  async function csrf(signal?: AbortSignal) {
    if (!csrfToken) {
      const body = object(await request('csrf', 'GET', undefined, signal))
      if (typeof body?.csrfToken !== 'string' || !body.csrfToken) throw new AuthError('invalid_response')
      csrfToken = body.csrfToken
    }
  }
  return {
    async session(signal?: AbortSignal) {
      return sessionUser(await request('session', 'GET', undefined, signal))
    },
    async login(identifier: string, password: string, signal?: AbortSignal) {
      await csrf(signal)
      const body = object(await request('login', 'POST', { identifier, password }, signal))
      const user = sessionUser(body)
      if (!user || typeof body?.csrfToken !== 'string' || !body.csrfToken) throw new AuthError('invalid_response')
      csrfToken = body.csrfToken
      const confirmed = sessionUser(await request('session', 'GET', undefined, signal))
      if (!confirmed || confirmed.id !== user.id) throw new AuthError('invalid_response')
      return confirmed
    },
    async logout(signal?: AbortSignal) {
      await csrf(signal)
      if (sessionUser(await request('logout', 'POST', {}, signal)) !== null) throw new AuthError('invalid_response')
      if (sessionUser(await request('session', 'GET', undefined, signal)) !== null) throw new AuthError('invalid_response')
      csrfToken = ''
    },
  }
}
