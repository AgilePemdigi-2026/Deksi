# Executable BDD: F11 berjalan melawan API disposable sungguhan (tanpa browser, tanpa jaringan luar).
# Revisi append-only: edit sukses menaikkan version, gagal mempertahankan config terakhir.
# Tags @sources (BUKAN @sprint1) agar suite baseline/as-built tidak ikut memungut.
#
# ============ BEHAT CHEATSHEET (ringkas, copy-paste) ============
# Run suite ini:
#   .\venv\Scripts\python.exe qa/run_bdd.py --suite sources --tags @sources --label sources-f09f11
#   .\venv\Scripts\python.exe qa/report_results.py qa/artifacts/<timestamp>-sources-f09f11
@sources @f11 @api
Feature: F11 Edit Sumber Data

  Background:
    Given admin staf sudah login
    And sumber "BPS_T" revision 1 sudah ada

  @BDD_F11_01 @R_F11_01 @api
  Scenario: BDD-F11-01 - Edit deskripsi naikkan revisi
    Given field "description" diubah menjadi "Deskripsi revisi uji"
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 200 revision naik ke 2 dan changedFields memuat "description"

  @BDD_F11_02 @R_F11_05 @api
  Scenario: BDD-F11-02 - Tanpa login ditolak 401
    Given client anonim tanpa session admin
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload valid
    Then respons 401 dan revision tetap 1

  @BDD_F11_03 @R_F11_02 @api
  Scenario: BDD-F11-03 - sourceId tidak boleh diubah
    Given payload ubah memuat sourceId "BPS_LAIN"
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 400 menyebut sourceId dan revision tetap 1

  @BDD_F11_04 @R_F11_03 @api
  Scenario: BDD-F11-04 - Endpoint berubah tak terjangkau ditolak, config lama kept
    Given endpointUrl baru tak terjangkau
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 400 menyebut endpoint dan revision tetap 1

  @BDD_F11_05 @R_F11_01 @api
  Scenario: BDD-F11-05 - Tanpa perubahan tidak buat revisi baru
    Given payload ubah sama dengan konfigurasi tersimpan
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 200 changedFields kosong dan revision tetap 1

  @BDD_F11_06 @R_F11_03 @api
  Scenario: BDD-F11-06 - primaryUrl bukan-url ditolak
    Given field "primaryUrl" diubah menjadi "bukan-url"
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 400 dan revision tetap 1

  @BDD_F11_07 @R_F11_03 @api
  Scenario: BDD-F11-07 - Status di luar pilihan ditolak
    Given field "status" diubah menjadi "arsip"
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 400 dan revision tetap 1

  @BDD_F11_08 @R_F11_01 @api
  Scenario: BDD-F11-08 - Riwayat revisi append-only terbaca
    Given edit deskripsi sudah tersimpan sebagai revision 2
    When client meminta GET "/api/admin/sources/BPS_T/revisions/"
    Then respons 200 dengan 2 revisi berurutan dan before sama dengan after sebelumnya
