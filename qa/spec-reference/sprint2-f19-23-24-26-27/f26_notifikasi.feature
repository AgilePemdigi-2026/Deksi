@sprint2 @notifications @f26
Feature: F26 Konfigurasi Notifikasi

  @BDD-F26-01 @R_F26_01 @api
  Scenario: BDD-F26-01 - Daftar menampilkan tiga jenis dengan default dan kanal
    Given Admin telah masuk tanpa preferensi notifikasi
    When Admin meminta daftar notifikasi
    Then daftar memuat tiga jenis dengan nilai default dan kanal event-log

  @BDD-F26-02 @R_F26_02 @api
  Scenario: BDD-F26-02 - Perubahan preferensi tersimpan berversi dan diaudit
    Given Admin telah masuk dengan token CSRF valid
    When Admin menonaktifkan notifikasi gagal sinkronisasi dengan alasan
    Then preferensi tersimpan berversi dengan audit

  @BDD-F26-03 @R_F26_03 @api
  Scenario: BDD-F26-03 - Jenis tidak dikenal dan flag bukan boolean ditolak
    Given Admin telah masuk dengan token CSRF valid
    When Admin mengubah jenis tidak dikenal dan flag bukan boolean
    Then server menolak dengan status 404 dan 400 tanpa audit baru

  @BDD-F26-04 @R_F26_04 @api
  Scenario: BDD-F26-04 - Event kegagalan tercatat mengikuti preferensi aktif
    Given Admin memiliki sumber sintetis dan preferensi gagal sinkronisasi aktif
    When sinkronisasi sumber gagal
    Then event tercatat bertanda notified

  @BDD-F26-05 @R_F26_05 @api
  Scenario: BDD-F26-05 - Event tetap tercatat tanpa tanda saat preferensi mati
    Given Admin memiliki sumber sintetis dan preferensi gagal sinkronisasi nonaktif
    When sinkronisasi sumber gagal
    Then event tercatat tanpa tanda notified

  @BDD-F26-06 @R_F26_06 @api
  Scenario: BDD-F26-06 - Notifikasi dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta daftar notifikasi
    Then server menolak akses notifikasi dengan status 401

  @BDD-F26-07 @R_F26_07 @browser
  Scenario: BDD-F26-07 - Admin melihat daftar event mengikuti preferensi [NOT BOUND]
    Given Admin membuka halaman notifikasi dengan event sintetis
    When preferensi diubah
    Then daftar event mencerminkan status notified terbaru

  @BDD-F26-08 @R_F26_08 @browser
  Scenario: BDD-F26-08 - Pembatalan sebelum simpan tidak mengubah preferensi [NOT BOUND]
    Given Admin membuka halaman notifikasi dengan preferensi berubah belum disimpan
    When Admin membatalkan sebelum menyimpan
    Then preferensi tetap pada nilai terakhir tersimpan
