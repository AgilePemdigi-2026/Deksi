# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f07
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

  @ASBUILT_F07_03 @R_F07_02 @browser @current_contract
  Scenario: ASBUILT-F07-03 - Keterbatasan klasifikasi dan formula mengikuti API nyata
    Given backend nyata mengirim trace sintetis unclassified tanpa formula input atau revisi immutable
    When browser membuka Source Trace PDB melalui aplikasi asli tanpa Login
    Then nilai periode satuan sumber dan batas klasifikasi formula revisi tampil sesuai kontrak nyata tanpa DTO sukses mock

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

  @ASBUILT_F07_08 @R_F07_04 @browser @acceptance_gap
  Scenario: ASBUILT-F07-08 - Rincian error trace mempertahankan sebab dan tidak memasang provenance pengganti
    Given fixture trace PDB nyata tersedia untuk pembanding kegagalan
    When browser membuka trace kode asing lalu trace PDB dengan transport yang diputus oleh harness
    Then rincian respons membedakan HTTP 404 dan transport gagal sementara provenance kosong serta kontrol coba lagi tetap tersedia
