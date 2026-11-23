export function shouldReloadRestoredAdminPage(persisted: boolean, pathname: string, hash: string): boolean {
  return persisted && (
    pathname === '/admin' || pathname.startsWith('/admin/') || hash.startsWith('#/admin/')
  )
}
