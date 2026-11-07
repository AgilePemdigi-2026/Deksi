# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f04
Feature: Grafik Tren Ekonomi

  @BDD_F04_01 @R_F04_01 @api
  Scenario: BDD-F04-01 - Histori mengirim desimal exact
    Given seri uji memiliki exactValue 123456789012345.6789 dan metadata sumber unit tanggal frequency serta dataType
    When client meminta histori native indikator
    Then payload mempertahankan exactValue dan metadata tersebut tanpa mengandalkan angka koordinat aproksimasi sebagai nilai exact

  @BDD_F04_02 @R_F04_01 @browser
  Scenario: BDD-F04-02 - Seri tidak sebanding tidak disambung
    Given histori uji memuat titik dari dua sumber atau satuan yang tidak sebanding
    When pengunjung membuka grafik
    Then UI memisahkan atau menolak garis gabungan dan tetap menyediakan nilai tabel dengan identitas sumber serta satuan

  @BDD_F04_03 @R_F04_02 @api
  Scenario: BDD-F04-03 - Agregasi deterministik sesuai oracle
    Given fixture komparabel mempunyai dua nilai 10 dan 20 pada tahun yang sama dengan aggregation_kind sum
    When client meminta histori Tahunan
    Then nilai exact agregasi adalah 30 dan metode dijelaskan sebagai jumlah tanpa pemanggilan AI

  @BDD_F04_04 @R_F04_02 @browser
  Scenario: BDD-F04-04 - Pilihan frekuensi mengikuti backend
    Given backend uji hanya mengizinkan Kuartalan dan Tahunan untuk indikator PDB
    When pengunjung membuka pilihan granularitas grafik
    Then kontrol tidak menawarkan Bulanan sebagai mode yang didukung untuk indikator tersebut

  @BDD_F04_05 @R_F04_03 @browser
  Scenario: BDD-F04-05 - Gap kalender tidak menjadi observasi nol
    Given seri bulanan uji memiliki Januari dan Maret tetapi tidak memiliki Februari
    When pengunjung membuka grafik dan alternatif tabel
    Then garis tidak menyiratkan observasi Februari tersedia dan tabel tidak menambahkan nilai nol atau interpolasi buatan

  @BDD_F04_06 @R_F04_03 @browser
  Scenario: BDD-F04-06 - Histori kosong memberi empty state
    Given indikator terdefinisi tetapi tidak mempunyai histori reviewed-published
    When pengunjung memilih indikator pada grafik
    Then pesan histori belum tersedia tampil tanpa garis atau titik angka buatan

  @BDD_F04_07 @R_F04_04 @browser
  Scenario: BDD-F04-07 - Respons indikator lama tidak mengganti pilihan baru
    Given request grafik indikator A ditunda dan request indikator B dapat selesai lebih dahulu
    When pengunjung cepat mengganti pilihan dari A ke B lalu respons A dilepas harness
    Then judul unit dan seri tetap milik B setelah kedua request selesai

  @BDD_F04_08 @R_F04_04 @browser
  Scenario: BDD-F04-08 - Grafik gagal memberi error dan retry
    Given endpoint histori mengalami kegagalan terkontrol sementara ringkasan tetap sukses
    When pengunjung membuka dashboard lalu mencoba ulang grafik setelah layanan pulih
    Then ringkasan tidak hilang dan grafik hanya menampilkan hasil baru setelah retry sukses
