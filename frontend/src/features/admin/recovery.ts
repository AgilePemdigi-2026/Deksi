export type ResetCredentials = { uid: string; token: string }
export type PasswordField = 'newPassword' | 'confirmPassword'
export type PasswordErrors = Partial<Record<PasswordField, string[]>>
export type RecoveryService = {
  request(email: string, signal?: AbortSignal): Promise<void>
  check(credentials: ResetCredentials, signal?: AbortSignal): Promise<void>
  confirm(credentials: ResetCredentials, newPassword: string, confirmPassword: string, signal?: AbortSignal): Promise<void>
}

export class RecoveryError extends Error {
  code: string
  fields: PasswordErrors
  constructor(code: string, fields: PasswordErrors = {}) {
    super('Recovery request could not be completed')
    this.code = code
    this.fields = fields
  }
}

// Explicit disconnected service for isolated previews or callers without an adapter.
const notConnected = () => Promise.reject(new RecoveryError('not_connected'))
export const unavailableRecovery: RecoveryService = { request: notConnected, check: notConnected, confirm: notConnected }

export function parseResetCredentials(fragment: string): ResetCredentials | null {
  if (fragment.length > 1024) return null
  const params = new URLSearchParams(fragment.replace(/^#/, ''))
  if ([...params.keys()].length !== 2 || params.getAll('uid').length !== 1 || params.getAll('token').length !== 1) return null
  const uid = params.get('uid')
  const token = params.get('token')
  if (!uid || !token || !/^[A-Za-z0-9_-]{1,256}$/.test(uid) || !/^[A-Za-z0-9_-]{1,256}$/.test(token)) return null
  return { uid, token }
}
