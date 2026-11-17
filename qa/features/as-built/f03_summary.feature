# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f03
Feature: Ringkasan Indikator Ekonomi

  @BDD_F03_01 @R_F03_01 @browser
  Scenario: BDD-F03-01 - Ringkasan dapat dibaca tanpa Login
    Given observasi PDB uji bernilai desimal 1234.50 dengan unit triliun rupiah dan periode Q1 2025 sudah direview dan dipublikasikan
    When pengunjung anonim membuka dashboard
    Then kartu PDB menampilkan angka ekuivalen 1234.50 beserta unit dan periode yang sama tanpa meminta Login

  @BDD_F03_02 @R_F03_01 @api
  Scenario: BDD-F03-02 - Ringkasan mengikuti identitas pengukuran
    Given observasi terpilih mempunyai source unit frequency dan dataType yang diketahui fixture
    When client meminta ringkasan indikator
    Then nilai serta metadata dan pembanding berasal dari konteks pengukuran fixture yang sebanding

  @BDD_F03_03 @R_F03_02 @browser
  Scenario: BDD-F03-03 - Nol sah tidak disamakan dengan data hilang
    Given satu indikator uji memiliki nilai published nol dan indikator lain tidak memiliki observasi publik
    When pengunjung membuka dashboard
    Then nilai pertama ditampilkan sebagai nol dan indikator kedua sebagai tidak tersedia tanpa angka nol pengganti

  @BDD_F03_04 @R_F03_02 @api
  Scenario: BDD-F03-04 - Pembaruan gagal mempertahankan last-valid
    Given tersedia observasi reviewed-published A dan percobaan pembaruan gagal setelahnya pada fixture log
    When client meminta ringkasan dan status pembaruan tersimpan
    Then nilai tetap berasal dari A dan metadata membedakan percobaan gagal dari waktu sukses terakhir

  @BDD_F03_05 @R_F03_03 @api
  Scenario: BDD-F03-05 - Draft dan published tanpa review tidak bocor
    Given tersedia observasi lama A yang reviewed-published serta draft B dan published C tanpa reviewer yang lebih baru
    When client meminta ringkasan indikator
    Then nilai A dikembalikan dan nilai B serta C tidak dikirim sebagai angka publik

  @BDD_F03_06 @R_F03_03 @browser
  Scenario: BDD-F03-06 - Tanggal sumber bukan waktu halaman dibuka
    Given fixture memiliki periode observasi tanggal rilis dan pembaruan tersimpan yang berbeda
    When pengunjung membuka lalu memuat ulang dashboard
    Then label waktu mempertahankan makna sumbernya dan tidak diganti timestamp pembukaan halaman

  @BDD_F03_07 @R_F03_04 @browser
  Scenario: BDD-F03-07 - Loading tidak memakai angka demo
    Given respons ringkasan ditunda oleh fault harness lokal
    When pengunjung membuka dashboard
    Then loading terlihat sebelum respons diterima dan tidak ada angka fixture desain yang ditampilkan sebagai data tersedia

  @BDD_F03_08 @R_F03_04 @browser
  Scenario: BDD-F03-08 - Error berbeda dari ringkasan kosong
    Given endpoint ringkasan menghasilkan error transport terkontrol lalu pulih pada percobaan berikutnya
    When pengunjung membuka dashboard dan memilih coba lagi setelah error
    Then pesan gagal tampil sebelum retry dan data baru hanya tampil setelah respons sukses tanpa fallback angka buatan
