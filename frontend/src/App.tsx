import './App.css'
import { useEffect, useState } from 'react'
import { EconomicSummary } from './components/EconomicSummary'
import { TrendChart } from './components/TrendChart'
import { InsightSection } from './components/ShellBottom'
import { EditorialLanding, EditorialContext } from './components/EditorialLanding'
import { EditorialInfo, EditorialFooter } from './components/EditorialInfo'
import { useDashboardData } from './api'
import { parseRoute } from './features/indicators/data'
import { DetailScreen, FeatureUnavailable } from './features/indicators/DetailPage'
import './features/indicators/features.css'

function DashboardView() {
  const { summary, cards, loading, error } = useDashboardData()
  const [infoOpen, setInfoOpen] = useState(false)
  useEffect(() => { document.title = 'DEKSI · Deteksi Ekonomi Indonesia' }, [])
  return <div className="deksi-page">
    <a className="skip-link" href="#hero-title">Lewati ke konten utama</a>
    <main>
      <EditorialLanding cards={cards} summary={summary} loading={loading} error={error} onInfo={() => setInfoOpen(true)} />
      <div className="api-context" role="status"><span>PEMBARUAN BACKEND</span><p>{loading ? 'Memuat metadata…' : error ? error : summary?.lastUpdate?.formatted ?? 'Waktu pembaruan belum tersedia.'}</p><p>Nilai dan metadata ditampilkan sesuai respons API, bukan fixture prototipe.</p></div>
      <EconomicSummary cards={cards} loading={loading} error={error} />
      <TrendChart />
      <InsightSection />
      <EditorialContext cards={cards} loading={loading} error={error} />
    </main>
    <EditorialFooter onInfo={() => setInfoOpen(true)} />
    <EditorialInfo open={infoOpen} onClose={() => setInfoOpen(false)} />
  </div>
}

export default function App() {
  const route = typeof window === 'undefined' ? parseRoute('/') : parseRoute(window.location.pathname, window.location.search)
  if (route.kind === 'dashboard') return <DashboardView />
  if (route.kind === 'detail') return <DetailScreen route={route} />
  return <FeatureUnavailable source={route.kind === 'source'} />
}
