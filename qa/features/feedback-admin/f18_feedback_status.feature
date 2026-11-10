@sprint2 @feedback_admin @f18
Feature: F18 Ubah Status Umpan Balik

  @BDD_F18_01 @R_F18_01 @api
  Scenario: BDD-F18-01 - Perubahan status menyimpan catatan waktu dan audit
    Given Admin memiliki laporan pending dan token CSRF valid
    When Admin mengubah status menjadi resolved dengan catatan penanganan sintetis
    Then status catatan waktu pembaruan dan audit log tersimpan

  @BDD_F18_02 @R_F18_02 @api
  Scenario: BDD-F18-02 - Status tidak valid tidak mengubah laporan
    Given Admin memiliki laporan pending dan token CSRF valid
    When Admin mengirim perubahan dengan status yang tidak valid
    Then server menolak perubahan dan tidak membuat audit log

  @BDD_F18_03 @R_F18_03 @api
  Scenario: BDD-F18-03 - Pengunjung anonim tidak dapat mengubah status
    Given laporan pending tersedia tanpa sesi Admin dan token CSRF valid
    When pengunjung anonim mengirim perubahan status
    Then server menolak perubahan dan status laporan tetap pending
