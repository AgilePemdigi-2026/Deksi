import { useEffect, useState } from "react";
import { AdminNavigation } from "./AdminNavigation";
import { fetchSchedules, updateSchedule, type ScheduleEntry } from "../api";
import "./admin-operations.css";

export function AdminSchedulePage() {
  const [items, setItems] = useState<ScheduleEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Record<string, { interval: string; runTime: string; enabled: boolean }>>({});
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    try {
      setItems(await fetchSchedules());
      setError(null);
    } catch {
      setError("Tidak dapat memuat jadwal. Pastikan login Admin.");
    }
  }
  useEffect(() => { void load(); }, []);

  async function save(s: ScheduleEntry) {
    const draft = editing[s.sourceId] ?? { interval: String(s.intervalDays), runTime: s.runTime ?? "", enabled: s.enabled };
    setMsg(null);
    try {
      await updateSchedule(s.sourceId, {
        intervalDays: Number(draft.interval),
        runTime: draft.runTime || null,
        enabled: draft.enabled,
      });
      setMsg("Konfigurasi tersimpan");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Gagal menyimpan");
    }
  }

  if (error) return <main className="admin-operations"><AdminNavigation active="schedules" /><p className="admin-operations__state" role="alert">{error}</p></main>;

  return (
    <main className="admin-operations">
      <AdminNavigation active="schedules" />
      <section aria-labelledby="sched-title">
        <p className="catalog-crumb">Admin &gt; Jadwal Pembaruan</p>
        <h2 id="sched-title">Konfigurasi Jadwal Pembaruan</h2>
        <p className="catalog-note">Jadwal mengikuti rilis resmi sumber, bukan real-time. Perubahan aman, tidak ganggu akuisisi berjalan.</p>
        {msg && <p role="status">{msg}</p>}
        <div className="catalog-table-wrap" role="region" aria-label="Jadwal" tabIndex={0}>
          <table className="catalog-table">
            <thead><tr><th>SUMBER</th><th>JADWAL SAAT INI</th><th>INTERVAL (HARI)</th><th>JAM</th><th>AKTIF</th><th>BERIKUTNYA</th><th>AKSI</th></tr></thead>
            <tbody>
              {items.map((s) => {
                const d = editing[s.sourceId] ?? { interval: String(s.intervalDays), runTime: s.runTime ?? "", enabled: s.enabled };
                return (
                  <tr key={s.sourceId}>
                    <td><strong>{s.sourceName}</strong><span className="catalog-sub">{s.institution} · {s.sourceId}</span></td>
                    <td><span className="catalog-sub">{s.currentScheduleText || "—"}</span></td>
                    <td><input value={d.interval} onChange={(e) => setEditing({ ...editing, [s.sourceId]: { ...d, interval: e.target.value } })} inputMode="numeric" aria-label={`Interval ${s.sourceId}`} /></td>
                    <td><input value={d.runTime} onChange={(e) => setEditing({ ...editing, [s.sourceId]: { ...d, runTime: e.target.value } })} placeholder="HH:MM" aria-label={`Jam ${s.sourceId}`} /></td>
                    <td><input type="checkbox" checked={d.enabled} onChange={(e) => setEditing({ ...editing, [s.sourceId]: { ...d, enabled: e.target.checked } })} aria-label={`Aktif ${s.sourceId}`} /></td>
                    <td>{s.nextRun ?? "—"}</td>
                    <td><button type="button" onClick={() => void save(s)}>Simpan</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
