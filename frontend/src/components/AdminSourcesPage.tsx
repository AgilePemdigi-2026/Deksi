import { useEffect, useRef, useState } from "react";
import ResyncAction from "../features/resync/ResyncAction";
import {
  adminLogin,
  adminLogout,
  createAdminSource,
  displayOrUnavailable,
  fetchAcquisitionMethods,
  fetchAdminSession,
  fetchAdminSourceDetail,
  fetchAdminSourceRevisions,
  fetchAdminSources,
  updateAdminSource,
  type AcquisitionMethod,
  type AdminRevision,
  type AdminSourceEntry,
} from "../api";

const EMPTY_FORM = {
  sourceId: "",
  sourceName: "",
  institution: "",
  primaryUrl: "",
  description: "",
  acquisitionMethod: "",
  endpointUrl: "",
  dataFormat: "",
  frequency: "",
  updateSchedule: "",
  status: "active",
};

function isValidHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function AdminSourcesPage() {
  const editRequest = useRef(0);
  const toggleBusy = useRef(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  const [sources, setSources] = useState<AdminSourceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [methods, setMethods] = useState<AcquisitionMethod[]>([]);
  const [frequencies, setFrequencies] = useState<string[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [mode, setMode] = useState<"add" | "edit">("add");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [revisions, setRevisions] = useState<AdminRevision[]>([]);
  const [revisionsLoading, setRevisionsLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [initialForm, setInitialForm] = useState<typeof EMPTY_FORM | null>(null);
  const [initialRevision, setInitialRevision] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [toggleError, setToggleError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  const reload = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, meta] = await Promise.all([fetchAdminSources(), fetchAcquisitionMethods()]);
      setSources(rows);
      setMethods(meta.methods);
      setFrequencies(meta.frequencies);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tidak dapat memuat sumber.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminSession()
      .then((s) => {
        setAuthenticated(s.authenticated);
        if (s.authenticated) void reload();
        else setLoading(false);
      })
      .catch(() => setLoading(false))
      .finally(() => setSessionChecked(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doLogin = async () => {
    setLoginLoading(true);
    setLoginError(null);
    try {
      await adminLogin(username.trim(), password);
      setAuthenticated(true);
      setPassword("");
      await reload();
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "Login gagal.");
    } finally {
      setLoginLoading(false);
    }
  };

  const doLogout = async () => {
    setLogoutLoading(true);
    setLogoutError(null);
    try {
      await adminLogout();
      editRequest.current += 1;
      setAuthenticated(false);
      setSources([]);
    } catch {
      setLogoutError("Sesi keluar belum dapat dipastikan. Periksa koneksi lalu coba kembali.");
    } finally {
      setLogoutLoading(false);
    }
  };

  const set = (key: keyof typeof EMPTY_FORM, value: string) => {
    setForm((f) => ({ ...f, [key]: value }));
    setDirty(true);
    setSuccess(null);
  };

  const activeMethod = methods.find((m) => m.value === form.acquisitionMethod);
  const allowedFormats = activeMethod?.formats ?? [];

  const validate = (): string | null => {
    if (mode === "add") {
      if (!form.sourceId.trim()) return "Source ID wajib diisi.";
      if (!/^[A-Za-z0-9_]{2,32}$/.test(form.sourceId.trim()))
        return "Source ID 2–32 karakter: huruf, angka, garis bawah.";
    }
    if (!form.sourceName.trim() || !form.institution.trim())
      return "Nama sumber dan institusi wajib diisi.";
    if (!form.primaryUrl.trim() || !isValidHttpUrl(form.primaryUrl.trim()))
      return "Portal resmi harus URL http(s) yang valid.";
    if (!form.acquisitionMethod) return "Metode akuisisi wajib dipilih.";
    if (!form.dataFormat) return "Format data wajib dipilih.";
    if (activeMethod && !allowedFormats.includes(form.dataFormat))
      return `Format tidak sesuai metode. Valid: ${allowedFormats.join(", ")}.`;
    if (!form.frequency) return "Frekuensi pembaruan wajib dipilih.";
    if (activeMethod?.endpointRequired && !form.endpointUrl.trim())
      return `Metode ${activeMethod.label} membutuhkan endpoint URL.`;
    if (form.endpointUrl.trim() && !isValidHttpUrl(form.endpointUrl.trim()) && !form.endpointUrl.startsWith("file://"))
      return "Endpoint harus URL http(s) valid atau path file://.";
    return null;
  };

  const submit = async () => {
    if (mode === "edit" && (initialForm === null || initialRevision === null)) {
      setFormError("Detail sumber belum tersedia. Buka kembali sebelum menyimpan.");
      return;
    }
    const statusOnly = mode === "edit" && initialForm !== null && form.status !== initialForm.status &&
      (Object.keys(EMPTY_FORM) as (keyof typeof EMPTY_FORM)[])
        .filter((key) => key !== "status").every((key) => form[key] === initialForm[key]);
    const problem = statusOnly ? null : validate();
    if (problem) {
      setFormError(problem);
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      if (mode === "edit" && editingId) {
        const result = await updateAdminSource(editingId, statusOnly ? { status: form.status, expectedRevision: initialRevision! } : {
          expectedRevision: initialRevision!,
          sourceName: form.sourceName.trim(),
          institution: form.institution.trim(),
          primaryUrl: form.primaryUrl.trim(),
          description: form.description.trim(),
          acquisitionMethod: form.acquisitionMethod,
          endpointUrl: form.endpointUrl.trim(),
          dataFormat: form.dataFormat,
          frequency: form.frequency,
          updateSchedule: form.updateSchedule.trim(),
          status: form.status,
        });
        if (result.changedFields && result.changedFields.length > 0) {
          setSuccess(
            `Sumber ${editingId} direvisi (v${result.revision?.version}). Ubah: ${result.changedFields.join(", ")}. Berlaku pada siklus akuisisi berikutnya.`,
          );
        } else {
          setSuccess(`Tidak ada perubahan pada ${editingId}. Konfigurasi tetap.`);
        }
      } else {
        const created = await createAdminSource({
          sourceId: form.sourceId.trim().toUpperCase(),
          sourceName: form.sourceName.trim(),
          institution: form.institution.trim(),
          primaryUrl: form.primaryUrl.trim(),
          description: form.description.trim(),
          acquisitionMethod: form.acquisitionMethod,
          endpointUrl: form.endpointUrl.trim(),
          dataFormat: form.dataFormat,
          frequency: form.frequency,
          updateSchedule: form.updateSchedule.trim(),
          status: form.status,
        });
        setSuccess(`Sumber ${created.sourceId} berhasil ditambahkan. Berlaku pada siklus akuisisi berikutnya.`);
      }
      resetForm();
      await reload();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Penyimpanan gagal.");
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    editRequest.current += 1;
    setDetailLoading(false);
    setRevisionsLoading(false);
    setShowForm(false);
    setMode("add");
    setEditingId(null);
    setForm(EMPTY_FORM);
    setInitialForm(null);
    setInitialRevision(null);
    setDirty(false);
    setFormError(null);
    setRevisions([]);
  };

  const cancelForm = () => {
    if (dirty && !window.confirm("Batalkan? Perubahan form akan hilang.")) return;
    resetForm();
  };

  const startAdd = () => {
    resetForm();
    setShowForm(true);
    setSuccess(null);
  };

  const toggleSource = async (source: AdminSourceEntry) => {
    if (toggleBusy.current || showForm || !["active", "inactive"].includes(source.status)) return;
    toggleBusy.current = true;
    setToggling(true);
    setToggleError(null);
    setSuccess(null);
    try {
      const detail = await fetchAdminSourceDetail(source.sourceId);
      if (detail.status !== source.status || !Number.isInteger(detail.revisionVersion)) {
        throw new Error("Status sumber berubah. Muat ulang sebelum mencoba kembali.");
      }
      const status = detail.status === "active" ? "inactive" : "active";
      await updateAdminSource(source.sourceId, {status, expectedRevision: detail.revisionVersion});
      setSuccess(`Status ${source.sourceId} berhasil diubah.`);
      await reload();
    } catch (e) {
      setToggleError(e instanceof Error ? e.message : "Status sumber tidak dapat diubah.");
    } finally {
      toggleBusy.current = false;
      setToggling(false);
    }
  };

  const startEdit = async (sourceId: string) => {
    if (dirty && showForm && !window.confirm("Batalkan perubahan berjalan dan edit sumber lain?")) return;
    const requestId = ++editRequest.current;
    setShowForm(true);
    setMode("edit");
    setEditingId(sourceId);
    setInitialForm(null);
    setInitialRevision(null);
    setForm(EMPTY_FORM);
    setRevisions([]);
    setRevisionsLoading(false);
    setSuccess(null);
    setFormError(null);
    setDetailLoading(true);
    try {
      const detail = await fetchAdminSourceDetail(sourceId);
      if (requestId !== editRequest.current) return;
      const loadedForm = {
        sourceId: detail.sourceId,
        sourceName: detail.sourceName,
        institution: detail.institution,
        primaryUrl: detail.primaryUrl,
        description: detail.description,
        acquisitionMethod: detail.acquisitionMethod,
        endpointUrl: detail.endpointUrl,
        dataFormat: detail.dataFormat,
        frequency: detail.frequency,
        updateSchedule: detail.updateSchedule,
        status: detail.status,
      };
      setForm(loadedForm);
      setInitialForm(loadedForm);
      setInitialRevision(Number.isInteger(detail.revisionVersion) ? detail.revisionVersion : null);
      setDirty(false);
      setRevisionsLoading(true);
      fetchAdminSourceRevisions(sourceId)
        .then((rows) => { if (requestId === editRequest.current) setRevisions(rows); })
        .catch(() => { if (requestId === editRequest.current) setRevisions([]); })
        .finally(() => { if (requestId === editRequest.current) setRevisionsLoading(false); });
    } catch (e) {
      if (requestId === editRequest.current) setFormError(e instanceof Error ? e.message : "Detail sumber tidak dapat dimuat.");
    } finally {
      if (requestId === editRequest.current) setDetailLoading(false);
    }
  };

  return (
    <section className="sources-page" aria-labelledby="admin-sources-title">
      <div className="section-head">
        <div>
          <h2 className="section-title" id="admin-sources-title">Kelola Sumber Data</h2>
          <p className="section-sub">
            Area Admin. Penambahan sumber tercatat di audit log dan berlaku pada siklus
            akuisisi berikutnya. Tanpa sinkronisasi otomatis.
          </p>
        </div>
        <span className="section-badge">Admin DEKSI</span>
      </div>

      <nav className="sources-nav" aria-label="Navigasi halaman">
        <a href="/">Beranda</a>
        <a href="/sumber-data">Sumber Data</a>
        <a href="/admin/sumber-data" aria-current="page">Kelola Sumber</a>
        <a href="/admin/riwayat-sinkronisasi">Riwayat Sinkronisasi</a>
        <a href="/#/admin/feedback">Kelola Umpan Balik</a>
      </nav>

      {!sessionChecked || (loading && !authenticated) ? (
        <p className="summary-loading">Memeriksa sesi admin…</p>
      ) : !authenticated ? (
        <article className="trace-panel" aria-label="Login admin">
          <h3 className="trace-title">Login Admin</h3>
          <p className="trace-note">Khusus staf pengelola sumber. Publik tidak dapat menambah sumber.</p>
          <div className="trace-grid">
            <label className="trace-row">Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" /></label>
            <label className="trace-row">Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
          </div>
          {loginError && <p className="summary-error">{loginError}</p>}
          <footer className="trace-foot">
            <button type="button" className="tab tab-active" onClick={doLogin} disabled={loginLoading || !username || !password}>
              {loginLoading ? "Memeriksa…" : "Masuk"}
            </button>
          </footer>
        </article>
      ) : (
        <>
          <div className="source-detail-head">
            <p className="source-meta">Masuk sebagai {displayOrUnavailable(username || "admin")}. Konfigurasi gagal tidak mengubah data lama.</p>
            <span>
              <button type="button" className="tab" disabled={toggling} onClick={() => (showForm && mode === "add" ? cancelForm() : startAdd())}>Tambah Sumber Data</button>{" "}
              <button type="button" className="tab" disabled={toggling || saving || logoutLoading} onClick={doLogout}>Keluar</button>
            </span>
          </div>

          {logoutError && <p className="summary-error" role="alert">{logoutError}</p>}
          {success && <p className="summary-loading">{success}</p>}
          {toggleError && <p className="summary-error" role="alert">{toggleError}</p>}
          {loading && <p className="summary-loading">Memuat registry sumber…</p>}
          {!loading && error && <p className="summary-error">{error}</p>}

          {!loading && !error && (
            <div className="sources-grid">
              {sources.map((s) => (
                <article key={s.sourceId} className="source-card">
                  <p className="source-institution">{s.institution} · {s.status}</p>
                  <p className="source-name">{s.sourceName}</p>
                  <p className="source-desc">{s.acquisitionMethodLabel || displayOrUnavailable(s.acquisitionMethod)} · {displayOrUnavailable(s.dataFormat)}</p>
                  <p className="source-meta">Jadwal: {displayOrUnavailable(s.updateSchedule || s.frequency)}</p>
                  <p className="source-meta">Fetch terakhir: {displayOrUnavailable(s.lastFetch.retrievedAt)} {s.lastFetch.documentName ? `· ${s.lastFetch.documentName}` : ""}</p>
                  {s.sourceId === "BPS" && !showForm && <ResyncAction sourceId={s.sourceId} sourceName={s.sourceName} active={s.status === "active"} supported />}
                  <button type="button" className="source-trace-link" disabled={toggling} onClick={() => startEdit(s.sourceId)}>
                    Edit ↗
                  </button>
                  <button type="button" className="source-trace-link" disabled={toggling || showForm || !["active", "inactive"].includes(s.status)}
                    aria-label={`${s.status === "active" ? "Nonaktifkan" : "Aktifkan"} ${s.sourceName}`}
                    onClick={() => void toggleSource(s)}>
                    {s.status === "active" ? "Nonaktifkan" : "Aktifkan"}
                  </button>
                </article>
              ))}
            </div>
          )}

          {showForm && (
            <article className="trace-panel" aria-label={mode === "edit" ? "Form edit sumber" : "Form tambah sumber"}>
              <h3 className="trace-title">{mode === "edit" ? `Edit Sumber ${editingId}` : "Tambah Sumber Data"} * wajib</h3>
              {detailLoading ? (
                <p className="summary-loading">Memuat detail sumber…</p>
              ) : (
              <>
              <div className="trace-grid">
                <label className="trace-row">Source ID *<input value={form.sourceId} onChange={(e) => set("sourceId", e.target.value.toUpperCase())} placeholder="CONTOH_ID" disabled={mode === "edit"} title={mode === "edit" ? "Identitas tidak dapat diubah" : undefined} /></label>
                <label className="trace-row">Nama sumber *<input value={form.sourceName} onChange={(e) => set("sourceName", e.target.value)} /></label>
                <label className="trace-row">Institusi *<input value={form.institution} onChange={(e) => set("institution", e.target.value)} /></label>
                <label className="trace-row">Portal resmi URL *<input value={form.primaryUrl} onChange={(e) => set("primaryUrl", e.target.value)} placeholder="https://" /></label>
                <label className="trace-row">Deskripsi<textarea value={form.description} onChange={(e) => set("description", e.target.value)} /></label>
                <label className="trace-row">Metode akuisisi *<select value={form.acquisitionMethod} onChange={(e) => { set("acquisitionMethod", e.target.value); set("dataFormat", ""); }}>
                  <option value="">Pilih…</option>
                  {methods.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select></label>
                <label className="trace-row">Endpoint URL {activeMethod?.endpointRequired ? "*" : ""}<input value={form.endpointUrl} onChange={(e) => set("endpointUrl", e.target.value)} placeholder="https://…" /></label>
                <label className="trace-row">Format data *<select value={form.dataFormat} onChange={(e) => set("dataFormat", e.target.value)}>
                  <option value="">Pilih…</option>
                  {allowedFormats.map((f) => <option key={f} value={f}>{f}</option>)}
                </select></label>
                <label className="trace-row">Frekuensi *<select value={form.frequency} onChange={(e) => set("frequency", e.target.value)}>
                  <option value="">Pilih…</option>
                  {frequencies.map((f) => <option key={f} value={f}>{f}</option>)}
                </select></label>
                <label className="trace-row">Jadwal pembaruan<input value={form.updateSchedule} onChange={(e) => set("updateSchedule", e.target.value)} placeholder="cth: Triwulanan" /></label>
                <label className="trace-row">Status<select value={form.status} onChange={(e) => set("status", e.target.value)}>
                  <option value="active">Aktif</option>
                  <option value="inactive">Nonaktif</option>
                </select></label>
              </div>
              {activeMethod && <p className="trace-note">Handler: {activeMethod.handler}. {activeMethod.description}</p>}
              {formError && <p className="summary-error">{formError}</p>}
              <footer className="trace-foot">
                <button type="button" className="tab tab-active" onClick={submit} disabled={saving || detailLoading}>{saving ? "Menyimpan…" : mode === "edit" ? "Simpan Perubahan" : "Simpan"}</button>
                <button type="button" className="tab" onClick={cancelForm} disabled={saving}>Batal</button>
              </footer>
              </>
              )}
              {mode === "edit" && editingId && (
                <details className="trace-raw">
                  <summary>Riwayat revisi {editingId} (tidak pernah dihapus)</summary>
                  {revisionsLoading ? (
                    <p className="summary-loading">Memuat riwayat…</p>
                  ) : revisions.length === 0 ? (
                    <p className="trace-note">Belum ada revisi tercatat.</p>
                  ) : (
                    <ul className="trace-history">
                      {revisions.map((r) => (
                        <li key={r.version}>
                          <span>v{r.version} · {r.action}</span>
                          <span>{r.updatedBy ?? "—"} · {r.createdAt ?? "Tidak tersedia"}</span>
                          <span className="trace-history-type">Ubah: {r.changedFields.join(", ") || "-"}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </details>
              )}
            </article>
          )}
        </>
      )}
    </section>
  );
}
