@sprint2 @monitoring @f19
Feature: F19 Dashboard Monitoring Admin

  @BDD-F19-01 @R_F19_01 @api
  Scenario: BDD-F19-01 - Ringkasan menghitung sumber dan status sinkronisasi
    Given Admin memiliki dua sumber sintetis aktif dan nonaktif dengan riwayat sinkronisasi sukses gagal dan berjalan
    When Admin meminta ringkasan monitoring
    Then ringkasan memuat hitungan sumber dan status sinkronisasi serta label kualitas

  @BDD-F19-02 @R_F19_02 @api
  Scenario: BDD-F19-02 - Daftar sumber memuat status sinkronisasi dan observasi terakhir
    Given Admin memiliki sumber sintetis dengan satu observasi terpublikasi dan satu riwayat sukses
    When Admin meminta daftar sumber monitoring
    Then daftar memuat status sinkronisasi terakhir dan hitungan observasi sumber tersebut

  @BDD-F19-03 @R_F19_03 @api
  Scenario: BDD-F19-03 - Riwayat mendukung pagination dan filter status
    Given Admin memiliki dua riwayat sinkronisasi dengan status berbeda
    When Admin meminta halaman riwayat dengan filter status gagal
    Then halaman hanya memuat riwayat gagal dengan total yang benar

  @BDD-F19-04 @R_F19_04 @api
  Scenario: BDD-F19-04 - Detail riwayat menampilkan durasi dan pesan aman
    Given Admin memiliki satu riwayat sinkronisasi selesai dengan pesan aman
    When Admin meminta detail riwayat tersebut
    Then detail memuat durasi hitung dan pesan aman tanpa data sensitif

  @BDD-F19-05 @R_F19_05 @api
  Scenario: BDD-F19-05 - Detail riwayat tidak dikenal mengembalikan 404
    Given Admin telah masuk tanpa riwayat sinkronisasi
    When Admin meminta detail riwayat yang tidak ada
    Then server menolak dengan status 404

  @BDD-F19-06 @R_F19_06 @api
  Scenario: BDD-F19-06 - Monitoring dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta ringkasan monitoring
    Then server menolak akses monitoring dengan status 401

  @BDD-F19-07 @R_F19_07 @browser
  Scenario: BDD-F19-07 - Admin melihat kartu ringkasan dan tabel sumber [NOT BOUND]
    Given Admin membuka halaman monitoring dengan data sintetis
    When halaman selesai dimuat
    Then kartu ringkasan dan tabel sumber tampil tanpa angka contoh
