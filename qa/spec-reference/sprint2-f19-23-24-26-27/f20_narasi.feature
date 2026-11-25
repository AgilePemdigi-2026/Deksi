@sprint2 @grounded-ai @f20
Feature: F20 Penjelasan Analisis Grounded AI

  # STATUS: DRAFT / NOT BOUND. Tidak ada endpoint narasi di backend dan tidak
  # ada komponen narasi di frontend. Seluruh skenario di bawah adalah rancangan
  # menunggu implementasi; JANGAN di-binding sampai kontrak narasi disepakati.
  # Fallback yang SUDAH ada: indikator terstruktur dan Source Trace tetap tampil.

  @BDD-F20-01 @R_F20_01 @api
  Scenario: BDD-F20-01 - Narasi menjelaskan fakta terstruktur tanpa mengubah angka [NOT BOUND]
    Given indikator terpublikasi dengan structured facts versi tertentu
    When User Publik meminta narasi penjelasan versi tersebut
    Then narasi memuat periode freshness dan diagnostic flags tanpa angka baru

  @BDD-F20-02 @R_F20_02 @api
  Scenario: BDD-F20-02 - Narasi mengikuti versi indikator dan periode yang dilihat [NOT BOUND]
    Given dua versi periode tersedia untuk indikator yang sama
    When User Publik meminta narasi untuk periode kedua
    Then narasi sesuai versi periode kedua bukan versi terbaru

  @BDD-F20-03 @R_F20_03 @api
  Scenario: BDD-F20-03 - Klaim sebab-akibat hanya bila didukung evidence [NOT BOUND]
    Given diagnostic rules tidak mendukung hubungan sebab-akibat
    When User Publik meminta narasi penjelasan
    Then narasi tidak menyatakan hubungan sebab-akibat yang tak didukung

  @BDD-F20-04 @R_F20_04 @api
  Scenario: BDD-F20-04 - Narasi tak tersedia tidak menghilangkan data terstruktur [NOT BOUND]
    Given indikator terpublikasi tanpa narasi tersedia
    When User Publik membuka detail indikator
    Then indikator terstruktur dan Source Trace tampil dengan keterangan narasi tidak tersedia

  @BDD-F20-05 @R_F20_05 @browser
  Scenario: BDD-F20-05 - Narasi tertaut ke Source Trace [NOT BOUND]
    Given User Publik melihat narasi penjelasan
    When pengguna mengikuti tautan dasar narasi
    Then halaman Source Trace versi yang sama terbuka
