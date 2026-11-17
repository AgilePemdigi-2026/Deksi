import { useEffect, useState } from "react";
import { AdminNavigation } from "./AdminNavigation";
import { fetchMonitoringHistory, fetchMonitoringSources, fetchMonitoringSummary, type MonitoringSource, type MonitoringSummary } from "../api";

export function AdminMonitoringPage() {
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [sources, setSources] = useState<MonitoringSource[]>([]);
  const [history, setHistory] = useState<{ id: string; sourceId: string | null; status: string; startedAt: string | null; message: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("Semua");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, src, hist] = await Promise.all([
          fetchMonitoringSummary(),
          fetchMonitoringSources(),
          fetchMonitoringHistory({ page: 1, pageSize: 20 }),
        ]);
        if (!cancelled) { setSummary(s); setSources(src); setHistory(hist.items); setError(null); }
      } catch {
        if (!cancelled) setError("Tidak dapat memuat monitoring. Pastikan login Admin.");
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) return <><AdminNavigation active="monitoring" /><p className="summary-error">{error}</p></>;
  if (!summary) return <><AdminNavigation active="monitoring" /><p className="summary-loading">Memuat monitoring…</p></>;

  const q = filter.trim().toLowerCase();
  const rows = sources.filter((s) => {
    if (statusFilter !== "Semua" && (s.lastSyncStatus ?? "-") !== statusFilter) return false;
    if (!q) return true;
    return `${s.sourceName} ${s.sourceId} ${s.institution}`.toLowerCase().includes(q);
  });

  return (
    <>
      <AdminNavigation active="monitoring" />
      <section aria-labelledby="monitoring-title">
        <p className="catalog-crumb">Admin &gt; Monitoring</p>
        <h2 id="monitoring-title">Dashboard Monitoring Admin</h2>
        <div className="catalog-stats">
          <div className="catalog-stat"><p>TOTAL SUMBER</p><strong>{summary.totalSources}</strong></div>
          <div className="catalog-stat"><p>AKTIF</p><strong>{summary.activeSources}</strong></div>
          <div className="catalog-stat"><p>NONAKTIF</p><strong>{summary.inactiveSources}</strong></div>
          <div className="catalog-stat"><p>SINKRON BERHASIL</p><strong>{summary.syncSuccess}</strong></div>
          <div className="catalog-stat"><p>SINKRON GAGAL</p><strong>{summary.syncFailed}</strong></div>
          <div className="catalog-stat"><p>BERJALAN</p><strong>{summary.syncRunning}</strong></div>
          <div className="catalog-stat"><p>KUALITAS</p><strong>{summary.quality.label}</strong><span>{summary.quality.validated}/{summary.quality.total} tervalidasi</span></div>
          <div className="catalog-stat"><p>PEMBARUAN TERAKHIR</p><strong>{summary.lastUpdateAt ?? summary.lastSyncAt ?? "—"}</strong></div>
        </div>

        <div className="catalog-explore-head">
          <h3>Tabel monitoring sumber</h3>
          <span className="catalog-count">● {rows.length} sumber</span>
        </div>
        <div className="catalog-filters">
          <label>Cari<input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Nama / institusi…" /></label>
          <label>Status<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option>Semua</option><option>success</option><option>failed</option><option>running</option>
          </select></label>
        </div>
        <div className="catalog-table-wrap" role="region" aria-label="Tabel monitoring" tabIndex={0}>
          <table className="catalog-table">
            <thead><tr><th>SUMBER</th><th>AKTIF</th><th>SINKRON TERAKHIR</th><th>PERIODE</th><th>JADWAL</th><th>STATUS DATA</th></tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.sourceId}>
                  <td><strong>{s.sourceName}</strong><span className="catalog-sub">{s.institution} · {s.sourceId}</span></td>
                  <td>{s.active ? "Aktif" : "Nonaktif"}</td>
                  <td><strong>{s.lastSyncStatus ?? "—"}</strong><span className="catalog-sub">{s.lastSyncAt ?? ""}</span></td>
                  <td>{s.lastPeriod ?? "—"}</td>
                  <td>{s.updateSchedule || "—"}</td>
                  <td><span className="catalog-sub">{s.lastSyncMessage || `${s.observationCount} observasi`}</span></td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={6}>Tidak ada sumber untuk filter ini.</td></tr>}
            </tbody>
          </table>
        </div>

        <h3>Riwayat pemrosesan</h3>
        <div className="catalog-table-wrap" role="region" aria-label="Riwayat pemrosesan" tabIndex={0}>
          <table className="catalog-table">
            <thead><tr><th>WAKTU</th><th>SUMBER</th><th>STATUS</th><th>PESAN</th></tr></thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{h.startedAt ?? "—"}</td>
                  <td>{h.sourceId ?? "—"}</td>
                  <td>{h.status}</td>
                  <td><span className="catalog-sub">{h.message}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
