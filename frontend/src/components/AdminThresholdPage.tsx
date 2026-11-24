import { useEffect, useState } from "react";
import { AdminNavigation } from "./AdminNavigation";
import {
  fetchThresholdDetail,
  fetchThresholdHistory,
  fetchThresholds,
  updateThreshold,
  validateThresholdInput,
  type ThresholdEntry,
  type ThresholdEvaluation,
  type ThresholdHistoryItem,
} from "../api";
import "./admin-source-card.css";

export function AdminThresholdPage() {
  const [items, setItems] = useState<ThresholdEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [selected, setSelected] = useState<ThresholdEntry | null>(null);
  const [evaluation, setEvaluation] = useState<ThresholdEvaluation | null>(null);
  const [formValue, setFormValue] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState<ThresholdHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setItems(await fetchThresholds());
      setError(null);
    } catch {
      setError("Tidak dapat memuat konfigurasi threshold. Pastikan login Admin.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void load(); }, []);

  async function openEdit(item: ThresholdEntry) {
    setMsg(null);
    setFormError(null);
    setConfirming(false);
    try {
      const detail = await fetchThresholdDetail(item.indicatorCode, item.paramKey);
      setSelected(detail.threshold);
      setEvaluation(detail.evaluation);
      setFormValue(detail.threshold.value);
      const hist = await fetchThresholdHistory(item.indicatorCode, item.paramKey);
      setHistory(hist);
    } catch (e) {
      setSelected(item);
      setEvaluation(null);
      setFormValue(item.value);
      setHistory([]);
      setFormError(e instanceof Error ? e.message : "Detail threshold tidak dapat dimuat.");
    }
  }

  function closeEdit() {
    setSelected(null);
    setEvaluation(null);
    setFormError(null);
    setConfirming(false);
    setHistory([]);
  }

  async function confirmSave() {
    if (!selected) return;
    setSaving(true);
    setFormError(null);
    try {
      const out = await updateThreshold(selected.indicatorCode, selected.paramKey, { value: formValue.trim() });
      setMsg(out.message || "Konfigurasi tersimpan");
      setConfirming(false);
      setSelected(out.threshold);
      setEvaluation(out.evaluation);
      setItems(await fetchThresholds());
      setHistory(await fetchThresholdHistory(selected.indicatorCode, selected.paramKey));
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Gagal menyimpan");
    } finally {
      setSaving(false);
    }
  }

  function requestSave() {
    if (!selected) return;
    const problem = validateThresholdInput(
      formValue, selected.minAllowed, selected.maxAllowed, selected.unit, selected.unit,
    );
    if (problem) {
      setFormError(problem);
      return;
    }
    setFormError(null);
    setConfirming(true);
  }

  return (
    <section className="sources-page" aria-labelledby="threshold-title">
      <div className="section-head">
        <div>
          <h2 className="section-title" id="threshold-title">Konfigurasi Threshold Diagnostik</h2>
          <p className="section-sub">
            Area Admin. Ambang diagnostik yang dapat dikonfigurasi; rumus inti Economic Engine tidak diubah.
            Setiap perubahan tercatat berversi di audit log.
          </p>
        </div>
        <span className="section-badge">Admin DEKSI</span>
      </div>

      <AdminNavigation active="thresholds" />

      {loading && <p className="summary-loading">Memuat konfigurasi threshold…</p>}
      {!loading && error && <p className="summary-error">{error}</p>}

      {!loading && !error && (
        <>
          {msg && <p className="summary-loading" role="status">{msg}</p>}
          {items.length === 0 ? (
            <p className="summary-empty">Belum ada parameter threshold yang dapat dikonfigurasi.</p>
          ) : (
            <div className="sources-grid admin-sources-grid">
              {items.map((t) => (
                <article
                  key={`${t.indicatorCode}/${t.paramKey}`}
                  className="source-card admin-source-card"
                  aria-current={selected?.paramKey === t.paramKey && selected?.indicatorCode === t.indicatorCode ? "true" : undefined}
                >
                  <div className="admin-source-card__heading">
                    <p className="source-institution">{t.category} · {t.status === "active" ? "AKTIF" : "NONAKTIF"}</p>
                    <p className="source-name">{t.label}</p>
                    <p className="source-desc">{t.description}</p>
                  </div>
                  <div className="admin-source-card__meta">
                    <p className="source-meta">Nilai: {t.value} {t.unit}</p>
                    <p className="source-meta">Rentang: {t.minAllowed}–{t.maxAllowed} {t.unit}</p>
                    <p className="source-meta">Parameter: {t.paramKey}</p>
                    <p className="source-meta">Versi: v{t.version}{t.updatedAt ? ` · ${t.updatedAt}` : ""}</p>
                    {t.latestValue !== null && <p className="source-meta">Nilai terbaru: {t.latestValue} {t.unit}</p>}
                  </div>
                  <div className="admin-source-card__actions">
                    <button
                      type="button"
                      className="source-trace-link admin-source-card__review"
                      onClick={() => void openEdit(t)}
                    >
                      Ubah
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}

          {selected && (
            <article className="trace-panel" aria-label={`Ubah ${selected.label}`}>
              <div className="trace-head">
                <div>
                  <p className="trace-kicker">UBAH THRESHOLD</p>
                  <h3 className="trace-title">{selected.label}</h3>
                </div>
                <span className="trace-badge">v{selected.version}</span>
              </div>
              <p className="trace-note">
                {selected.indicatorName} · {selected.paramKey} · Satuan: {selected.unit} ·
                Rentang: {selected.minAllowed}–{selected.maxAllowed} {selected.unit}
              </p>
              {evaluation && <p className="trace-note">Dampak saat ini: {evaluation.impact}</p>}
              <label className="trace-row">
                Nilai threshold baru
                <input
                  value={formValue}
                  onChange={(e) => { setFormValue(e.target.value); setConfirming(false); }}
                  inputMode="decimal"
                  aria-label="Nilai threshold baru"
                />
              </label>
              {formError && <p className="trace-error" role="alert">{formError}</p>}
              {!confirming && (
                <div className="admin-source-card__actions">
                  <button type="button" className="source-trace-link admin-source-card__review" onClick={closeEdit}>
                    Batalkan
                  </button>
                  <button type="button" className="source-trace-link admin-source-card__review" onClick={requestSave} disabled={saving}>
                    Simpan perubahan
                  </button>
                </div>
              )}
              {confirming && (
                <div role="dialog" aria-modal="true" aria-labelledby="threshold-confirm-title">
                  <h4 className="trace-title" id="threshold-confirm-title">Simpan perubahan?</h4>
                  <dl className="trace-grid">
                    <div className="trace-row"><dt>Indikator</dt><dd>{selected.indicatorName}</dd></div>
                    <div className="trace-row"><dt>Parameter</dt><dd>{selected.paramKey}</dd></div>
                    <div className="trace-row"><dt>Nilai sebelumnya</dt><dd>{selected.value} {selected.unit}</dd></div>
                    <div className="trace-row"><dt>Nilai baru</dt><dd>{formValue.trim()} {selected.unit}</dd></div>
                  </dl>
                  {evaluation && <p className="trace-note">Dampak yang diketahui sistem: {evaluation.impact}</p>}
                  <div className="admin-source-card__actions">
                    <button type="button" className="source-trace-link admin-source-card__review" onClick={() => setConfirming(false)} disabled={saving}>
                      Batalkan
                    </button>
                    <button
                      type="button"
                      className="source-trace-link admin-source-card__review"
                      onClick={() => void confirmSave()}
                      disabled={saving}
                    >
                      {saving ? "Menyimpan…" : "Konfirmasi simpan"}
                    </button>
                  </div>
                </div>
              )}
              <div className="trace-foot">
                <h4>Riwayat perubahan</h4>
                {historyLoading ? (
                  <p className="trace-note">Memuat riwayat…</p>
                ) : history.length === 0 ? (
                  <p className="trace-note">Belum ada riwayat perubahan.</p>
                ) : (
                  <ul className="trace-history">
                    {history.map((h, i) => (
                      <li key={i}>
                        <span>{h.createdAt ?? "—"}</span>
                        <span className="trace-history-type">{h.actor ?? "—"}</span>
                        <span>v{(h.oldValue as { version?: number }).version ?? "?"} → v{(h.newValue as { version?: number }).version ?? "?"}</span>
                        <span>{(h.newValue as { value?: string }).value ?? ""} {(h.newValue as { unit?: string }).unit ?? ""}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <button
                  type="button"
                  className="source-trace-link"
                  onClick={() => {
                    if (!selected) return;
                    setHistoryLoading(true);
                    fetchThresholdHistory(selected.indicatorCode, selected.paramKey)
                      .then(setHistory)
                      .catch(() => setHistory([]))
                      .finally(() => setHistoryLoading(false));
                  }}
                >
                  Muat ulang riwayat
                </button>
              </div>
            </article>
          )}
        </>
      )}
    </section>
  );
}
