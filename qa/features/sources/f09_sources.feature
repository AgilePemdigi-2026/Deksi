# Executable BDD: F09 berjalan melawan API disposable sungguhan (tanpa browser).
# Tags @sources (BUKAN @sprint1) agar suite baseline/as-built tidak ikut memungut.
# @sprint1 @not_run hanya untuk file spec di qa/features/*.Data (dokumen, tak tereksekusi).
#
# ============ BEHAT CHEATSHEET (ringkas, copy-paste) ============
# Struktur: Feature > [Background] > Scenario > Given-When-Then.
# Run suite ini:
#   .\venv\Scripts\python.exe qa/run_bdd.py --suite sources --tags @sources --label sources-f09f11
#   .\venv\Scripts\python.exe qa/report_results.py qa/artifacts/<timestamp>-sources-f09f11
# Behat (PHP) setara: vendor/bin/behat --tags='@sources' (lihat FeatureContext di file spec).
@sources @f09 @api
Feature: F09 Daftar Sumber Data

  @BDD_F09_01 @R_F09_01 @api
  Scenario: BDD-F09-01 - Daftar sumber tampil lengkap
    Given katalog dua sumber publik dengan observasi reviewed tersedia
    When client meminta GET "/api/sources/"
    Then respons daftar sumber berstatus 200 dengan 2 sumber dan field lengkap

  @BDD_F09_02 @R_F09_01 @api
  Scenario: BDD-F09-02 - Detail sumber case-insensitive dan hanya indikator reviewed
    Given sumber "TEST_A" dengan satu observasi published-direview dan satu draft
    When client meminta GET "/api/sources/test_a/"
    Then respons detail sumber "TEST_A" berstatus 200 dengan 1 indikator

  @BDD_F09_03 @R_F09_01 @api
  Scenario: BDD-F09-03 - Daftar indikator per sumber konsisten dengan detail
    Given sumber "TEST_A" dengan dua indikator published-direview
    When client meminta GET "/api/sources/TEST_A/indicators/"
    Then respons indikator sumber "TEST_A" berstatus 200 dengan 2 indikator

  @BDD_F09_04 @R_F09_02 @api
  Scenario: BDD-F09-04 - Sumber tak dikenal 404 tanpa bocor data
    Given tidak ada sumber "X_TIDAK_ADA"
    When client meminta GET "/api/sources/X_TIDAK_ADA/"
    Then respons berstatus 404 tanpa daftar sumber

  @BDD_F09_05 @R_F09_02 @api
  Scenario: BDD-F09-05 - Indikator sumber kosong tetap 200
    Given sumber baru "TEST_EMPTY" tanpa observasi
    When client meminta GET "/api/sources/TEST_EMPTY/indicators/"
    Then respons indikator sumber "TEST_EMPTY" berstatus 200 dengan 0 indikator

  @BDD_F09_06 @R_F09_01 @api
  Scenario: BDD-F09-06 - Detail sumber huruf kecil semua
    Given sumber "TEST_A" dengan satu observasi published-direview dan satu draft
    When client meminta GET "/api/sources/test_a/"
    Then respons detail sumber "TEST_A" berstatus 200 dengan 1 indikator

  @BDD_F09_07 @R_F09_01 @api
  Scenario: BDD-F09-07 - Sumber tanpa observasi reviewed tidak tersedia
    Given sumber "TEST_DRAFT" hanya dengan observasi draft
    When client meminta GET "/api/sources/TEST_DRAFT/"
    Then respons detail sumber "TEST_DRAFT" berstatus 200 dengan 0 indikator
