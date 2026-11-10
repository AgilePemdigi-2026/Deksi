export type LoginErrors = { identifier?: string; password?: string }

export function validateLogin(identifier: string, password: string): LoginErrors {
  const errors: LoginErrors = {}
  if (!identifier.trim()) errors.identifier = 'Masukkan email atau nama pengguna.'
  if (!password.length) errors.password = 'Masukkan kata sandi.'
  return errors
}
