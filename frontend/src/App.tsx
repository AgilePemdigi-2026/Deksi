import './App.css'
import { useEffect, useState } from 'react'
import { EconomicSummary } from './components/EconomicSummary'
import { TrendChart } from './components/TrendChart'
import { InsightSection } from './components/ShellBottom'
import { EditorialLanding, EditorialContext } from './components/EditorialLanding'
import { EditorialInfo, EditorialFooter } from './components/EditorialInfo'
import { DashboardFilter } from './components/DashboardFilter'
import { FeedbackForm } from './components/FeedbackForm'
import { SourceDataPage, type SourcePageSelection } from './components/SourceDataPage'
import { useDashboardFilter, type DashboardFilters } from './api'

const INITIAL_FILTERS: DashboardFilters = { category: '', year: '' }

function parseSourceHash(): SourcePageSelection | null {
  const hash = window.location.hash || '';
  if (!hash.startsWith('#/sumber-data')) return null;
  const query = hash.includes('?') ? hash.split('?')[1] : '';
  const params = new URLSearchParams(query);
  return {
    sourceId: params.get('source') || undefined,
    indicator: params.get('indicator') || undefined,
    period: params.get('period') || undefined,
  };
}

export default function App() {
  const [infoOpen, setInfoOpen] = useState(false)
  const [filters, setFilters] = useState<DashboardFilters>(INITIAL_FILTERS)
  const [sourceRoute, setSourceRoute] = useState<SourcePageSelection | null>(
    () => (typeof window !== 'undefined' ? parseSourceHash() : null),
  )

  // Fitur 5: gunakan hook filter; saat filter kosong hasilnya identik dengan
  // endpoint /api/indicators/ sehingga tidak ada perubahan perilaku default.
  const { summary, cards, loading, error } = useDashboardFilter(filters)

  useEffect(() => { document.title = 'DEKSI · Deteksi Ekonomi Indonesia' }, [])

  // Fitur 9: rute hash publik #/sumber-data (tanpa login, tanpa router tambahan).
  useEffect(() => {
    const sync = () => setSourceRoute(parseSourceHash());
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, [])

  if (sourceRoute) {
    return (
      <div className="deksi-page">
        <a className="skip-link" href="#sources-title">Lewati ke konten utama</a>
        <main>
          <SourceDataPage selection={sourceRoute} />
        </main>
        <EditorialFooter onInfo={() => setInfoOpen(true)} />
        <EditorialInfo open={infoOpen} onClose={() => setInfoOpen(false)} />
      </div>
    );
  }

  return (
    <div className="deksi-page">
      <a className="skip-link" href="#hero-title">Lewati ke konten utama</a>
      <main>
        <EditorialLanding
          cards={cards}
          summary={summary}
          loading={loading}
          error={error}
          onInfo={() => setInfoOpen(true)}
        />

        <div className="api-context" role="status">
          <span>PEMBARUAN BACKEND</span>
          <p>
            {loading
              ? 'Memuat metadata…'
              : error
              ? error
              : summary?.lastUpdate?.formatted ?? 'Waktu pembaruan belum tersedia.'}
          </p>
          <p>Nilai dan metadata ditampilkan sesuai respons API, bukan fixture prototipe.</p>
        </div>

        {/* Fitur 5: Filter dashboard */}
        <DashboardFilter filters={filters} onChange={setFilters} />

        <EconomicSummary cards={cards} loading={loading} error={error} />
        <TrendChart />
        <InsightSection />
        <EditorialContext cards={cards} loading={loading} error={error} />

        {/* Fitur 8: Form umpan balik */}
        <section id="feedback-section" className="feedback-section">
          <div className="feedback-section__inner">
            <h2 className="feedback-section__title">Kirim Umpan Balik</h2>
            <p className="feedback-section__desc">
              Temukan data yang perlu diperbaiki atau memiliki saran untuk DEKSI?
              Sampaikan kepada tim kami. Identitas pengirim bersifat opsional.
            </p>
            <FeedbackForm />
          </div>
        </section>
      </main>

      <EditorialFooter onInfo={() => setInfoOpen(true)} />
      <EditorialInfo open={infoOpen} onClose={() => setInfoOpen(false)} />
    </div>
  )
}
