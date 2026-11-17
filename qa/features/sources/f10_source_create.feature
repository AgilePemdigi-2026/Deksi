# Executable BDD: F10 berjalan melawan API disposable sungguhan (tanpa browser, tanpa jaringan luar).
# Endpoint tanpa http tidak di-probe; endpoint http menunjuk 127.0.0.1:9 (refused cepat, loopback diizinkan audit hook).
# Tags @sources (BUKAN @sprint1) agar suite baseline/as-built tidak ikut memungut.
#
# ============ BEHAT CHEATSHEET (ringkas, copy-paste) ============
# Run suite ini:
#   .\venv\Scripts\python.exe qa/run_bdd.py --suite sources --tags @sources --label sources-f09f11
#   .\venv\Scripts\python.exe qa/report_results.py qa/artifacts/<timestamp>-sources-f09f11
@sources @f10 @api
Feature: F10 Tambah Sumber Data

  Background:
    Given admin staf sudah login

  @BDD_F10_01 @R_F10_01 @api
  Scenario: BDD-F10-01 - Tambah sumber file_xlsx tanpa endpoint lolos
    Given payload tambah sumber file_xlsx valid
    When client POST ke "/api/admin/sources/create/" dengan payload tambah
    Then respons 201 dengan revision tambah version 1

  @BDD_F10_02 @R_F10_05 @api
  Scenario: BDD-F10-02 - Tanpa login ditolak 401
    Given client anonim tanpa session admin
    When client POST ke "/api/admin/sources/create/" dengan payload valid
    Then respons 401 dan sumber "SRC_F10_NEW" tidak tersimpan

  @BDD_F10_03 @R_F10_05 @api
  Scenario: BDD-F10-03 - Akun non-staf ditolak 403
    Given session login milik akun non-staf yang valid
    When client POST ke "/api/admin/sources/create/" dengan payload valid
    Then respons 403 dan sumber "SRC_F10_NEW" tidak tersimpan

  @BDD_F10_04 @R_F10_02 @api
  Scenario: BDD-F10-04 - Duplikat sourceId ditolak 409
    Given sumber "SRC_F10_DUP" revision 1 sudah ada
    When client POST ke "/api/admin/sources/create/" dengan sourceId "SRC_F10_DUP" yang sama
    Then respons 409 dan revision tetap 1

  @BDD_F10_05 @R_F10_03 @api
  Scenario: BDD-F10-05 - Endpoint http tak terjangkau ditolak, data lama aman
    Given payload tambah sumber api_bps dengan endpoint tak terjangkau
    When client POST ke "/api/admin/sources/create/" dengan payload tambah
    Then respons 400 menyebut endpoint dan sumber tidak tersimpan

  @BDD_F10_06 @R_F10_03 @api
  Scenario: BDD-F10-06 - Karakter sourceId invalid ditolak
    Given payload tambah sumber dengan sourceId "BAD-ID!"
    When client POST ke "/api/admin/sources/create/" dengan payload tambah
    Then respons 400 dan tidak ada sumber baru tersimpan

  @BDD_F10_07 @R_F10_02 @api
  Scenario: BDD-F10-07 - Kombinasi nama dan institusi ganda ditolak
    Given sumber bernama "Data Investasi" dari "BKPM" sudah terdaftar
    When client POST ke "/api/admin/sources/create/" dengan nama dan institusi sama tetapi sourceId berbeda
    Then respons 400 menyebut kombinasi sudah terdaftar

  @BDD_F10_08 @R_F10_01 @api
  Scenario: BDD-F10-08 - Daftar metode akuisisi tersedia untuk form admin
    When client meminta GET "/api/admin/sources/acquisition-methods/"
    Then respons 200 memuat metode file_xlsx
