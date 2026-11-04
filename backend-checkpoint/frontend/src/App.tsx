import './App.css'
import { useEffect } from "react";
import { Navbar } from "./components/ShellTop";
import { Hero } from "./components/HeroStatus";
import { InsightSection, Footer } from "./components/ShellBottom";
import { EconomicSummary } from "./components/EconomicSummary";
import { TrendChart } from "./components/TrendChart";
import { useDashboardData } from "./api";

export default function App() {
  const { summary, cards, loading, error } = useDashboardData();

  useEffect(() => {
    document.title = "DEKSI — Deteksi Ekonomi Indonesia";
  }, []);

  return (
    <div className="deksi-page">
      <Navbar />
      <Hero
        updatedAt={summary?.lastUpdate?.formatted ?? null}
        period={cards[0]?.latestPeriod ?? null}
        loading={loading}
        error={error}
      />
      <EconomicSummary cards={cards} loading={loading} error={error} />
      <TrendChart />
      <InsightSection />
      <Footer />
    </div>
  );
}
