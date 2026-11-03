import { useEffect, useState } from "react";
import {
  displayOrUnavailable,
  fetchSourceTrace,
  type SourceTrace,
} from "../api";

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="trace-row">
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{value}</dd>
    </div>
  );
}

export function SourceTracePanel({
  code,
  period,
  observationDate,
  compact = false,
}: {
  code: string;
  period?: string;
  observationDate?: string;
  compact?: boolean;
}) {
  const [trace, setTrace] = useState<SourceTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchSourceTrace(code, { period, observation_date: observationDate })
      .then((body) => {
        if (!cancelled) {
          setTrace(body);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Tidak dapat memuat Source Trace. Metadata tersimpan tetap dapat dilihat melalui daftar sumber.");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [code, period, observationDate]);

  if (loading) return <p className="trace-state">Memuat Source Trace untuk {code}…</p>;
  if (error) return <p className="trace-state trace-error">{error}</p>;
  if (!trace || trace.available === false)
    return <p className="trace-state">Belum ada observasi terpublikasi untuk {code}.</p>;

  const isDerived = trace.valueType === "DEKSI-Derived Metric";
  const pubUrl = trace.publicationUrl || trace.source?.primaryUrl || null;

  return (
    <article className={compact ? "trace-panel compact" : "trace-panel"} aria-label={`Source Trace ${trace.indicatorName}`}>
      <header className="trace-head">
        <div>
          <p className="trace-kicker">SOURCE TRACE · {trace.indicatorCode}</p>
          <h3 className="trace-title">{trace.indicatorName}</h3>
        </div>
        <span className={isDerived ? "trace-badge derived" : "trace-badge official"}>
          {trace.valueType ?? "Official Source Value"}
        </span>
      </header>

      <dl className="trace-grid">
        <Row label="Nilai" value={`${displayOrUnavailable(trace.value)} ${trace.unit ?? ""}`.trim()} />
        <Row label="Periode" value={displayOrUnavailable(trace.period ?? trace.periodLabel)} />
        <Row label="Satuan" value={displayOrUnavailable(trace.unit)} />
        <Row label="Institusi sumber" value={displayOrUnavailable(trace.institution ?? trace.source?.institution)} />
        <Row label="Publikasi / rilis" value={displayOrUnavailable(trace.publicationName ?? trace.source?.sourceName)} />
        <Row label="Tanggal rilis" value={displayOrUnavailable(trace.publicationDate)} />
        <Row label="Tanggal observasi" value={displayOrUnavailable(trace.observationDate)} />
        <Row label="Diambil pada" value={displayOrUnavailable(trace.retrievedAt ?? trace.rawFile?.retrievedAt)} />
        <Row label="Versi" value={displayOrUnavailable(trace.version)} mono />
        <Row label="Revisi / catatan" value={displayOrUnavailable(trace.revision)} />
      </dl>

      {isDerived ? (
        <div className="trace-derived">
          <h4>DEKSI-Derived Metric</h4>
          <p className="trace-note">
            Nilai turunan. Formula dan input resmi ditampilkan agar dapat ditelusuri. RAW tidak ditimpa.
          </p>
          <dl className="trace-grid">
            <Row label="Formula" value={displayOrUnavailable(trace.derived?.formula)} mono />
            <Row label="Periode pembanding" value={displayOrUnavailable(trace.derived?.comparisonPeriod)} />
            <Row
              label="Input resmi"
              value={
                trace.derived?.inputValue
                  ? `${trace.derived.inputValue} ${trace.derived.inputUnit ?? ""} · ${trace.derived.comparisonPeriod ?? ""} · ${trace.derived.inputSource ?? ""}`.trim()
                  : "Tidak tersedia"
              }
            />
          </dl>
        </div>
      ) : (
        <p className="trace-note">
          Official Source Value. Nilai ditampilkan apa adanya dari institusi sumber tanpa formula turunan.
        </p>
      )}

      {trace.rawFile && (
        <details className="trace-raw">
          <summary>Integritas berkas RAW</summary>
          <dl className="trace-grid">
            <Row label="Dokumen" value={displayOrUnavailable(trace.rawFile.documentName)} />
            <Row label="Checksum SHA-256" value={displayOrUnavailable(trace.rawFile.checksumSha256)} mono />
            <Row label="Ukuran" value={String(trace.rawFile.fileSizeBytes ?? "Tidak tersedia")} />
          </dl>
        </details>
      )}

      <footer className="trace-foot">
        {pubUrl ? (
          <a href={pubUrl} target="_blank" rel="noopener noreferrer">
            Buka publikasi resmi ↗
          </a>
        ) : (
          <span>Tidak tersedia</span>
        )}
        <span className="trace-hint">
          Jika tautan eksternal tidak dapat dijangkau, metadata tersimpan di atas tetap berlaku.
        </span>
      </footer>

      {trace.history && trace.history.length > 1 && (
        <details className="trace-raw">
          <summary>Riwayat 12 periode terakhir</summary>
          <ul className="trace-history">
            {trace.history.map((h) => (
              <li key={`${h.period}-${h.observationDate}`}>
                <span>{displayOrUnavailable(h.period)}</span>
                <span>
                  {displayOrUnavailable(h.value)} {h.unit ?? ""}
                </span>
                <span className="trace-history-type">{h.valueType ?? h.dataType ?? ""}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}
