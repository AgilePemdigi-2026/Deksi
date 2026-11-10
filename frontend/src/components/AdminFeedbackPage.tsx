import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  adminLogin,
  adminLogout,
  fetchAdminSession,
  fetchAdminFeedbacks,
  fetchAdminFeedbackDetail,
  updateAdminFeedbackStatus,
  type AdminFeedbackItem,
  type AdminFeedbackDetail,
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
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedFeedbackId, setSelectedFeedbackId] = useState<number | null>(null);
  const [detail, setDetail] = useState<AdminFeedbackDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const detailRequestId = useRef(0);
  const [newStatus, setNewStatus] = useState("");
  const [handlingNotes, setHandlingNotes] = useState("");
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [statusUpdateMessage, setStatusUpdateMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const feedbackRequestId = useRef(0);

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
    const requestId = ++feedbackRequestId.current;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAdminFeedbacks({
        search: searchQuery,
        status: selectedStatus,
        category: selectedCategory,
      });
      if (feedbackRequestId.current === requestId) setFeedbacks(res.feedbacks);
    } catch (err) {
      if (feedbackRequestId.current === requestId) {
        setError(err instanceof Error ? err.message : "Gagal memuat daftar umpan balik.");
      }
    } finally {
      if (feedbackRequestId.current === requestId) setLoading(false);
    }
  }, [searchQuery, selectedStatus, selectedCategory]);

  useEffect(() => {
    if (!authenticated) return;
    const timer = setTimeout(() => {
      void loadFeedbacks();
    }, 250);
    return () => clearTimeout(timer);
  }, [authenticated, loadFeedbacks]);

  const handleOpenDetail = async (id: number) => {
    const requestId = ++detailRequestId.current;
    setSelectedFeedbackId(id);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await fetchAdminFeedbackDetail(id);
      if (detailRequestId.current !== requestId) return;
      setDetail(data);
      setNewStatus(data.status);
      setHandlingNotes(data.admin_notes || "");
      setStatusUpdateMessage(null);
      setFeedbacks((current) =>
        current.map((item) =>
          item.id === data.id
            ? { ...item, status: data.status, status_label: data.status_label }
            : item,
        ),
      );
    } catch (err) {
      if (detailRequestId.current === requestId) {
        setDetailError(err instanceof Error ? err.message : "Gagal memuat detail laporan.");
      }
    } finally {
      if (detailRequestId.current === requestId) setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    if (statusUpdating) return;
    detailRequestId.current += 1;
    setSelectedFeedbackId(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(false);
    setStatusUpdateMessage(null);
  };

  const handleUpdateStatus = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!detail) return;
    const requestId = detailRequestId.current;
    if (!newStatus) {
      setStatusUpdateMessage({ type: "error", text: "Silakan pilih status penanganan." });
      return;
    }

    setStatusUpdating(true);
    setStatusUpdateMessage(null);
    try {
      const updated = await updateAdminFeedbackStatus(detail.id, {
        status: newStatus,
        notes: handlingNotes,
        csrfToken: detail.csrfToken,
      });
      if (detailRequestId.current !== requestId) return;
      setDetail(updated);
      setStatusUpdateMessage({ type: "success", text: "Status dan catatan berhasil disimpan." });
      await loadFeedbacks();
    } catch (err) {
      if (detailRequestId.current === requestId) {
        setStatusUpdateMessage({
          type: "error",
          text: err instanceof Error ? err.message : "Gagal memperbarui status umpan balik.",
        });
      }
    } finally {
      if (detailRequestId.current === requestId) setStatusUpdating(false);
    }
  };

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
      feedbackRequestId.current += 1;
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

  const formatDetailDateTime = (iso: string | null) => {
    if (!iso) return "-";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return formatDateTime(iso);
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

  const hasFilters = Boolean(searchQuery.trim()) || selectedStatus !== "all" || selectedCategory !== "all";

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
        <div className="admin-fb-search-wrap">
          <span className="admin-fb-search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            className="admin-fb-search-input"
            placeholder="Cari deskripsi, pengirim, email, indikator, atau periode…"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            aria-label="Cari umpan balik"
          />
          {searchQuery && (
            <button
              type="button"
              className="admin-fb-search-clear"
              onClick={() => setSearchQuery("")}
              aria-label="Hapus pencarian"
            >
              ×
            </button>
          )}
        </div>
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
                setSearchQuery("");
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
                <h3>Tidak Ada Hasil yang Cocok</h3>
                <p>
                  {searchQuery.trim()
                    ? `Tidak ditemukan laporan untuk kata kunci "${searchQuery.trim()}".`
                    : "Tidak ditemukan laporan dengan status dan kategori yang dipilih."}
                </p>
                <button
                  onClick={() => {
                    setSelectedStatus("all");
                    setSelectedCategory("all");
                    setSearchQuery("");
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
                  <th style={{ width: "100px", textAlign: "center" }}>Aksi</th>
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
                    <td style={{ textAlign: "center" }}>
                      <button
                        type="button"
                        onClick={() => void handleOpenDetail(fb.id)}
                        className="admin-fb-btn small primary"
                      >
                        Detail
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {selectedFeedbackId !== null && (
        <div
          className="admin-fb-modal-overlay"
          onClick={handleCloseDetail}
        >
          <section
            className="admin-fb-modal-content"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="feedback-detail-title"
          >
            <header className="admin-fb-modal-header">
              <div>
                <span className="admin-fb-eyebrow">DETAIL LAPORAN UMPAN BALIK</span>
                <h2 id="feedback-detail-title">Laporan #{selectedFeedbackId}</h2>
              </div>
              <button
                type="button"
                className="admin-fb-modal-close"
                onClick={handleCloseDetail}
                disabled={statusUpdating}
                aria-label="Tutup detail"
              >
                ×
              </button>
            </header>
            <div className="admin-fb-modal-body">
              {detailLoading ? (
                <p>Memuat detail laporan…</p>
              ) : detailError ? (
                <div className="admin-fb-alert error" role="alert">{detailError}</div>
              ) : detail ? (
                <>
                  <section className="admin-fb-detail-card">
                    <div className="admin-fb-detail-banner">
                      <div>
                        <span className="detail-meta-label">Status</span>
                        <span className={`badge-status ${getStatusBadgeClass(detail.status)}`}>
                          {detail.status_label}
                        </span>
                      </div>
                      <div>
                        <span className="detail-meta-label">Dikirim pada</span>
                        <strong>{formatDetailDateTime(detail.created_at)}</strong>
                      </div>
                    </div>
                    <h3>Isi Laporan</h3>
                    <div className="detail-desc-box">{detail.description}</div>
                    <div className="detail-meta-grid">
                      <div>
                        <span className="detail-meta-label">Kategori</span>
                        <p className="detail-meta-val">{detail.category_label}</p>
                      </div>
                      <div>
                        <span className="detail-meta-label">Pengirim</span>
                        <p className="detail-meta-val">
                          {detail.sender_name || "Anonim"}
                          {detail.sender_email ? ` (${detail.sender_email})` : ""}
                        </p>
                      </div>
                      <div>
                        <span className="detail-meta-label">Terakhir diperbarui</span>
                        <p className="detail-meta-val">{formatDetailDateTime(detail.updated_at)}</p>
                      </div>
                      <div>
                        <span className="detail-meta-label">Catatan admin</span>
                        <p className="detail-meta-val">{detail.admin_notes || "-"}</p>
                      </div>
                    </div>
                  </section>
                  <section className="admin-fb-detail-card">
                    <h3>Indikator Terkait</h3>
                    {detail.related_indicator ? (
                      <div className="detail-indicator-box">
                        <div className="detail-indicator-header">
                          <span className="badge-indicator-code">
                            {detail.related_indicator.code.toUpperCase()}
                          </span>
                          <h4>{detail.related_indicator.name}</h4>
                        </div>
                        <div className="detail-indicator-props">
                          <span><strong>Kategori:</strong> {detail.related_indicator.category}</span>
                          <span><strong>Satuan:</strong> {detail.related_indicator.unit}</span>
                          {detail.related_period && (
                            <span><strong>Periode:</strong> {detail.related_period}</span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="cell-muted">Laporan ini tidak mengaitkan indikator spesifik.</p>
                    )}
                  </section>
                  <section className="admin-fb-detail-card highlight">
                    <h3>Tindak Lanjut dan Perubahan Status</h3>
                    {statusUpdateMessage && (
                    <div className={`admin-fb-alert ${statusUpdateMessage.type}`} role="status">
                      {statusUpdateMessage.text}
                    </div>
                    )}
                    <form onSubmit={handleUpdateStatus} className="admin-fb-form">
                    <div className="admin-fb-form-group">
                      <label htmlFor="feedback-new-status">Status Baru</label>
                      <select
                        id="feedback-new-status"
                        value={newStatus}
                        onChange={(event) => setNewStatus(event.target.value)}
                        required
                      >
                        <option value="pending">Menunggu Ditinjau</option>
                        <option value="in_review">Sedang Ditinjau</option>
                        <option value="resolved">Diselesaikan</option>
                        <option value="rejected">Ditolak</option>
                      </select>
                    </div>
                    <div className="admin-fb-form-group">
                      <label htmlFor="feedback-handling-notes">Catatan Penanganan</label>
                      <textarea
                        id="feedback-handling-notes"
                        rows={3}
                        maxLength={2000}
                        value={handlingNotes}
                        onChange={(event) => setHandlingNotes(event.target.value)}
                        placeholder="Catatan tindakan atau alasan (opsional)"
                      />
                    </div>
                    <div className="admin-fb-status-actions">
                      <span className="cell-muted">{handlingNotes.length}/2000 karakter</span>
                      <button
                        type="submit"
                        className="admin-fb-btn primary"
                        disabled={statusUpdating || !detail}
                      >
                        {statusUpdating ? "Menyimpan…" : "Simpan Status"}
                      </button>
                    </div>
                    </form>
                  </section>
                  <section className="admin-fb-detail-card">
                    <h3>Riwayat Perubahan Status</h3>
                    {detail.audit_logs.length === 0 ? (
                    <p className="cell-muted">Belum ada riwayat perubahan status.</p>
                    ) : (
                    <div className="admin-fb-timeline">
                      {detail.audit_logs.map((log) => (
                        <article key={log.id} className="timeline-item">
                          <div className="timeline-content">
                            <div className="timeline-header">
                              <span>
                                <strong>{log.old_status_label}</strong> →{" "}
                                <strong>{log.new_status_label}</strong>
                              </span>
                              <span className="timeline-date">{formatDateTime(log.changed_at)}</span>
                            </div>
                            {log.notes && <p className="timeline-notes">{log.notes}</p>}
                            <span className="timeline-actor">Oleh: {log.changed_by}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                    )}
                  </section>
                </>
              ) : null}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
