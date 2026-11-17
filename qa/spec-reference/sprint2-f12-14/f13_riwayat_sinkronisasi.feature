# Rancangan saja: seluruh skenario NOT RUN, belum ada binding/runner.
@draft @not_run @sprint2 @f13
Feature: F13 Riwayat sinkronisasi sumber data
  Agar Admin dapat melihat hasil akuisisi tanpa mengira log lain sebagai sinkronisasi

  @BDD_F13_01 @browser
  Scenario: Riwayat menampilkan run sintetis terbaru
    Given Admin masuk dan ada dua run sintetis dengan waktu mulai berbeda
    When Admin membuka halaman riwayat sinkronisasi
    Then run ditampilkan dari yang terbaru beserta sumber status dan waktu mulai
    And waktu selesai dan jumlah hanya ditampilkan jika memang tersedia

  @BDD_F13_02 @browser
  Scenario: Filter sumber dan status membatasi hasil
    Given riwayat sintetis berisi beberapa sumber dan status
    When Admin memilih satu sumber dan satu status
    Then hanya run yang cocok dengan kedua filter yang tampil

  @BDD_F13_03 @api
  Scenario: Halaman berikutnya berisi run berikutnya tanpa duplikasi
    Given jumlah run sintetis lebih besar daripada ukuran satu halaman
    When Admin membaca halaman pertama lalu halaman kedua dengan filter yang sama
    Then masing-masing halaman mengikuti urutan waktu mulai terbaru
    And ID run yang sama tidak muncul di kedua halaman untuk dataset yang tidak berubah

  @BDD_F13_04 @browser
  Scenario: Riwayat kosong tidak dianggap gagal
    Given Admin masuk dan tidak ada run yang cocok dengan filter
    When Admin membuka riwayat dengan filter tersebut
    Then halaman menampilkan kondisi kosong tanpa menciptakan run atau angka

  @BDD_F13_05 @browser
  Scenario: Gagal mengambil riwayat tidak digambarkan sebagai kosong
    Given Admin masuk dan permintaan riwayat menghasilkan kegagalan server sintetis
    When Admin membuka riwayat
    Then halaman menampilkan kesalahan dan menyediakan cara mencoba lagi
    And tidak menampilkan data contoh sebagai riwayat nyata

  @BDD_F13_06 @api
  Scenario: Riwayat ditolak untuk pengunjung anonim
    Given pengunjung tidak memiliki sesi Admin
    When pengunjung meminta riwayat sinkronisasi
    Then server menolak akses tanpa memberikan daftar run

  @BDD_F13_07 @api
  Scenario: Parameter filter tidak valid ditolak
    Given Admin masuk
    When Admin meminta riwayat dengan status atau nomor halaman yang tidak valid
    Then server menolak parameter tanpa mengubah run

  @BDD_F13_08 @api
  Scenario: Log historis ambigu tidak disajikan sebagai run sinkronisasi
    Given terdapat log lama sintetis yang jenis peristiwanya tidak dapat dipastikan
    And tidak ada run sinkronisasi terkait
    When Admin meminta riwayat sinkronisasi
    Then log ambigu tidak disajikan sebagai run atau keberhasilan sinkronisasi

  @BDD_F13_09 @browser
  Scenario: Admin kembali dari riwayat ke pengelolaan sumber
    Given Admin berada pada halaman riwayat sinkronisasi
    When Admin memilih tautan Kelola Sumber Data
    Then halaman Kelola Sumber terbuka dengan sesi Admin yang sama
