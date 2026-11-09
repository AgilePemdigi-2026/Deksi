import { useEffect, useState } from "react";
import {
  adminLogin,
  adminLogout,
  createAdminSource,
  displayOrUnavailable,
  fetchAcquisitionMethods,
  fetchAdminSession,
  fetchAdminSources,
  type AcquisitionMethod,
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
  const [sessionChecked, setSessionChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);

  const [sources, setSources] = useState<AdminSourceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [methods, setMethods] = useState<AcquisitionMethod[]>([]);
  const [frequencies, setFrequencies] = useState<string[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

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
    await adminLogout();
    setAuthenticated(false);
    setSources([]);
  };

  const set = (key: keyof typeof EMPTY_FORM, value: string) => {
    setForm((f) => ({ ...f, [key]: value }));
    setDirty(true);
    setSuccess(null);
  };

  const activeMethod = methods.find((m) => m.value === form.acquisitionMethod);
  const allowedFormats = activeMethod?.formats ?? [];

  const validate = (): string | null => {
    if (!form.sourceId.trim() || !form.sourceName.trim() || !form.institution.trim())
      return "Identitas sumber (ID, nama, institusi) wajib diisi.";
    if (!/^[A-Za-z0-9_]{2,32}$/.test(form.sourceId.trim()))
      return "Source ID 2–32 karakter: huruf, angka, garis bawah.";
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
    const problem = validate();
    if (problem) {
      setFormError(problem);
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
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
      setForm(EMPTY_FORM);
      setDirty(false);
      setShowForm(false);
      await reload();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Penyimpanan gagal.");
    } finally {
      setSaving(false);
    }
  };

  const cancelForm = () => {
    if (dirty && !window.confirm("Batalkan? Perubahan form akan hilang.")) return;
    setShowForm(false);
    setForm(EMPTY_FORM);
    setDirty(false);
    setFormError(null);
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
              <button type="button" className="tab" onClick={() => (showForm ? cancelForm() : (setShowForm(true), setSuccess(null)))}>Tambah Sumber Data</button>{" "}
              <button type="button" className="tab" onClick={doLogout}>Keluar</button>
            </span>
          </div>

          {success && <p className="summary-loading">{success}</p>}
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
                </article>
              ))}
            </div>
          )}

          {showForm && (
            <article className="trace-panel" aria-label="Form tambah sumber">
              <h3 className="trace-title">Tambah Sumber Data * wajib</h3>
              <div className="trace-grid">
                <label className="trace-row">Source ID *<input value={form.sourceId} onChange={(e) => set("sourceId", e.target.value.toUpperCase())} placeholder="CONTOH_ID" /></label>
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
                <button type="button" className="tab tab-active" onClick={submit} disabled={saving}>{saving ? "Menyimpan…" : "Simpan"}</button>
                <button type="button" className="tab" onClick={cancelForm} disabled={saving}>Batal</button>
              </footer>
            </article>
          )}
        </>
      )}
    </section>
  );
}
