import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchAdminSession } from '../../api'

export function AdminSessionGuard({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'checking' | 'authenticated' | 'signed-out' | 'error'>('checking')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let active = true
    fetchAdminSession().then(session => {
      if (active) setState(session.authenticated ? 'authenticated' : 'signed-out')
    }).catch(() => {
      if (active) setState('error')
    })
    return () => { active = false }
  }, [retry])

  useEffect(() => {
    if (state === 'signed-out') window.location.replace('/admin/login')
  }, [state])

  if (state === 'authenticated') return children
  if (state === 'error') {
    return <main className="admin-operations">
      <p className="admin-operations__state" role="alert">Sesi Admin tidak dapat diverifikasi. Halaman tetap terkunci.</p>
      <button type="button" onClick={() => { setState('checking'); setRetry(value => value + 1) }}>Coba lagi</button>
    </main>
  }
  return <main className="admin-operations"><p className="admin-operations__state" role="status">
    {state === 'signed-out' ? 'Sesi berakhir. Kembali ke login…' : 'Memeriksa sesi Admin…'}
  </p></main>
}
