@sprint2 @feedback_admin @f16
Feature: F16 Detail Umpan Balik

  @BDD_F16_01 @R_F16_01 @api
  Scenario: BDD-F16-01 - Detail mempertahankan laporan indikator dan status
    Given Admin memiliki laporan sintetis terkait indikator PDB
    When Admin membuka detail laporan tersebut
    Then detail menunjukkan indikator terkait dan status yang sama dengan daftar

  @BDD_F16_02 @R_F16_02 @api
  Scenario: BDD-F16-02 - Detail laporan tak dikenal tidak ditemukan
    Given Admin memiliki sesi valid tanpa laporan terpilih
    When Admin meminta detail laporan yang tidak ada
    Then server mengembalikan status 404 tanpa detail laporan
