@sprint2 @f14
Feature: F14 Sinkronisasi ulang BPS oleh Admin
  Agar Admin meminta akuisisi ulang secara terkendali tanpa publikasi otomatis

  @BDD_F14_01 @browser
  Scenario: Permintaan BPS aktif setelah pemeriksaan riwayat
    Given Admin browser F14 masuk dan sumber BPS sintetis aktif tanpa pekerjaan aktif
    And Admin F14 telah memeriksa riwayat dan menandai pernyataan pemeriksaan
    When Admin F14 memilih sinkronkan dan mengonfirmasi permintaan
    Then browser F14 menampilkan identitas pekerjaan dan status server
    And pekerjaan F14 yang baru diterima tidak langsung disebut berhasil

  @BDD_F14_02 @browser
  Scenario: Permintaan dibatalkan saat konfirmasi
    Given Admin browser F14 masuk dan sumber BPS sintetis aktif siap disinkronkan
    When Admin F14 membatalkan dialog konfirmasi
    Then browser F14 tidak mengirim permintaan sinkronisasi baru

  @BDD_F14_03 @api
  Scenario: Sumber nonaktif atau selain BPS tidak membuat pekerjaan
    Given Admin API F14 login dan tersedia sumber BPS nonaktif serta sumber lain aktif
    When Admin API F14 meminta sinkronisasi ulang untuk masing-masing sumber
    Then server F14 menolak setiap permintaan dan tidak membuat pekerjaan

  @BDD_F14_04 @api
  Scenario: Permintaan dengan identitas yang sama tidak membuat duplikat
    Given Admin API F14 login dan sumber BPS sintetis aktif dengan requestId valid
    When Admin API F14 mengirim dua kali requestId yang sama untuk sumber yang sama
    Then server F14 mengembalikan identitas pekerjaan yang sama tanpa pekerjaan kedua

  @BDD_F14_05 @api
  Scenario: Dua permintaan berbeda tidak menjalankan pekerjaan aktif ganda
    Given Admin API F14 login dan pekerjaan BPS sintetis sudah aktif
    When Admin API F14 mengirim permintaan baru dengan requestId berbeda
    Then server F14 menolak permintaan karena terdapat pekerjaan aktif
    And hanya pekerjaan F14 aktif semula yang dipertahankan

  @BDD_F14_06 @browser
  Scenario: Status queued ditemukan kembali setelah halaman dimuat ulang
    Given Admin browser F14 masuk dan pekerjaan BPS sintetis diterima serta masih dalam antrean
    When Admin F14 memuat ulang halaman Kelola Sumber
    Then browser F14 menampilkan pekerjaan aktif dan status antrean yang sama
    And pemuatan ulang F14 tidak mengirim permintaan baru secara otomatis

  @BDD_F14_07 @browser
  Scenario: Jawaban permintaan tidak pasti tidak menyebabkan pengiriman ulang otomatis
    Given Admin browser F14 masuk dan sumber BPS sintetis aktif siap disinkronkan
    When Admin F14 mengonfirmasi permintaan dan koneksi permintaan terputus
    Then browser F14 menampilkan hasil tidak diketahui dan meminta pemeriksaan antrean atau riwayat
    And browser F14 tidak mengirim ulang permintaan secara otomatis

  @BDD_F14_08 @api
  Scenario: Rekonsiliasi manual mencatat hasil unknown tanpa mengarang hasil akhir
    Given Admin API F14 login dan pekerjaan serta run BPS sintetis berstatus running
    When Admin API F14 merekonsiliasi pekerjaan dengan konfirmasi dan alasan valid
    Then pekerjaan dan run F14 berstatus unknown dengan pemeriksa waktu dan alasan tercatat
    And rekonsiliasi F14 tidak mengarang waktu selesai atau hasil sukses maupun gagal

  @BDD_F14_09 @api
  Scenario: Rekonsiliasi tanpa konfirmasi atau alasan valid ditolak
    Given Admin API F14 login dan pekerjaan serta run BPS sintetis berstatus running
    When Admin API F14 mengirim rekonsiliasi tanpa konfirmasi atau dengan alasan tidak valid
    Then server F14 menolak rekonsiliasi dan status pekerjaan serta run tidak berubah

  @BDD_F14_10 @api
  Scenario: Worker lama tidak dapat melanjutkan penulisan setelah rekonsiliasi
    Given Admin API F14 login dan pekerjaan BPS sintetis telah direkonsiliasi menjadi unknown
    When worker lama F14 mencoba menulis metadata atau kandidat melalui jalur BPS yang dipagari
    Then pagar worker F14 menolak penulisan dan tidak membuat kandidat baru
    And hasil F14 tidak mengklaim request jaringan yang telah dikirim sudah dibatalkan

  @BDD_F14_11 @api
  Scenario: Hasil akuisisi tidak otomatis menjadi nilai publik
    Given Admin API F14 login dan tersedia nilai publik terakhir yang sudah direview
    When sinkronisasi F14 menstage kandidat sintetis baru yang belum direview
    Then nilai publik terakhir F14 tetap tersedia dan kandidat baru tidak dipublikasikan

  @BDD_F14_12 @api
  Scenario: Pengunjung anonim tidak dapat meminta sinkronisasi ulang
    Given client anonim F14 dan sumber BPS sintetis aktif
    When pengunjung anonim F14 meminta sinkronisasi ulang
    Then server F14 menolak permintaan tanpa membuat pekerjaan
