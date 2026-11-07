# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f02
Feature: Lupa dan Reset Password

  @BDD_F02_01 @R_F02_01 @api
  Scenario: BDD-F02-01 - Email dikenal dan tidak dikenal mendapat acknowledgement generik
    Given mailer locmem dan akun Admin sintetis unik tersedia pada settings uji
    When client mengirim permintaan reset untuk email akun lalu email sintetis yang tidak dikenal dengan CSRF valid
    Then kedua respons berstatus 202 dengan reset_request_accepted tanpa mengungkap keberadaan akun

  @BDD_F02_02 @R_F02_01 @browser
  Scenario: BDD-F02-02 - Form meminta koreksi email malformed
    Given halaman Lupa Password dibuka dan alamat email tidak valid diisikan
    When pengunjung mengirim formulir
    Then pesan validasi tampil pada field email dan tidak ada request reset yang dikirim

  @BDD_F02_03 @R_F02_02 @api
  Scenario: BDD-F02-03 - Token kedaluwarsa dan token terpakai ditolak
    Given tersedia token reset yang sudah lewat timeout kandidat dan token lain yang telah dipakai sukses
    When client mengonfirmasi reset menggunakan masing-masing token
    Then kedua request ditolak sebagai invalid_reset_link dan hash password tidak berubah

  @BDD_F02_04 @R_F02_02 @browser
  Scenario: BDD-F02-04 - Password konfirmasi tidak cocok
    Given tautan reset uji valid dan dua field password berisi nilai berbeda
    When pengunjung mengirim password baru
    Then pesan ketidakcocokan terlihat dan tidak ada konfirmasi reset sukses

  @BDD_F02_05 @R_F02_03 @browser
  Scenario: BDD-F02-05 - Reset lengkap melalui email locmem
    Given Admin uji mempunyai sesi lama dan reset diaktifkan hanya pada settings uji dengan mailer locmem
    When Admin meminta reset dan menggunakan tautan yang ditangkap harness locmem untuk menetapkan password baru yang valid
    Then password baru diterima tanpa auto-login serta Login lama gagal dan sesi lama ditolak pada request berikutnya

  @BDD_F02_06 @R_F02_03 @api
  Scenario: BDD-F02-06 - Password tidak memenuhi policy tidak mengubah akun
    Given token valid dan password baru yang ditolak validator kandidat tersedia
    When client mengonfirmasi reset dengan CSRF valid
    Then respons berstatus 400 dengan password_validation_failed dan password lama tetap berlaku

  @BDD_F02_07 @R_F02_04 @api
  Scenario: BDD-F02-07 - Reset default disabled tidak mengirim email
    Given reset disabled pada konfigurasi yang dipilih untuk skenario uji
    When client mengirim permintaan reset dengan payload dan CSRF valid
    Then respons berstatus 503 dengan reset_unavailable dan outbox locmem tidak bertambah

  @BDD_F02_08 @R_F02_04 @browser
  Scenario: BDD-F02-08 - Hasil confirm tidak pasti tidak diulang otomatis
    Given halaman password baru memiliki token uji dan request confirm menghasilkan 503 terkontrol
    When pengunjung mengirim formulir sekali
    Then UI tidak mengklaim password berubah dan tidak otomatis mengulang request berisi password
