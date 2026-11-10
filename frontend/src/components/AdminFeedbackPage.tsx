import React, { useCallback, useEffect, useState } from "react";
import {
  adminLogin,
  adminLogout,
  fetchAdminSession,
  fetchAdminFeedbacks,
  type AdminFeedbackItem,
} from "../api";

export function AdminFeedbackPage() {
  const [sessionChecked, setSessionChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [adminUsername, setAdminUsername] = useState("");
  const [loginUser, setLoginUser] = useState("");
  const [loginPass, setLoginPass] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);

  const [feedbacks, setFeedbacks] = useState<AdminFeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");

  useEffect(() => {
    fetchAdminSession()
      .then((session) => {
        setAuthenticated(session.authenticated);
        if (session.username) setAdminUsername(session.username);
      })
      .catch(() => setAuthenticated(false))
      .finally(() => setSessionChecked(true));
  }, []);

  const loadFeedbacks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAdminFeedbacks({
        status: selectedStatus,
        category: selectedCategory,
      });
      setFeedbacks(res.feedbacks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuat daftar umpan balik.");
    } finally {
      setLoading(false);
    }
  }, [selectedStatus, selectedCategory]);

  useEffect(() => {
    if (!authenticated) return;
    const timer = setTimeout(() => {
      void loadFeedbacks();
    }, 250);
    return () => clearTimeout(timer);
  }, [authenticated, loadFeedbacks]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      await adminLogin(loginUser, loginPass);
      setAuthenticated(true);
      setAdminUsername(loginUser);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Login gagal. Periksa username dan password.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await adminLogout();
    } finally {
      setAuthenticated(false);
      setFeedbacks([]);
    }
  };

  const formatDateTime = (iso: string | null) => {
    if (!iso) return "-";
    const date = new Date(iso);
    return date.toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "pending":
        return "badge-status-pending";
      case "in_review":
        return "badge-status-review";
      case "resolved":
        return "badge-status-resolved";
      case "rejected":
        return "badge-status-rejected";
      default:
        return "";
    }
  };

  if (!sessionChecked) {
    return (
      <div className="admin-fb-container">
        <p className="admin-fb-loading">Memeriksa sesi administrator…</p>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="admin-fb-container">
        <div className="admin-fb-login-box">
          <div className="admin-fb-login-header">
            <h2>DEKSI · Portal Admin</h2>
            <p>Masuk untuk mengelola daftar laporan umpan balik pengguna.</p>
          </div>
          {loginError && <div className="admin-fb-alert error">{loginError}</div>}
          <form onSubmit={handleLogin} className="admin-fb-form">
            <div className="admin-fb-form-group">
              <label htmlFor="admin-user">Username</label>
              <input
                id="admin-user"
                type="text"
                value={loginUser}
                onChange={(e) => setLoginUser(e.target.value)}
                required
                placeholder="mis. admin"
              />
            </div>
            <div className="admin-fb-form-group">
              <label htmlFor="admin-pass">Kata Sandi</label>
              <input
                id="admin-pass"
                type="password"
                value={loginPass}
                onChange={(e) => setLoginPass(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>
            <button type="submit" disabled={loginLoading} className="admin-fb-btn primary full">
              {loginLoading ? "Memproses…" : "Masuk ke Panel Admin"}
            </button>
          </form>
          <div style={{ marginTop: "1.5rem", textAlign: "center" }}>
            <a href="/" className="admin-fb-link">← Kembali ke Beranda Publik</a>
          </div>
        </div>
      </div>
    );
  }

  const hasFilters = selectedStatus !== "all" || selectedCategory !== "all";

  return (
    <div className="admin-fb-container">
      <header className="admin-fb-header">
        <div>
          <span className="admin-fb-eyebrow">PORTAL ADMINISTRASI DEKSI</span>
          <h1 className="admin-fb-title">Daftar Laporan Umpan Balik</h1>
          <p className="admin-fb-subtitle">
            Daftar kritik, verifikasi data, dan saran dari publik.
          </p>
        </div>
        <div className="admin-fb-actions">
          <a href="/#/admin/sumber" className="admin-fb-btn secondary">
            Kelola Sumber Data
          </a>
          <a href="/" className="admin-fb-btn secondary">
            Lihat Dashboard Publik
          </a>
          <button onClick={handleLogout} className="admin-fb-btn outline danger">
            Keluar ({adminUsername || "Admin"})
          </button>
        </div>
      </header>

      <section className="admin-fb-toolbar" aria-label="Filter daftar umpan balik">
        <div className="admin-fb-filters">
          <div className="admin-fb-filter-group">
            <label htmlFor="filter-status">Status:</label>
            <select
              id="filter-status"
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              <option value="all">Semua Status</option>
              <option value="pending">Menunggu Ditinjau</option>
              <option value="in_review">Sedang Ditinjau</option>
              <option value="resolved">Diselesaikan</option>
              <option value="rejected">Ditolak</option>
            </select>
          </div>
          <div className="admin-fb-filter-group">
            <label htmlFor="filter-category">Kategori:</label>
            <select
              id="filter-category"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="all">Semua Kategori</option>
              <option value="data_error">Kesalahan Data</option>
              <option value="methodology">Metodologi / Penjelasan</option>
              <option value="visualization">Visualisasi</option>
              <option value="source">Sumber Data</option>
              <option value="other">Lainnya</option>
            </select>
          </div>
          {hasFilters && (
            <button
              className="admin-fb-btn text"
              onClick={() => {
                setSelectedStatus("all");
                setSelectedCategory("all");
              }}
            >
              Reset Filter
            </button>
          )}
        </div>
      </section>

      <main className="admin-fb-main">
        {error && (
          <div className="admin-fb-alert error" role="alert">
            <span>{error}</span>
            <button onClick={() => void loadFeedbacks()} className="admin-fb-btn secondary small">
              Coba Lagi
            </button>
          </div>
        )}

        {loading ? (
          <div className="admin-fb-empty-state">
            <p>Memuat daftar laporan pengguna…</p>
          </div>
        ) : feedbacks.length === 0 ? (
          <div className="admin-fb-empty-state">
            {hasFilters ? (
              <>
                <h3>Tidak Ada Laporan yang Cocok</h3>
                <p>Tidak ditemukan laporan dengan status dan kategori yang dipilih.</p>
                <button
                  onClick={() => {
                    setSelectedStatus("all");
                    setSelectedCategory("all");
                  }}
                  className="admin-fb-btn secondary"
                >
                  Reset Filter
                </button>
              </>
            ) : (
              <>
                <h3>Belum Ada Laporan Masuk</h3>
                <p>Laporan yang dikirim oleh publik dari dashboard akan muncul di halaman ini.</p>
              </>
            )}
          </div>
        ) : (
          <div className="admin-fb-table-wrap">
            <div className="admin-fb-meta-info">
              <span>Menampilkan {feedbacks.length} laporan umpan balik</span>
            </div>
            <table className="admin-fb-table">
              <thead>
                <tr>
                  <th style={{ width: "60px" }}>ID</th>
                  <th style={{ width: "140px" }}>Kategori</th>
                  <th>Uraian Laporan</th>
                  <th style={{ width: "160px" }}>Pengirim</th>
                  <th style={{ width: "120px" }}>Indikator</th>
                  <th style={{ width: "130px" }}>Tanggal</th>
                  <th style={{ width: "140px" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {feedbacks.map((fb) => (
                  <tr key={fb.id}>
                    <td className="cell-id">#{fb.id}</td>
                    <td>
                      <span className="badge-category">{fb.category_label}</span>
                    </td>
                    <td>
                      <div className="cell-desc-title">{fb.description}</div>
                      {fb.admin_notes && (
                        <div className="cell-desc-notes">
                          <em>Catatan admin:</em> {fb.admin_notes}
                        </div>
                      )}
                    </td>
                    <td>
                      <div className="cell-sender-name">{fb.sender_name || "Anonim"}</div>
                      {fb.sender_email && (
                        <div className="cell-sender-email">{fb.sender_email}</div>
                      )}
                    </td>
                    <td>
                      {fb.related_indicator_code ? (
                        <span className="badge-indicator">
                          {fb.related_indicator_code.toUpperCase()}
                          {fb.related_period ? ` (${fb.related_period})` : ""}
                        </span>
                      ) : (
                        <span className="cell-muted">-</span>
                      )}
                    </td>
                    <td className="cell-date">{formatDateTime(fb.created_at)}</td>
                    <td>
                      <span className={`badge-status ${getStatusBadgeClass(fb.status)}`}>
                        {fb.status_label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
