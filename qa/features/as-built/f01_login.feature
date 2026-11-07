# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f01
Feature: Login Admin

  @BDD_F01_01 @R_F01_01 @browser
  Scenario: BDD-F01-01 - Admin aktif berhasil masuk
    Given akun sintetis Admin aktif dengan password uji yang valid dan CSRF bootstrap tersedia
    When Admin mengisi identifier dan password lalu mengirim formulir Login
    Then browser menunjukkan status Admin dan pemeriksaan sesi backend menyatakan authenticated true

  @BDD_F01_02 @R_F01_01 @api
  Scenario: BDD-F01-02 - Akun non-Admin tidak memperoleh sesi Admin
    Given akun sintetis aktif tanpa role staff dan cookie CSRF yang valid
    When client mengirim kredensial akun itu ke endpoint Login
    Then respons berstatus 401 dengan code invalid_credentials dan sesi Admin tidak terbentuk

  @BDD_F01_03 @R_F01_02 @browser
  Scenario: BDD-F01-03 - Password salah tidak memberi keberhasilan palsu
    Given akun Admin sintetis tersedia tetapi password yang dimasukkan salah
    When pengunjung mengirim formulir Login
    Then pesan gagal generik tampil dan halaman tidak menunjukkan sesi Admin berhasil

  @BDD_F01_04 @R_F01_02 @api
  Scenario: BDD-F01-04 - Lockout mengikuti kebijakan kandidat
    Given akun uji dan IP uji terisolasi dengan lima kegagalan Login pada jendela limiter aktif
    When client mencoba Login lagi sebelum cooloff berakhir
    Then respons berstatus 429 dengan code rate_limited tanpa membuat sesi Admin

  @BDD_F01_05 @R_F01_03 @api
  Scenario: BDD-F01-05 - Sesi kedaluwarsa tidak tetap terautentikasi
    Given sesi Admin sintetis sudah melewati expiry absolut delapan jam memakai jam uji terkontrol
    When client meminta status sesi
    Then respons menyatakan authenticated false dan user null tanpa memperpanjang sesi

  @BDD_F01_06 @R_F01_03 @browser
  Scenario: BDD-F01-06 - Logout membatalkan sesi server
    Given Admin uji sudah Login dan token CSRF terbaru tersedia
    When Admin memilih Keluar lalu halaman dimuat ulang
    Then status browser menjadi anonim dan cookie sesi lama tidak dapat mengautentikasi request server berikutnya

  @BDD_F01_07 @R_F01_04 @api
  Scenario: BDD-F01-07 - Login tanpa CSRF ditolak
    Given client anonim belum mempunyai pasangan cookie dan header CSRF yang valid
    When client mengirim POST Login dengan kredensial uji valid
    Then server merespons 403 dan tidak membentuk sesi Admin

  @BDD_F01_08 @R_F01_04 @browser
  Scenario: BDD-F01-08 - Gangguan Login bukan kredensial salah atau sukses
    Given request Login di lingkungan uji dihentikan dengan kegagalan transport terkontrol
    When Admin mengirim formulir Login
    Then pesan layanan tidak tersedia tampil dan tidak ada status sukses atau pengiriman ulang otomatis
