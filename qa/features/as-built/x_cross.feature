# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @x
Feature: Lintas Fitur Sprint 1

  @BDD_X_01 @R_X_01 @browser
  Scenario: BDD-X-01 - Dashboard publik sebelum dan sesudah Login
    Given fixture indikator publik tersedia dan akun Admin uji mempunyai hak terbatas
    When pengunjung membuka dashboard lalu Login dan Logout sebelum membuka detail serta trace lagi
    Then data publik tetap tersedia tanpa sesi dan Logout tidak membuat navigasi publik meminta Login

  @BDD_X_02 @R_X_01 @api
  Scenario: BDD-X-02 - Pencabutan role Admin ditegakkan
    Given sesi Admin uji terbentuk lalu flag staff dicabut pada fixture
    When client meminta status sesi dan mencoba operasi Admin yang memerlukan izin
    Then sesi tidak memberi hak Admin lagi dan data publik tetap dapat diakses anonim

  @BDD_X_03 @R_X_02 @browser @needs_confirmation @Q02
  Scenario: BDD-X-03 - Ringkasan detail trace membawa identitas yang sama
    Given dashboard difilter tahun historis dengan satu observasi A yang memiliki selector lengkap
    When pengunjung membuka kartu ke detail lalu Source Trace dan kembali
    Then nilai periode satuan dan sumber tetap merujuk A sepanjang navigasi

  @BDD_X_04 @R_X_02 @browser
  Scenario: BDD-X-04 - Feedback setelah Login memakai CSRF yang berlaku
    Given browser telah memperoleh token feedback sebelum Login lalu sesi Login merotasi CSRF
    When pengguna mengirim feedback setelah Login melalui alur client yang memperbarui bootstrap
    Then request memakai token yang berlaku dan row pending tersimpan tanpa mematikan middleware CSRF

  @BDD_X_05 @R_X_03 @browser
  Scenario: BDD-X-05 - Alur utama dapat dioperasikan keyboard
    Given halaman Login dashboard filter detail trace dan feedback tersedia pada fixture uji
    When pengguna memakai Tab Shift Tab Enter dan Escape pada kontrol serta dialog yang tersedia
    Then fokus terlihat urutannya logis label terbaca dan penutupan dialog mengembalikan fokus ke pemicunya

  @BDD_X_06 @R_X_03 @browser
  Scenario: BDD-X-06 - Konten penting tetap terbaca pada viewport kecil
    Given fixture memuat nama indikator panjang dan angka exact pada seluruh halaman Sprint 1
    When browser memakai viewport uji 390 dan 1280 CSS pixel
    Then kontrol dan nilai penting tidak terpotong oleh overflow horizontal halaman dan fungsi tidak bergantung pada hover saja

  @BDD_X_07 @R_X_04 @api
  Scenario: BDD-X-07 - Tes tidak memakai database atau provider kerja
    Given harness uji mendeklarasikan database disposable mailer locmem serta larangan jaringan nonloopback
    When suite menginisialisasi fixture skenario dan membersihkan sesudah skenario
    Then database kerja dan env pengguna tidak dibaca serta tidak ada email eksternal ingestion atau provider AI dijalankan

  @BDD_X_08 @R_X_04 @browser
  Scenario: BDD-X-08 - Input sensitif tidak masuk URL atau storage
    Given browser memakai kredensial dan token reset sintetis dengan marker yang diketahui harness
    When pengguna menjalani Login dan reset lalu memuat ulang halaman
    Then password tidak ada di URL atau browser storage dan token reset tidak tertinggal di URL setelah dikonsumsi UI tanpa mencetak nilainya ke laporan
