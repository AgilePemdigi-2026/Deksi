# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f08
Feature: Kirim Umpan Balik

  @BDD_F08_01 @R_F08_01 @browser
  Scenario: BDD-F08-01 - Feedback anonim berhasil dikirim
    Given pengunjung tanpa sesi mempunyai kategori valid dan deskripsi sintetis yang memenuhi batas kandidat
    When pengunjung mengirim form setelah bootstrap CSRF
    Then server mengembalikan 201 dengan status pending dan UI menampilkan konfirmasi setelah row tersimpan

  @BDD_F08_02 @R_F08_01 @api
  Scenario: BDD-F08-02 - Publik tidak dapat menentukan status Admin
    Given payload feedback valid menyertakan status resolved dan admin_notes dari pengirim anonim
    When client mengirim feedback dengan CSRF valid
    Then record tersimpan pending dengan admin_notes kosong dan respons tidak mengungkap catatan Admin

  @BDD_F08_03 @R_F08_02 @api
  Scenario: BDD-F08-03 - Batas panjang deskripsi kandidat
    Given fixture request memakai kategori valid dengan deskripsi setelah trim sepanjang 9 lalu 10 lalu 2000 lalu 2001 karakter
    When client mengirim keempat request secara terpisah dengan CSRF valid
    Then panjang 9 dan 2001 ditolak 400 tanpa row baru sedangkan 10 dan 2000 diterima 201

  @BDD_F08_04 @R_F08_02 @browser
  Scenario: BDD-F08-04 - Identitas opsional tidak menjadi kewajiban akun
    Given pengunjung membuka form dengan kategori valid dan deskripsi lengkap tanpa nama dan email
    When pengunjung mengirim formulir
    Then feedback diterima tanpa registrasi Login atau kewajiban mengisi identitas opsional

  @BDD_F08_05 @R_F08_03 @api
  Scenario: BDD-F08-05 - Feedback tanpa CSRF tidak tersimpan
    Given payload feedback valid dikirim tanpa pasangan cookie dan header CSRF
    When client melakukan POST feedback
    Then respons berstatus 403 dan jumlah record feedback tidak bertambah

  @BDD_F08_06 @R_F08_03 @api
  Scenario: BDD-F08-06 - Payload malformed tidak tersimpan
    Given request feedback memakai JSON dengan key duplikat atau field description bertipe array
    When client mengirim masing-masing payload dengan CSRF valid
    Then respons berstatus 400 tanpa record baru dan tanpa exception internal yang bocor

  @BDD_F08_07 @R_F08_04 @browser
  Scenario: BDD-F08-07 - Kegagalan simpan tidak memberi konfirmasi sukses
    Given penyimpanan feedback dipaksa gagal pada lingkungan uji sebelum commit database
    When pengunjung mengirim satu feedback valid
    Then UI menampilkan kegagalan tanpa konfirmasi tersimpan dan tidak otomatis mengirim ulang

  @BDD_F08_08 @R_F08_04 @api @needs_confirmation @Q04
  Scenario: BDD-F08-08 - Konteks advisory bukan binding revisi
    Given payload valid menyertakan related_indicator_code dan related_period sintetis
    When client mengirim feedback
    Then kedua field dipertahankan sebagai konteks advisory dan tidak diklaim mengikat immutable revision analisis
