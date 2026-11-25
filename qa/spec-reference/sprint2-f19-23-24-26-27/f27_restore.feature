@sprint2 @restore @f27
Feature: F27 Kembalikan Konfigurasi ke Default

  @BDD-F27-01 @R_F27_01 @api
  Scenario: BDD-F27-01 - Restore mengembalikan notifikasi dan jadwal yang diubah
    Given Admin telah mengubah preferensi notifikasi dan jadwal sumber sintetis
    When Admin meminta restore domain notifikasi dan jadwal dengan token CSRF valid
    Then nilai kembali ke default dengan audit restore dan teks jadwal sumber ikut pulih

  @BDD-F27-02 @R_F27_02 @api
  Scenario: BDD-F27-02 - Domain threshold dilaporkan dilewati tanpa mengubah data
    Given Admin telah masuk dengan token CSRF valid
    When Admin meminta restore domain threshold
    Then hasil bertanda skipped tanpa baris threshold baru

  @BDD-F27-03 @R_F27_03 @api
  Scenario: BDD-F27-03 - Domain tidak dikenal dan daftar kosong ditolak
    Given Admin telah masuk dengan token CSRF valid
    When Admin meminta restore domain tidak dikenal dan daftar kosong
    Then server menolak dengan status 400

  @BDD-F27-04 @R_F27_04 @api
  Scenario: BDD-F27-04 - Restore dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta restore konfigurasi
    Then server menolak akses restore dengan status 401

  @BDD-F27-05 @R_F27_05 @api
  Scenario: BDD-F27-05 - Restore tanpa daftar domain memulihkan semua default
    Given Admin telah mengubah preferensi notifikasi dan jadwal sumber sintetis
    When Admin meminta restore semua domain dengan token CSRF valid
    Then semua domain kembali ke default dengan pesan pengaturan awal

  @BDD-F27-06 @R_F27_06 @browser
  Scenario: BDD-F27-06 - Admin memulihkan dari dialog konfirmasi [NOT BOUND]
    Given Admin membuka halaman notifikasi dengan konfigurasi berubah
    When Admin mengonfirmasi dialog Kembalikan ke Default
    Then halaman menampilkan hasil per domain tanpa klaim sukses menyeluruh

  @BDD-F27-07 @R_F27_07 @browser
  Scenario: BDD-F27-07 - Kegagalan satu domain tidak menutup hasil domain lain [NOT BOUND]
    Given Admin membuka halaman restore dengan satu domain gagal
    When Admin meminta restore semua domain
    Then hasil menampilkan per domain termasuk yang dilewati
