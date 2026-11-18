import { useEffect, useState } from "react";
import { AdminNavigation } from "./AdminNavigation";
import { fetchNotifications, restoreDefaults, updateNotification, type NotificationEntry } from "../api";
import "./admin-source-card.css";

export function AdminNotificationPage() {
  const [items, setItems] = useState<NotificationEntry[]>([]);
  const [events, setEvents] = useState<{ kind: string; sourceId: string | null; notified: boolean; message: string; createdAt: string | null }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [dirty, setDirty] = useState<Record<string, boolean>>({});
  const [confirming, setConfirming] = useState(false);
  const [restoring, setRestoring] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await fetchNotifications();
      setItems(data.notifications);
      setEvents(data.events ?? []);
      setError(null);
    } catch {
      setError("Tidak dapat memuat preferensi. Pastikan login Admin.");
    } finally {
      setLoading(false);
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

  async function confirmRestore() {
    setRestoring(true);
    setMsg(null);
    try {
      const out = await restoreDefaults();
      setMsg(out.message || "Konfigurasi dikembalikan ke pengaturan awal");
      setConfirming(false);
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Pemulihan gagal; konfigurasi sebelumnya dipertahankan");
    } finally {
      setRestoring(false);
    }
  }

  return (
    <section className="sources-page" aria-labelledby="notif-title">
      <div className="section-head">
        <div>
          <h2 className="section-title" id="notif-title">Konfigurasi Notifikasi</h2>
          <p className="section-sub">
            Area Admin. Mekanisme didukung: pencatatan event. Kanal email/Telegram belum tersedia di backend.
          </p>
        </div>
        <span className="section-badge">Admin DEKSI</span>
      </div>

      <AdminNavigation active="notifications" />

      {loading && <p className="summary-loading">Memuat preferensi notifikasi…</p>}
      {!loading && error && <p className="summary-error">{error}</p>}

      {!loading && !error && (
        <>
          {msg && <p className="summary-loading" role="status">{msg}</p>}
          {Object.keys(dirty).length > 0 && <p className="summary-loading" role="status">Ada perubahan belum disimpan.</p>}
          {items.length === 0 ? (
            <p className="summary-empty">Belum ada preferensi notifikasi.</p>
          ) : (
            <div className="sources-grid admin-sources-grid">
              {items.map((n) => (
                <article key={n.kind} className="source-card admin-source-card">
                  <div className="admin-source-card__heading">
                    <p className="source-institution">NOTIFIKASI · {n.configured ? "TERKONFIGURASI" : "BAWAAN"}</p>
                    <p className="source-name">{n.label}</p>
                    <p className="source-desc">{n.description}</p>
                  </div>
                  <div className="admin-source-card__meta">
                    <p className="source-meta">Status: {n.enabled ? "Aktif" : "Nonaktif"}</p>
                    <p className="source-meta">Versi: v{n.version}{n.updatedAt ? ` · ${n.updatedAt}` : ""}</p>
                    {n.updatedBy && <p className="source-meta">Diubah oleh: {n.updatedBy}</p>}
                  </div>
                  <div className="admin-source-card__actions">
                    <button
                      type="button"
                      className="source-trace-link admin-source-card__review"
                      onClick={() => void toggle(n)}
                      aria-pressed={n.enabled}
                    >
                      {n.enabled ? "Nonaktifkan" : "Aktifkan"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}

          <article className="trace-panel" aria-label="Event notifikasi terakhir">
            <div className="trace-head">
              <div>
                <p className="trace-kicker">RIWAYAT EVENT</p>
                <h3 className="trace-title">Event terakhir</h3>
              </div>
            </div>
            {events.length === 0 ? (
              <p className="trace-note">Belum ada event.</p>
            ) : (
              <ul className="trace-history">
                {events.map((e, i) => (
                  <li key={i}>
                    <span>{e.createdAt ?? "—"}</span>
                    <span className="trace-history-type">{e.kind} · {e.sourceId ?? "—"}</span>
                    <span>{e.notified ? "Aktif" : "Tercatat saja"}</span>
                    <span>{e.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="trace-panel" aria-label="Pemulihan konfigurasi">
            <div className="trace-head">
              <div>
                <p className="trace-kicker">PEMULIHAN</p>
                <h3 className="trace-title">Kembalikan ke Default</h3>
              </div>
            </div>
            <p className="trace-note">
              Mengembalikan preferensi notifikasi (dan domain terjadwal bila tersedia) ke nilai bawaan.
              Formula inti, data, dan riwayat tidak diubah.
            </p>
            {!confirming && (
              <button type="button" className="source-trace-link" onClick={() => setConfirming(true)}>
                Kembalikan ke Default
              </button>
            )}
            {confirming && (
              <div role="dialog" aria-modal="true" aria-labelledby="restore-title">
                <h4 className="trace-title" id="restore-title">Kembalikan ke Default?</h4>
                <p className="trace-note">
                  Konfigurasi saat ini digantikan nilai bawaan: notifikasi, jadwal, threshold (bila tersedia).
                  Tindakan tercatat di audit log. Batal tidak mengubah apa pun.
                </p>
                <div className="admin-source-card__actions">
                  <button
                    type="button"
                    className="source-trace-link admin-source-card__review"
                    onClick={() => setConfirming(false)}
                    disabled={restoring}
                  >
                    Batal
                  </button>
                  <button
                    type="button"
                    className="source-trace-link admin-source-card__review"
                    onClick={() => void confirmRestore()}
                    disabled={restoring}
                  >
                    {restoring ? "Memulihkan…" : "Konfirmasi pemulihan"}
                  </button>
                </div>
              </div>
            )}
          </article>
        </>
      )}
    </section>
  );
}
