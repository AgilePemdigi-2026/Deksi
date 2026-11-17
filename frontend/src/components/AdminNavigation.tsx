import './admin-navigation.css';

type AdminPage = 'sources' | 'history' | 'feedback';

export function AdminNavigation({ active }: { active: AdminPage }) {
  const links = [
    { href: '/', label: 'Dashboard Publik' },
    { href: '/admin/sumber-data', label: 'Kelola Sumber', page: 'sources' },
    { href: '/admin/riwayat-sinkronisasi', label: 'Riwayat Sinkronisasi', page: 'history' },
    { href: '/admin/feedback', label: 'Kelola Umpan Balik', page: 'feedback' },
  ];
  return <nav className="admin-navigation" aria-label="Navigasi admin">
    {links.map(link => <a key={link.href} href={link.href} aria-current={link.page === active ? 'page' : undefined}>{link.label}</a>)}
  </nav>;
}
