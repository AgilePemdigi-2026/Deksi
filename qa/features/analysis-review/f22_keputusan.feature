@sprint2 @publish-decision @f22
Feature: F22 Keputusan Kelayakan Publikasi

  @BDD-F22-01 @R_F22_01 @api
  Scenario: BDD-F22-01 - Keputusan publish menerbitkan observasi dan audit
    Given Admin memiliki versi analisis pending dan token CSRF valid
    When Admin menetapkan keputusan publish tanpa catatan
    Then versi menjadi published observasi terbit dan audit publish tercatat

  @BDD-F22-02 @R_F22_02 @api
  Scenario: BDD-F22-02 - Keputusan perlu revisi wajib catatan dan tanpa publikasi
    Given Admin memiliki versi analisis pending dan token CSRF valid
    When Admin menetapkan keputusan perlu revisi dengan catatan ketidaksesuaian
    Then versi menjadi needs_revision tanpa observasi baru dan audit tercatat

  @BDD-F22-03 @R_F22_03 @api
  Scenario: BDD-F22-03 - Penolakan tanpa catatan ditolak
    Given Admin memiliki versi analisis pending dan token CSRF valid
    When Admin menetapkan keputusan reject tanpa catatan
    Then server menolak dengan status 400 dan versi tetap pending

  @BDD-F22-04 @R_F22_04 @api
  Scenario: BDD-F22-04 - Keputusan ganda dan fingerprint berubah ditolak
    Given Admin memiliki versi analisis pending dan token CSRF valid
    When Admin menetapkan keputusan dua kali dan dengan fingerprint salah
    Then pengulangan dan fingerprint salah ditolak dengan status 409

  @BDD-F22-05 @R_F22_05 @api
  Scenario: BDD-F22-05 - Keputusan dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung menetapkan keputusan publikasi
    Then server menolak akses keputusan dengan status 401

