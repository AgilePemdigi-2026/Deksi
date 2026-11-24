export function shouldRedirectRestoredAdminPage(persisted: boolean, pathname: string, hash: string): boolean {
  if (!persisted) return false
  const path = pathname.replace(/\/+$/, '') || '/'
  if (['/admin/login', '/admin/forgot-password', '/admin/reset-password'].includes(path)) return false
  return path === '/admin' || path.startsWith('/admin/') || hash.startsWith('#/admin/')
}
