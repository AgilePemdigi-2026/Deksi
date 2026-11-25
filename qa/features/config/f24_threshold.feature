@sprint2 @thresholds @f24
Feature: F24 Konfigurasi Threshold Diagnostik

  @BDD-F24-01 @R_F24_01 @api
  Scenario: BDD-F24-01 - Daftar threshold menampilkan default registry
    Given Admin telah masuk tanpa konfigurasi threshold
    When Admin meminta daftar threshold
    Then daftar memuat parameter registry dengan nilai default dan status aktif

  @BDD-F24-02 @R_F24_02 @api
  Scenario: BDD-F24-02 - Pembaruan threshold valid tersimpan berversi dan diaudit
    Given Admin memiliki indikator sintetis pdb dan token CSRF valid
    When Admin menyimpan threshold pdb dalam rentang dengan alasan
    Then threshold tersimpan berversi dengan audit dan evaluasi diagnostik

  @BDD-F24-03 @R_F24_03 @api
  Scenario: BDD-F24-03 - Nilai di luar rentang dan satuan salah ditolak
    Given Admin memiliki indikator sintetis pdb dan token CSRF valid
    When Admin menyimpan threshold pdb di luar rentang dan satuan salah
    Then server menolak dengan status 400 dan tidak ada baris threshold baru

  @BDD-F24-04 @R_F24_04 @api
  Scenario: BDD-F24-04 - Indikator dan parameter tidak dikenal mengembalikan 404
    Given Admin telah masuk dengan token CSRF valid
    When Admin meminta detail threshold untuk indikator dan parameter tidak dikenal
    Then server menolak dengan status 404

  @BDD-F24-05 @R_F24_05 @api
  Scenario: BDD-F24-05 - Detail indikator tanpa baris database mengembalikan 404
    Given Admin telah masuk dengan token CSRF valid
    When Admin menyimpan threshold untuk kode registry tanpa baris indikator
    Then server menolak dengan status 404 tanpa audit baru

  @BDD-F24-06 @R_F24_06 @api
  Scenario: BDD-F24-06 - Riwayat menampilkan jejak perubahan threshold
    Given Admin memiliki threshold pdb yang sudah diubah satu kali
    When Admin meminta riwayat threshold tersebut
    Then riwayat memuat satu entri dengan nilai lama dan baru

  @BDD-F24-07 @R_F24_07 @api
  Scenario: BDD-F24-07 - Evaluasi diagnostik memakai ambang aktif dan observasi terbaru
    Given Admin memiliki indikator sintetis pdb dengan observasi terpublikasi
    When Admin meminta evaluasi diagnostik pdb
    Then evaluasi memuat status terhadap ambang dan periode observasi

  @BDD-F24-08 @R_F24_08 @api
  Scenario: BDD-F24-08 - Threshold dilindungi untuk Admin
    Given pengunjung anonim belum memiliki sesi Admin
    When pengunjung meminta daftar threshold
    Then server menolak akses threshold dengan status 401

  @BDD-F24-09 @R_F24_09 @api
  Scenario: BDD-F24-09 - Pengguna tanpa hak staf tidak dapat menyimpan threshold
    Given pengguna masuk tanpa hak staf pengelola
    When pengguna menyimpan threshold pdb yang valid
    Then server menolak dengan status 403 dan tidak ada baris threshold baru

  @BDD-F24-10 @R_F24_10 @api
  Scenario: BDD-F24-10 - Formula inti terkunci lewat parameter tak terdaftar
    Given Admin memiliki indikator sintetis pdb dan token CSRF valid
    When Admin menyimpan parameter formula inti yang tak terdaftar
    Then server menolak dengan status 404 tanpa audit baru

