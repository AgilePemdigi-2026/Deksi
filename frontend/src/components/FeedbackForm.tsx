/**
 * FeedbackForm – Fitur 8: Kirim Umpan Balik (UC-05).
 *
 * Form terkontrol dengan:
 *  - Pilihan kategori dari endpoint /api/feedback/categories/
 *  - Field deskripsi wajib (min 10 karakter)
 *  - Field identitas pengirim opsional (nama, email)
 *  - Field pengaitan indikator dan periode (opsional)
 *  - Validasi client-side sebelum kirim ke backend
 *  - Tiga state visual: idle → loading → success | error
 */

import { useState, type FormEvent } from "react";
import {
  useFeedbackCategories,
  submitFeedback,
  type FeedbackPayload,
  type FeedbackResult,
} from "../api";

interface Props {
  /** Kode indikator yang sedang dilihat user, opsional untuk pra-isi field terkait. */
  defaultIndicatorCode?: string;
  /** Periode yang sedang dilihat user, opsional untuk pra-isi field terkait. */
  defaultPeriod?: string;
}

const EMPTY_PAYLOAD: FeedbackPayload = {
  category: "",
  description: "",
  sender_name: "",
  sender_email: "",
  related_indicator_code: "",
  related_period: "",
};

export function FeedbackForm({ defaultIndicatorCode = "", defaultPeriod = "" }: Props) {
  const feedbackCategories = useFeedbackCategories();

  const [payload, setPayload] = useState<FeedbackPayload>({
    ...EMPTY_PAYLOAD,
    related_indicator_code: defaultIndicatorCode,
    related_period: defaultPeriod,
  });
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof FeedbackPayload, string>>>({});
  const [result, setResult] = useState<FeedbackResult>({
    id: null,
    status: "idle",
    message: "",
  });

  // ── Validasi client-side ────────────────────────────────────────────────
  function validate(): boolean {
    const errors: Partial<Record<keyof FeedbackPayload, string>> = {};

    if (!payload.category) {
      errors.category = "Pilih kategori umpan balik.";
    }
    if (!payload.description.trim()) {
      errors.description = "Deskripsi wajib diisi.";
    } else if (payload.description.trim().length < 10) {
      errors.description = "Deskripsi minimal 10 karakter.";
    } else if (payload.description.trim().length > 2000) {
      errors.description = "Deskripsi maksimal 2.000 karakter.";
    }
    if (payload.sender_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.sender_email)) {
      errors.sender_email = "Format email tidak valid.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  // ── Submit ──────────────────────────────────────────────────────────────
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setResult({ id: null, status: "loading", message: "" });

    // Kirim hanya field yang tidak kosong
    const clean: FeedbackPayload = {
      category: payload.category,
      description: payload.description.trim(),
    };
    if (payload.sender_name?.trim())          clean.sender_name = payload.sender_name.trim();
    if (payload.sender_email?.trim())         clean.sender_email = payload.sender_email.trim();
    if (payload.related_indicator_code?.trim()) clean.related_indicator_code = payload.related_indicator_code.trim();
    if (payload.related_period?.trim())       clean.related_period = payload.related_period.trim();

    const res = await submitFeedback(clean);
    setResult(res);

    if (res.status === "success") {
      setPayload({ ...EMPTY_PAYLOAD, related_indicator_code: defaultIndicatorCode, related_period: defaultPeriod });
      setFieldErrors({});
    }
  }

  function update<K extends keyof FeedbackPayload>(key: K, value: FeedbackPayload[K]) {
    setPayload((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => ({ ...prev, [key]: undefined }));
    if (result.status !== "idle") setResult({ id: null, status: "idle", message: "" });
  }

  // ── Render ──────────────────────────────────────────────────────────────
  if (result.status === "success") {
    return (
      <div className="feedback-success" role="status">
        <span className="feedback-success__icon" aria-hidden="true">✓</span>
        <p className="feedback-success__message">{result.message}</p>
        <button
          className="feedback-btn feedback-btn--secondary"
          onClick={() => setResult({ id: null, status: "idle", message: "" })}
        >
          Kirim Umpan Balik Lain
        </button>
      </div>
    );
  }

  return (
    <form
      id="feedback-form"
      className="feedback-form"
      onSubmit={handleSubmit}
      noValidate
      aria-label="Form umpan balik"
    >
      {/* Error dari server */}
      {result.status === "error" && (
        <div className="feedback-form__server-error" role="alert">
          {result.message}
        </div>
      )}

      {/* Kategori */}
      <div className="feedback-field">
        <label htmlFor="fb-category" className="feedback-label">
          Kategori <span aria-hidden="true">*</span>
        </label>
        <select
          id="fb-category"
          className={`feedback-select${fieldErrors.category ? " feedback-input--error" : ""}`}
          value={payload.category}
          onChange={(e) => update("category", e.target.value)}
          required
          disabled={result.status === "loading"}
        >
          <option value="">— Pilih kategori —</option>
          {feedbackCategories.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
        {fieldErrors.category && (
          <p className="feedback-error" role="alert">{fieldErrors.category}</p>
        )}
      </div>

      {/* Deskripsi */}
      <div className="feedback-field">
        <label htmlFor="fb-description" className="feedback-label">
          Deskripsi <span aria-hidden="true">*</span>
        </label>
        <textarea
          id="fb-description"
          className={`feedback-textarea${fieldErrors.description ? " feedback-input--error" : ""}`}
          rows={5}
          placeholder="Jelaskan secara spesifik apa yang perlu diperbaiki atau ditambahkan…"
          value={payload.description}
          onChange={(e) => update("description", e.target.value)}
          required
          minLength={10}
          maxLength={2000}
          disabled={result.status === "loading"}
        />
        <p className="feedback-char-count">
          {payload.description.length} / 2.000 karakter
        </p>
        {fieldErrors.description && (
          <p className="feedback-error" role="alert">{fieldErrors.description}</p>
        )}
      </div>

      {/* Indikator & Periode terkait */}
      <div className="feedback-field-row">
        <div className="feedback-field">
          <label htmlFor="fb-indicator" className="feedback-label">
            Indikator terkait <span className="feedback-label--optional">(opsional)</span>
          </label>
          <input
            id="fb-indicator"
            type="text"
            className="feedback-input"
            placeholder="mis. pdb, inflasi"
            value={payload.related_indicator_code}
            onChange={(e) => update("related_indicator_code", e.target.value)}
            disabled={result.status === "loading"}
            maxLength={32}
          />
        </div>
        <div className="feedback-field">
          <label htmlFor="fb-period" className="feedback-label">
            Periode terkait <span className="feedback-label--optional">(opsional)</span>
          </label>
          <input
            id="fb-period"
            type="text"
            className="feedback-input"
            placeholder="mis. Q1 2024"
            value={payload.related_period}
            onChange={(e) => update("related_period", e.target.value)}
            disabled={result.status === "loading"}
            maxLength={50}
          />
        </div>
      </div>

      {/* Identitas pengirim (opsional) */}
      <details className="feedback-identity">
        <summary className="feedback-identity__toggle">
          Identitas pengirim <span className="feedback-label--optional">(opsional)</span>
        </summary>
        <div className="feedback-field-row">
          <div className="feedback-field">
            <label htmlFor="fb-name" className="feedback-label">Nama</label>
            <input
              id="fb-name"
              type="text"
              className="feedback-input"
              placeholder="Nama Anda"
              value={payload.sender_name}
              onChange={(e) => update("sender_name", e.target.value)}
              disabled={result.status === "loading"}
              maxLength={150}
            />
          </div>
          <div className="feedback-field">
            <label htmlFor="fb-email" className="feedback-label">Email</label>
            <input
              id="fb-email"
              type="email"
              className={`feedback-input${fieldErrors.sender_email ? " feedback-input--error" : ""}`}
              placeholder="email@contoh.com"
              value={payload.sender_email}
              onChange={(e) => update("sender_email", e.target.value)}
              disabled={result.status === "loading"}
            />
            {fieldErrors.sender_email && (
              <p className="feedback-error" role="alert">{fieldErrors.sender_email}</p>
            )}
          </div>
        </div>
      </details>

      {/* Tombol kirim */}
      <button
        id="fb-submit"
        type="submit"
        className="feedback-btn feedback-btn--primary"
        disabled={result.status === "loading"}
      >
        {result.status === "loading" ? "Mengirim…" : "Kirim Umpan Balik"}
      </button>
    </form>
  );
}
