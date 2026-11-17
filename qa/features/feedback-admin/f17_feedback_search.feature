@sprint2 @feedback_admin @f17
Feature: F17 Cari Umpan Balik

  @BDD_F17_01 @R_F17_01 @api
  Scenario: BDD-F17-01 - Kata kunci menyaring laporan terkait
    Given Admin memiliki laporan dengan kata kunci indikator dan laporan pembanding
    When Admin mencari umpan balik menggunakan kata kunci indikator
    Then hanya laporan yang cocok ditampilkan

  @BDD_F17_02 @R_F17_02 @api
  Scenario: BDD-F17-02 - Pencarian tanpa hasil menghasilkan daftar kosong
    Given Admin memiliki laporan umpan balik sintetis
    When Admin mencari umpan balik menggunakan kata kunci yang tidak ada
    Then pencarian sukses menampilkan nol hasil
