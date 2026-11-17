import './admin-navigation.css';

type AdminPage = 'sources' | 'history' | 'feedback' | 'monitoring' | 'analysis';

export function AdminNavigation({ active, busy = false }: { active: AdminPage; busy?: boolean }) {
  const links = [
    { href: '/', label: 'Dashboard Publik' },
    { href: '/admin/monitoring', label: 'Monitoring', page: 'monitoring' },
    { href: '/admin/sumber-data', label: 'Kelola Sumber', page: 'sources' },
    { href: '/admin/riwayat-sinkronisasi', label: 'Riwayat Sinkronisasi', page: 'history' },
    { href: '/admin/analisis', label: 'Peninjauan Analisis', page: 'analysis' },
    { href: '/admin/feedback', label: 'Kelola Umpan Balik', page: 'feedback' },
  ];
  return <>
    <nav className="admin-navigation" aria-label="Navigasi admin" aria-describedby={busy ? 'admin-navigation-busy' : undefined}>
      {links.map(link => <a key={link.href} href={busy ? undefined : link.href} aria-disabled={busy ? true : undefined} aria-current={link.page === active ? 'page' : undefined}>{link.label}</a>)}
    </nav>
    {busy && <p id="admin-navigation-busy" role="status">Tunggu hingga proses selesai sebelum berpindah halaman.</p>}
  </>;
}
