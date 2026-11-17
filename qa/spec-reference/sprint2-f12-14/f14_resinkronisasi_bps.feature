# Rancangan saja: seluruh skenario NOT RUN, belum ada binding/runner.
@draft @not_run @sprint2 @f14
Feature: F14 Sinkronisasi ulang BPS oleh Admin
  Agar Admin dapat meminta akuisisi ulang secara terkendali tanpa publikasi otomatis

  @BDD_F14_01 @browser
  Scenario: Permintaan BPS aktif setelah pemeriksaan riwayat
    Given Admin masuk dan sumber BPS sintetis aktif tanpa pekerjaan aktif
    And Admin telah memeriksa riwayat dan menandai pernyataan pemeriksaan
    When Admin memilih sinkronkan dan mengonfirmasi permintaan
    Then aplikasi menampilkan identitas pekerjaan dan status server
    And pekerjaan yang baru diterima tidak langsung disebut berhasil

  @BDD_F14_02 @browser
  Scenario: Permintaan dibatalkan saat konfirmasi
    Given Admin masuk dan sumber BPS sintetis aktif siap disinkronkan
    When Admin membatalkan dialog konfirmasi
    Then tidak ada permintaan sinkronisasi baru dikirim

  @BDD_F14_03 @api
  Scenario: Sumber nonaktif atau selain BPS tidak membuat pekerjaan
    Given Admin masuk dan dua sumber sintetis terdiri dari BPS nonaktif dan sumber lain aktif
    When Admin meminta sinkronisasi ulang untuk masing-masing sumber
    Then setiap permintaan ditolak dan tidak ada pekerjaan baru dibuat

  @BDD_F14_04 @api
  Scenario: Permintaan dengan identitas yang sama tidak membuat duplikat
    Given Admin sudah mengirim requestId valid untuk sumber BPS sintetis
    When Admin yang sama mengirim lagi requestId yang sama untuk sumber yang sama
    Then server mengembalikan identitas pekerjaan yang sama
    And tidak ada pekerjaan kedua dibuat

  @BDD_F14_05 @api
  Scenario: Dua permintaan berbeda tidak menjalankan pekerjaan aktif ganda
    Given pekerjaan BPS sintetis sudah aktif
    When Admin mengirim permintaan baru dengan requestId berbeda
    Then permintaan baru ditolak karena terdapat pekerjaan aktif
    And hanya pekerjaan aktif semula yang dipertahankan

  @BDD_F14_06 @browser
  Scenario: Status queued ditemukan kembali setelah halaman dimuat ulang
    Given pekerjaan BPS sintetis diterima dan masih dalam antrean
    When Admin memuat ulang halaman Kelola Sumber
    Then pekerjaan aktif dan status antrean tetap dapat dilihat
    And aplikasi tidak mengirim permintaan baru secara otomatis

  @BDD_F14_07 @browser
  Scenario: Jawaban permintaan tidak pasti tidak menyebabkan pengiriman ulang otomatis
    Given Admin mengonfirmasi permintaan BPS sintetis
    When koneksi terputus sebelum hasil permintaan dapat dipastikan
    Then aplikasi menampilkan hasil tidak diketahui dan meminta pemeriksaan antrean atau riwayat
    And aplikasi tidak mengirim ulang permintaan secara otomatis

  @BDD_F14_08 @api
  Scenario: Rekonsiliasi manual mencatat hasil unknown tanpa mengarang hasil akhir
    Given pekerjaan sintetis berstatus running dengan run terkait yang juga running
    When Admin mengonfirmasi pemeriksaan manual dengan alasan yang valid
    Then pekerjaan dan run berstatus unknown dengan identitas pemeriksa waktu dan alasan tercatat
    And waktu selesai aktual tidak direka dan hasil tidak disebut sukses atau gagal

  @BDD_F14_09 @api
  Scenario: Rekonsiliasi tanpa konfirmasi atau alasan valid ditolak
    Given pekerjaan sintetis berstatus running dengan run terkait
    When Admin mengirim rekonsiliasi tanpa konfirmasi atau dengan alasan tidak valid
    Then server menolak permintaan dan status pekerjaan serta run tidak berubah

  @BDD_F14_10 @api
  Scenario: Worker lama tidak dapat melanjutkan penulisan setelah rekonsiliasi
    Given pekerjaan BPS sintetis telah direkonsiliasi menjadi unknown
    When worker lama mencoba membuat metadata atau kandidat melalui jalur BPS yang dilindungi
    Then penulisan tersebut ditolak tanpa membuat kandidat baru
    And rekonsiliasi tidak mengklaim request jaringan yang sudah dikirim telah dibatalkan

  @BDD_F14_11 @api
  Scenario: Hasil akuisisi tidak otomatis menjadi nilai publik
    Given terdapat nilai publik terakhir yang sudah direview
    When sinkronisasi sintetis menghasilkan kandidat baru yang belum direview
    Then nilai publik terakhir tetap tersedia
    And kandidat baru tidak dipublikasikan tanpa review

  @BDD_F14_12 @api
  Scenario: Pengunjung anonim tidak dapat meminta sinkronisasi ulang
    Given pengunjung tanpa sesi Admin dan sumber BPS sintetis aktif
    When pengunjung meminta sinkronisasi ulang
    Then server menolak permintaan tanpa membuat pekerjaan
