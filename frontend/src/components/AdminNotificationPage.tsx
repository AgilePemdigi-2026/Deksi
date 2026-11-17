import { useEffect, useState } from "react";
import { AdminNavigation } from "./AdminNavigation";
import { fetchNotifications, updateNotification, type NotificationEntry } from "../api";

export function AdminNotificationPage() {
  const [items, setItems] = useState<NotificationEntry[]>([]);
  const [events, setEvents] = useState<{ kind: string; sourceId: string | null; notified: boolean; message: string; createdAt: string | null }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [dirty, setDirty] = useState<Record<string, boolean>>({});

  async function load() {
    try {
      const data = await fetchNotifications();
      setItems(data.notifications);
      setError(null);
    } catch {
      setError("Tidak dapat memuat preferensi. Pastikan login Admin.");
    }
  }
  useEffect(() => { void load(); }, []);

  async function toggle(item: NotificationEntry) {
    setMsg(null);
    try {
      const updated = await updateNotification(item.kind, !item.enabled);
      setItems((prev) => prev.map((p) => (p.kind === item.kind ? updated : p)));
      setDirty((prev) => {
        const next = { ...prev };
        delete next[item.kind];
        return next;
      });
      setMsg("Konfigurasi tersimpan");
      const data = await fetchNotifications();
      setEvents(data.events ?? []);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Gagal menyimpan");
    }
  }

  if (error) return <><AdminNavigation active="notifications" /><p className="summary-error">{error}</p></>;

  return (
    <>
      <AdminNavigation active="notifications" />
      <section aria-labelledby="notif-title">
        <p className="catalog-crumb">Admin &gt; Notifikasi</p>
        <h2 id="notif-title">Konfigurasi Notifikasi</h2>
        <p className="catalog-note">Mekanisme didukung: pencatatan event. Kanal email/Telegram belum tersedia di backend.</p>
        {msg && <p role="status">{msg}</p>}
        {Object.keys(dirty).length > 0 && <p role="status">Ada perubahan belum disimpan.</p>}
        <div className="catalog-table-wrap" role="region" aria-label="Preferensi notifikasi" tabIndex={0}>
          <table className="catalog-table">
            <thead><tr><th>NOTIFIKASI</th><th>PEMICU</th><th>STATUS</th><th>AKSI</th></tr></thead>
            <tbody>
              {items.map((n) => (
                <tr key={n.kind}>
                  <td><strong>{n.label}</strong><span className="catalog-sub">v{n.version}{n.updatedAt ? ` · ${n.updatedAt}` : ""}</span></td>
                  <td><span className="catalog-sub">{n.description}</span></td>
                  <td>{n.enabled ? "Aktif" : "Nonaktif"}</td>
                  <td><button type="button" onClick={() => void toggle(n)} aria-pressed={n.enabled}>{n.enabled ? "Nonaktifkan" : "Aktifkan"}</button></td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={4}>Memuat…</td></tr>}
            </tbody>
          </table>
        </div>
        <h3>Event terakhir</h3>
        <div className="catalog-table-wrap" role="region" aria-label="Event notifikasi" tabIndex={0}>
          <table className="catalog-table">
            <thead><tr><th>WAKTU</th><th>JENIS</th><th>SUMBER</th><th>NOTIFIKASI</th><th>PESAN</th></tr></thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={i}>
                  <td>{e.createdAt ?? "—"}</td>
                  <td>{e.kind}</td>
                  <td>{e.sourceId ?? "—"}</td>
                  <td>{e.notified ? "Aktif" : "Tercatat saja"}</td>
                  <td><span className="catalog-sub">{e.message}</span></td>
                </tr>
              ))}
              {events.length === 0 && <tr><td colSpan={5}>Belum ada event.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
