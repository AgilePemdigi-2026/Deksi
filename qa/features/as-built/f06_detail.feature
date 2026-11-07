# English Gherkin keywords; Bahasa Indonesia scenario text.
# AS-BUILT v2: pinned real application; requirement gaps remain in baseline suite.
@sprint1 @as_built @f06
Feature: Detail Indikator Ekonomi

  @BDD_F06_01 @R_F06_01 @browser
  Scenario: BDD-F06-01 - Detail langsung dan dari kartu konsisten
    Given observasi PDB uji reviewed-published tersedia dan pengunjung anonim
    When pengunjung membuka detail dari kartu lalu membuka URL detail yang sama secara langsung
    Then kedua jalur menampilkan indikator serta konteks observasi yang sama tanpa Login

  @ASBUILT_F06_02 @R_F06_01 @browser @acceptance_gap
  Scenario: ASBUILT-F06-02 - Kode asing tetap anonim dan tidak memperoleh angka PDB
    Given fixture publik PDB nyata pada database disposable dan kode asing unknown_bdd
    When browser membuka detail unknown_bdd dan rincian ketersediaan API
    Then kode asing dan nilai tidak tersedia tampil dengan rincian HTTP 404 tanpa angka PDB atau permintaan Login

  @BDD_F06_03 @R_F06_02 @browser
  Scenario: BDD-F06-03 - Perubahan poin persentase tidak menjadi persen relatif
    Given payload fixture memberi nilai perubahan 0.50 dengan changeUnit percentage_point serta periode pembanding Q1 2024
    When pengunjung membuka detail indikator
    Then UI menampilkan 0.50 poin persentase dan periode pembanding Q1 2024 tanpa menghitung persen relatif sendiri

  @BDD_F06_04 @R_F06_02 @browser
  Scenario: BDD-F06-04 - Tanpa fakta kausal tidak ada narasi sebab akibat
    Given payload detail hanya berisi angka dan tren tanpa interpretasi kausal atau formula turunan
    When pengunjung membuka detail
    Then UI tidak mengarang penyebab perubahan formula atau kontribusi sektor dan tidak memanggil provider AI

  @BDD_F06_05 @R_F06_03 @browser
  Scenario: BDD-F06-05 - Metadata rilis yang hilang tetap hilang
    Given nilai uji tersedia tetapi publicationDate null dan tanggal akuisisi berbeda dari periode observasi
    When pengunjung membuka detail
    Then nilai tetap tampil dan rilis ditandai belum tersedia tanpa memakai waktu akuisisi sebagai tanggal rilis

  @BDD_F06_06 @R_F06_03 @browser
  Scenario: BDD-F06-06 - Grafik detail mempunyai alternatif dan gap
    Given histori uji mempunyai gap kalender dan nilai exact desimal yang diketahui
    When pengunjung membuka detail dan alternatif tabel histori
    Then tabel mempertahankan nilai exact serta gap tidak diisi nol dan akses nilai tidak hanya melalui warna atau tooltip

  @BDD_F06_07 @R_F06_04 @browser
  Scenario: BDD-F06-07 - Detail meneruskan selector observasi ke trace
    Given detail sedang menampilkan observasi A dengan observationDate frequency dataType dan sourceId fixture
    When pengunjung memilih Source Trace
    Then keempat selector diteruskan dan halaman trace tetap merujuk observasi A bukan observasi terbaru lain

  @BDD_F06_08 @R_F06_04 @browser
  Scenario: BDD-F06-08 - Pergantian detail tidak dicemari respons lama
    Given pemuatan detail A ditunda dan detail B berhasil lebih dahulu
    When pengunjung berpindah dari A ke B lalu respons A selesai
    Then nama nilai grafik dan tautan trace tetap milik B tanpa campuran konteks
