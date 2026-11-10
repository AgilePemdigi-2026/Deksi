@sprint2 @feedback_admin @f15
Feature: F15 Daftar Umpan Balik Admin

  @BDD_F15_01 @R_F15_01 @api
  Scenario: BDD-F15-01 - Daftar menampilkan kategori tanggal dan status
    Given Admin memiliki dua laporan umpan balik sintetis dengan kategori dan status berbeda
    When Admin meminta daftar umpan balik
    Then daftar berisi kedua laporan dengan kategori tanggal dan status

  @BDD_F15_02 @R_F15_02 @api
  Scenario: BDD-F15-02 - Daftar kosong ditangani sebagai hasil valid
    Given Admin memiliki daftar umpan balik kosong
    When Admin meminta daftar umpan balik
    Then respons sukses menampilkan daftar kosong tanpa error

  @BDD_F15_03 @R_F15_03 @api
  Scenario: BDD-F15-03 - Daftar umpan balik dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta daftar umpan balik Admin
    Then server menolak akses daftar dengan status 401
