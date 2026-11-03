/**
 * DashboardFilter – Fitur 5: Filter periode dan kategori indikator.
 *
 * Menampilkan kontrol filter berupa:
 *  - Pills kategori yang diisi dinamis dari endpoint /api/indicators/categories/
 *  - Dropdown tahun (10 tahun terakhir)
 *  - Tombol reset yang muncul hanya ketika filter aktif
 *
 * Komponen ini bersifat controlled: state filter dikelola oleh parent (App)
 * sehingga perubahan filter dapat mempengaruhi komponen lain (kartu, grafik).
 */

import { useIndicatorCategories, type DashboardFilters } from "../api";

interface Props {
  filters: DashboardFilters;
  onChange: (next: DashboardFilters) => void;
}

// Daftar tahun yang tersedia di dropdown
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR - i);

export function DashboardFilter({ filters, onChange }: Props) {
  const categoryEntries = useIndicatorCategories();
  const hasActiveFilter = filters.category !== "" || filters.year !== "";

  function setCategory(cat: string) {
    onChange({ ...filters, category: cat });
  }

  function setYear(year: string) {
    onChange({ ...filters, year });
  }

  function resetFilters() {
    onChange({ category: "", year: "" });
  }

  return (
    <section className="dashboard-filter" aria-label="Filter dashboard">
      <div className="dashboard-filter__row">
        {/* Pills kategori */}
        <div className="dashboard-filter__group" role="group" aria-label="Filter kategori">
          <span className="dashboard-filter__label">Kategori:</span>
          <div className="dashboard-filter__pills">
            <button
              id="filter-cat-all"
              className={`filter-pill${filters.category === "" ? " filter-pill--active" : ""}`}
              onClick={() => setCategory("")}
              aria-pressed={filters.category === ""}
            >
              Semua
            </button>
            {categoryEntries.map((entry) => (
              <button
                key={entry.category}
                id={`filter-cat-${entry.category.toLowerCase().replace(/\s/g, "-")}`}
                className={`filter-pill${
                  filters.category === entry.category ? " filter-pill--active" : ""
                }`}
                onClick={() => setCategory(entry.category)}
                aria-pressed={filters.category === entry.category}
              >
                {entry.category}
              </button>
            ))}
          </div>
        </div>

        {/* Dropdown tahun */}
        <div className="dashboard-filter__group">
          <label htmlFor="filter-year" className="dashboard-filter__label">
            Tahun:
          </label>
          <select
            id="filter-year"
            className="filter-select"
            value={filters.year}
            onChange={(e) => setYear(e.target.value)}
          >
            <option value="">Semua Tahun</option>
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={String(y)}>
                {y}
              </option>
            ))}
          </select>
        </div>

        {/* Tombol reset – muncul hanya bila ada filter aktif */}
        {hasActiveFilter && (
          <button
            id="filter-reset"
            className="filter-reset"
            onClick={resetFilters}
            aria-label="Reset semua filter"
          >
            ✕ Reset Filter
          </button>
        )}
      </div>

      {/* Notifikasi filter aktif */}
      {hasActiveFilter && (
        <p className="dashboard-filter__active-note" role="status">
          Filter aktif:{" "}
          {[
            filters.category && `Kategori: ${filters.category}`,
            filters.year && `Tahun: ${filters.year}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
    </section>
  );
}
