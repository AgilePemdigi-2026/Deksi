import { useState, type MouseEvent } from 'react';
import { adminLogout } from '../api';
import './admin-navigation.css';

type AdminPage = 'sources' | 'history' | 'feedback' | 'schedules' | 'monitoring' | 'analysis' | 'thresholds' | 'notifications';

export function AdminNavigation({ active, busy = false, hideLogout = false }: { active: AdminPage; busy?: boolean; hideLogout?: boolean }) {
  const [leaving, setLeaving] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const links = [
    ...(hideLogout ? [] : [{ href: '/admin/login', label: 'Keluar' }]),
    { href: '/admin/monitoring', label: 'Monitoring', page: 'monitoring' },
    { href: '/admin/sumber-data', label: 'Kelola Sumber', page: 'sources' },
    { href: '/admin/riwayat-sinkronisasi', label: 'Riwayat Sinkronisasi', page: 'history' },
    { href: '/admin/analisis', label: 'Peninjauan Analisis', page: 'analysis' },
    { href: '/admin/konfigurasi', label: 'Konfigurasi', page: 'thresholds' },
    { href: '/admin/feedback', label: 'Kelola Umpan Balik', page: 'feedback' },
    { href: '/admin/notifikasi', label: 'Notifikasi', page: 'notifications' },
    { href: '/admin/jadwal', label: 'Jadwal Pembaruan', page: 'schedules' },
  ];
  const leaveDashboard = async (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    if (busy || leaving) return;
    setLeaving(true);
    setLogoutError(null);
    try {
      await adminLogout();
      window.location.replace('/admin/login');
    } catch {
      setLogoutError('Sesi keluar belum dapat dipastikan. Periksa koneksi lalu coba kembali.');
      setLeaving(false);
    }
  };
  return <>
    <nav className="admin-navigation" aria-label="Navigasi admin" aria-describedby={busy ? 'admin-navigation-busy' : undefined}>
      {links.map(link => <a
        key={link.href}
        href={busy || leaving ? undefined : link.href}
        aria-disabled={busy || leaving ? true : undefined}
        aria-current={link.page === active ? 'page' : undefined}
        onClick={link.href === '/admin/login' ? leaveDashboard : undefined}
      >{link.label}</a>)}
    </nav>
    {busy && <p id="admin-navigation-busy" role="status">Tunggu hingga proses selesai sebelum berpindah halaman.</p>}
    {leaving && <p role="status">Mengakhiri sesi Admin…</p>}
    {logoutError && <p className="admin-navigation__error" role="alert">{logoutError}</p>}
  </>;
}
