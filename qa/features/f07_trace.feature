# English Gherkin keywords; Bahasa Indonesia scenario text.
# SPECIFICATION ONLY: no step definitions, no application execution.
@sprint1 @not_run @f07
Feature: Source Trace Data

  @BDD_F07_01 @R_F07_01 @api
  Scenario: BDD-F07-01 - Selector lengkap tidak fallback ke terbaru
    Given observasi publik A dan B tersedia dengan empat selector berbeda dan B lebih baru
    When client meminta Source Trace menggunakan selector lengkap A
    Then nilai sumber dan periode berasal dari A meskipun B lebih baru

  @BDD_F07_02 @R_F07_01 @api
  Scenario: BDD-F07-02 - Selector parsial ditolak
    Given hanya observationDate dari selector A diberikan tanpa frequency dataType dan sourceId
    When client meminta Source Trace
    Then respons berstatus 400 dan tidak mengembalikan trace terbaru sebagai pengganti

  @BDD_F07_03 @R_F07_02 @browser
  Scenario: BDD-F07-03 - Nilai resmi tidak memiliki formula buatan
    Given trace fixture menyatakan nilai official dan tidak menyediakan formula internal
    When pengunjung membuka Source Trace tanpa Login
    Then jenis nilai resmi terlihat dan formula internal tidak dikarang atau diklaim sudah terverifikasi

  @BDD_F07_04 @R_F07_02 @browser @needs_confirmation @Q03
  Scenario: BDD-F07-04 - Provenance belum immutable tidak diklaim versi beku
    Given payload trace memberi immutableSnapshot false revisionId null dan tidak mempunyai input formula turunan lengkap
    When pengunjung membuka Source Trace
    Then UI menyatakan keterlacakan yang belum lengkap dan tidak melabeli observationId sebagai immutable revision

  @BDD_F07_05 @R_F07_03 @browser
  Scenario: BDD-F07-05 - Konten sumber berbahaya tidak dieksekusi
    Given judul publikasi fixture memuat markup uji dan URL sumber memakai skema javascript
    When pengunjung membuka metadata Source Trace
    Then judul tampil sebagai teks tanpa eksekusi skrip dan URL tidak menjadi tautan aktif

  @BDD_F07_06 @R_F07_03 @api
  Scenario: BDD-F07-06 - RAW checksum rusak tidak diunduh
    Given berkas RAW sintetis terkait observasi publik tetapi byte-nya tidak cocok checksum tersimpan
    When client meminta download RAW tersebut
    Then respons menolak pengiriman byte dengan status 503 dan tidak melakukan request URL sumber eksternal

  @BDD_F07_07 @R_F07_04 @browser
  Scenario: BDD-F07-07 - Metadata parsial tetap dapat dibaca
    Given trace uji memiliki institusi dan periode tetapi tanggal rilis serta nama publikasi kosong
    When pengunjung membuka Source Trace
    Then institusi dan periode tetap tampil sedangkan field kosong ditandai belum tersedia bukan nama atau tanggal buatan

  @BDD_F07_08 @R_F07_04 @browser
  Scenario: BDD-F07-08 - Error trace berbeda dari tidak ditemukan
    Given harness menyediakan satu trace tidak ditemukan dan satu request yang gagal transport
    When pengunjung membuka masing-masing konteks
    Then UI membedakan konteks tidak ditemukan dari kegagalan layanan dan tidak menggantinya dengan provenance observasi lain
