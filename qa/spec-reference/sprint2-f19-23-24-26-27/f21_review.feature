@sprint2 @analysis-review @f21
Feature: F21 Detail Peninjauan Hasil Analisis

  @BDD-F21-01 @R_F21_01 @api
  Scenario: BDD-F21-01 - Daftar hasil analisis memuat versi pending
    Given Admin memiliki versi analisis pending tanpa riwayat keputusan
    When Admin meminta daftar hasil analisis pending
    Then daftar memuat versi tersebut dengan status pending

  @BDD-F21-02 @R_F21_02 @api
  Scenario: BDD-F21-02 - Daftar mendukung filter status dan pagination
    Given Admin memiliki versi analisis published dan needs_revision
    When Admin meminta daftar hasil analisis semua status
    Then daftar memuat kedua versi dengan status masing-masing

  @BDD-F21-03 @R_F21_03 @api
  Scenario: BDD-F21-03 - Detail versi memuat bukti dan riwayat keputusan
    Given Admin memiliki versi analisis pending dengan payload lengkap
    When Admin meminta detail versi tersebut
    Then detail memuat nilai satuan periode sumber dan riwayat kosong

  @BDD-F21-04 @R_F21_04 @api
  Scenario: BDD-F21-04 - Detail versi tidak dikenal mengembalikan 404
    Given Admin telah masuk
    When Admin meminta detail versi analisis yang tidak ada
    Then server menolak dengan status 404

  @BDD-F21-05 @R_F21_05 @api
  Scenario: BDD-F21-05 - Peninjauan dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta daftar hasil analisis
    Then server menolak akses hasil analisis dengan status 401

  @BDD-F21-06 @R_F21_06 @browser
  Scenario: BDD-F21-06 - Panel peninjauan menampilkan bukti satu tampilan [NOT BOUND]
    Given Admin membuka detail versi analisis
    When halaman selesai dimuat
    Then nilai resmi turunan Engine diagnostic flags narasi dan Source Trace tampil bersama

  @BDD-F21-07 @R_F21_07 @browser
  Scenario: BDD-F21-07 - Versi terpublikasi dapat dibuka ulang untuk tinjau ulang [NOT BOUND]
    Given versi analisis sudah terpublikasi
    When Admin membuka ulang versi tersebut
    Then bukti versi tampil dengan status publikasi terakhir
