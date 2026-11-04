export function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <a className="brand" href="#dashboard">
          <span className="brand-mark">DK</span>
          <span className="brand-text">
            <span className="brand-name">
              DEKSI <span className="brand-badge">PLATFORM DATA &amp; ANALISIS</span>
            </span>
            <span className="brand-sub">Deteksi Ekonomi Indonesia</span>
          </span>
        </a>
        <nav className="navbar-nav" aria-label="Navigasi utama">
          <a className="nav-link nav-link-active" href="#dashboard">
            ● Dashboard
          </a>
          <a className="nav-link" href="#indikator">Indikator</a>
          <a className="nav-link" href="#analisis">Analisis</a>
          <a className="nav-link" href="#sumber-data">Sumber Data</a>
          <a className="nav-link" href="#tentang">Tentang DEKSI</a>
        </nav>
        <div className="navbar-actions">
          <label className="search">
            <span className="search-glyph">🔍</span>
            <input type="search" placeholder="Cari data atau indikator…" />
          </label>
          <button type="button" className="login-btn">
            <span aria-hidden="true">🔒</span> Masuk
          </button>
        </div>
      </div>
    </header>
  );
}

export function Hero() {
  return (
    <section className="hero" id="dashboard">
      <p className="hero-eyebrow">
        Platform Data &amp; Analisis Ekonomi • Data dari Kementerian &amp; Lembaga Resmi
      </p>
      <h1 className="hero-title">Kondisi Ekonomi Indonesia</h1>
      <p className="hero-sub">
        Ringkasan indikator ekonomi makro terbaru berdasarkan data resmi
        kementerian dan lembaga negara yang diperbarui secara berkala.
      </p>
      <div className="hero-strip">
        <span className="strip-item">🕘 Terakhir diperbarui: 15 Okt 2024, 09:00 WIB</span>
        <span className="strip-item">🗓️ Periode Analisis: Q2 2024 / Semester I</span>
        <span className="strip-right">✅ Sumber Terverifikasi: BPS • BI • KEMENKEU • BKPM</span>
      </div>
    </section>
  );
}
