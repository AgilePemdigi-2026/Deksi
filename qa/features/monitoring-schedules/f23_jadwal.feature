@sprint2 @schedules @f23
Feature: F23 Konfigurasi Jadwal Pembaruan

  @BDD-F23-01 @R_F23_01 @api
  Scenario: BDD-F23-01 - Daftar jadwal menampilkan default untuk sumber tanpa konfigurasi
    Given Admin memiliki sumber sintetis aktif tanpa konfigurasi jadwal
    When Admin meminta daftar jadwal
    Then daftar memuat sumber tersebut dengan interval default dan status aktif

  @BDD-F23-02 @R_F23_02 @api
  Scenario: BDD-F23-02 - Pembaruan jadwal valid tersimpan berversi dan diaudit
    Given Admin memiliki sumber sintetis aktif dan token CSRF valid
    When Admin menyimpan jadwal interval 7 hari nonaktif dengan jam jalan
    Then jadwal tersimpan berversi dengan audit dan teks jadwal sumber ikut berubah

  @BDD-F23-03 @R_F23_03 @api
  Scenario: BDD-F23-03 - Payload tidak valid ditolak tanpa mengubah data
    Given Admin memiliki sumber sintetis aktif dan token CSRF valid
    When Admin menyimpan jadwal dengan interval di luar rentang dan format jam salah
    Then server menolak dengan status 400 dan konfigurasi tetap kosong

  @BDD-F23-04 @R_F23_04 @api
  Scenario: BDD-F23-04 - Sumber nonaktif dan tidak dikenal tidak dapat dijadwalkan
    Given Admin memiliki sumber sintetis nonaktif dan token CSRF valid
    When Admin menyimpan jadwal untuk sumber nonaktif dan sumber tidak ada
    Then server menolak sumber nonaktif dan yang tidak ada tanpa audit baru

  @BDD-F23-05 @R_F23_05 @api
  Scenario: BDD-F23-05 - Jadwal dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta daftar jadwal
    Then server menolak akses jadwal dengan status 401

  @BDD-F23-06 @R_F23_06 @api
  Scenario: BDD-F23-06 - Jadwal berikutnya hanya memuat yang aktif dan terurut
    Given Admin memiliki dua sumber sintetis dengan jadwal aktif dan nonaktif
    When Admin meminta jadwal berikutnya
    Then daftar hanya memuat sumber aktif terurut waktu jalan

  @BDD-F23-07 @R_F23_07 @api
  Scenario: BDD-F23-07 - Perubahan jadwal tidak mengganggu akses publik
    Given dashboard publik menampilkan satu observasi terpublikasi
    When Admin menyimpan jadwal baru untuk sumber observasi tersebut
    Then dashboard publik tetap menampilkan observasi yang sama

