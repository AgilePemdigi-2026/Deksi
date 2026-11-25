@sprint2 @ai-policy @f25
Feature: F25 Konfigurasi Kebijakan Grounded AI

  # STATUS: DRAFT / NOT BOUND. Tidak ada model endpoint atau halaman kebijakan
  # Grounded AI di codebase. Seluruh skenario di bawah adalah rancangan menunggu
  # implementasi; JANGAN di-binding sampai registry kebijakan disepakati.

  @BDD-F25-01 @R_F25_01 @api
  Scenario: BDD-F25-01 - Daftar kebijakan menampilkan guardrails aktif [NOT BOUND]
    Given Admin telah masuk
    When Admin meminta daftar kebijakan Grounded AI
    Then daftar memuat guardrail fakta tervalidasi tanpa ubah nilai dan wajib Source Trace

  @BDD-F25-02 @R_F25_02 @api
  Scenario: BDD-F25-02 - Perubahan kebijakan tervalidasi dan beraudit [NOT BOUND]
    Given Admin telah masuk dengan token CSRF valid
    When Admin menyimpan perubahan kebijakan dalam guardrails
    Then kebijakan tersimpan berversi dengan audit dan konfirmasi

  @BDD-F25-03 @R_F25_03 @api
  Scenario: BDD-F25-03 - Nilai di luar guardrails ditolak dan konfigurasi lama utuh [NOT BOUND]
    Given Admin telah masuk dengan token CSRF valid
    When Admin menyimpan kebijakan yang melanggar guardrails
    Then server menolak dengan status 400 dan tidak ada versi baru

  @BDD-F25-04 @R_F25_04 @api
  Scenario: BDD-F25-04 - Formula inti tidak dapat diubah lewat kebijakan [NOT BOUND]
    Given Admin telah masuk dengan token CSRF valid
    When Admin mencoba mengubah formula inti Economic Engine
    Then server menolak dan formula tetap utuh

  @BDD-F25-05 @R_F25_05 @api
  Scenario: BDD-F25-05 - Kebijakan dilindungi hak konfigurasi [NOT BOUND]
    Given pengunjung anonim dan pengguna tanpa hak konfigurasi
    When mereka meminta atau menyimpan kebijakan
    Then server menolak akses tanpa hak

  @BDD-F25-06 @R_F25_06 @browser
  Scenario: BDD-F25-06 - Pembatalan sebelum simpan tidak mengubah apa pun [NOT BOUND]
    Given Admin mengubah kebijakan tanpa menyimpan
    When Admin membatalkan
    Then kebijakan tampil tetap pada nilai terakhir tersimpan
