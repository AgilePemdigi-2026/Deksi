# Rancangan saja: seluruh skenario NOT RUN, belum ada binding/runner.
@draft @not_run @sprint2 @f12
Feature: F12 Mengendalikan status aktif sumber data
  Agar akuisisi baru tidak menggunakan sumber yang dinonaktifkan
  Sebagai Admin saya dapat meninjau dan mengubah status sumber dengan revisi

  @BDD_F12_01 @browser
  Scenario: Admin menonaktifkan sumber yang aktif
    Given Admin masuk dan sumber sintetis aktif memiliki revisi 1
    When Admin menonaktifkan sumber menggunakan revisi 1
    Then status sumber menjadi nonaktif dan revisi perubahan tersimpan
    And status nonaktif terlihat setelah daftar sumber dimuat ulang

  @BDD_F12_02 @browser
  Scenario: Admin mengaktifkan kembali sumber nonaktif
    Given Admin masuk dan sumber sintetis nonaktif memiliki revisi 2
    When Admin mengaktifkan sumber menggunakan revisi 2
    Then status sumber menjadi aktif dan revisi baru tercatat

  @BDD_F12_03 @api
  Scenario: Perubahan tanpa versi revisi yang diwajibkan ditolak
    Given Admin masuk dan sumber sintetis berada pada revisi 2
    When Admin mengirim perubahan status tanpa expectedRevision
    Then respons menyatakan permintaan tidak valid
    And status dan riwayat revisi tidak berubah

  @BDD_F12_04 @api
  Scenario: Pembaruan dari layar usang tidak menimpa perubahan lain
    Given dua Admin membaca sumber sintetis pada revisi 2
    And Admin pertama sudah menyimpan perubahan sehingga revisi menjadi 3
    When Admin kedua mencoba mengganti status menggunakan revisi 2
    Then server menolak perubahan dengan konflik revisi
    And perubahan Admin pertama tetap tersimpan

  @BDD_F12_05 @api
  Scenario: Sumber nonaktif dilewati sebelum akuisisi baru
    Given sumber sintetis nonaktif dan provider diganti dengan stub yang mencatat panggilan
    When proses akuisisi baru untuk sumber tersebut dimulai
    Then proses tidak memanggil provider atau membuat run sinkronisasi baru
    And tidak ada catatan palsu bahwa sinkronisasi berhasil

  @BDD_F12_06 @api
  Scenario: Penonaktifan saat pekerjaan berjalan tidak digambarkan sebagai pembatalan otomatis
    Given pekerjaan sintetis sudah dimulai ketika sumber masih aktif
    When Admin menonaktifkan sumber
    Then tidak ada pekerjaan baru dimulai untuk sumber nonaktif
    And status pekerjaan yang sudah dimulai mengikuti hasilnya sendiri

  @BDD_F12_07 @api
  Scenario: Pengunjung anonim tidak dapat mengubah status
    Given pengunjung tanpa sesi Admin dan sumber sintetis aktif
    When pengunjung mengirim perubahan status
    Then server menolak perubahan dan status tetap aktif

  @BDD_F12_08 @browser
  Scenario: Simpan berhasil tetapi muat ulang daftar gagal
    Given Admin menonaktifkan sumber dan server mengonfirmasi penyimpanan
    When permintaan berikutnya untuk memuat daftar gagal
    Then pengguna diberi tahu bahwa penyimpanan dan pembaruan tampilan memiliki hasil berbeda
    And aplikasi tidak otomatis mengirim ulang perubahan status
