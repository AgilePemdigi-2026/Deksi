import { insightItems } from "../data/indicators";
import type { InsightItem } from "../data/indicators";

const toneClass: Record<InsightItem["statusTone"], string> = {
  green: "tag-green",
  blue: "tag-blue",
  orange: "tag-orange",
};

export function InsightSection() {
  return (
    <section className="insight" id="sumber-data">
      <div className="section-head">
        <div>
          <h2 className="section-title">
            Insight Utama <span className="insight-chip">ANALISIS DEKSI</span>
          </h2>
          <p className="section-sub">
            Pola makroekonomi teridentifikasi dari multi-sumber data kementerian dan regulator
          </p>
        </div>
      </div>
      <div className="insight-grid">
        {insightItems.map((item) => (
          <article className="insight-card" key={item.index}>
            <div className="insight-top">
              <span className={toneClass[item.statusTone]}>{item.statusTag}</span>
              <span className="insight-index">{item.index}</span>
            </div>
            <h3 className="insight-title">{item.title}</h3>
            <p className="insight-subtitle">{item.subtitle}</p>
            <p className="insight-body">{item.body}</p>
            <div className="insight-badge">
              <p className="insight-badge-title">{item.badgeTitle}</p>
              <p className="insight-badge-body">{item.badgeBody}</p>
            </div>
            <footer className="insight-footer">
              <span>{item.footerSource}</span>
              <a href="#analisis">{item.footerAction}</a>
            </footer>
          </article>
        ))}
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="footer" id="tentang">
      <div className="footer-top">
        <div className="footer-brand">
          <p className="footer-name">DEKSI <span>|</span> Deteksi Ekonomi Indonesia</p>
          <p className="footer-desc">
            Menghubungkan data resmi Badan Pusat Statistik (BPS), Bank Indonesia (BI),
            Kementerian Keuangan (Kemenkeu), dan Kementerian Investasi (BPIPM) untuk
            pemahaman kondisi ekonomi nasional yang objektif, transparan, dan dapat
            ditelusuri oleh publik.
          </p>
        </div>
        <div className="footer-col">
          <p className="footer-head">Kemitraan &amp; Integrasi Sumber Resmi</p>
          <a href="https://www.bps.go.id/" target="_blank" rel="noopener noreferrer">Portal Resmi Badan Pusat Statistik (BPS) ↗</a>
          <a href="https://www.bi.go.id/" target="_blank" rel="noopener noreferrer">Bank Indonesia — Data &amp; Moneter ↗</a>
          <a href="https://webapi.bps.go.id/developer/" target="_blank" rel="noopener noreferrer">Dokumentasi WebAPI BPS ↗</a>
          <a href="https://www.kemenkeu.go.id/satudata" target="_blank" rel="noopener noreferrer">Kementerian Keuangan — Satu Data Fiskal ↗</a>
          <a href="https://www.bkpm.go.id/" target="_blank" rel="noopener noreferrer">Kementerian Investasi — BKPM ↗</a>
        </div>
        <div className="footer-col">
          <p className="footer-head">Transparansi &amp; Keberlakuan</p>
          <a href="#tentang">Prosedur Verifikasi Data</a>
          <a href="#tentang">Kamus Indikator Ekonomi</a>
          <a href="#tentang">Kebijakan Privasi &amp; Lisensi Terbuka</a>
          <a href="#tentang">Kontak Tim Kurasi DEKSI</a>
        </div>
      </div>
      <div className="footer-bottom">
        <span>© 2024 DEKSI — Deteksi Ekonomi Indonesia. Portal data dan analisis makroekonomi terpadu.</span>
        <span className="footer-note">🛡️ Standar Integritas Data Statistik Nasional</span>
      </div>
    </footer>
  );
}
