# English Gherkin keywords; Bahasa Indonesia scenario text.
# SPECIFICATION ONLY: no step definitions, no application execution.
@sprint1 @not_run @f05
Feature: Filter Dashboard Ekonomi

  @BDD_F05_01 @R_F05_01 @api
  Scenario: BDD-F05-01 - Filter tahun memilih observasi pada tahun itu
    Given fixture inflasi memiliki nilai 2.50 tahun 2024 dan 3.00 tahun 2025 dengan review publik lengkap
    When client meminta dashboard kategori Inflasi untuk tahun 2024
    Then kartu menampilkan 2.50 dengan metadata tahun 2024 dan activeFilters year 2024

  @BDD_F05_02 @R_F05_01 @browser
  Scenario: BDD-F05-02 - Ringkasan dan histori mengikuti filter
    Given fixture mempunyai observasi beberapa kategori pada tahun 2024 dan 2025
    When pengunjung memilih kategori Inflasi dan tahun 2024
    Then kartu kategori lain tidak ditampilkan dan rentang histori yang terlihat tidak memasukkan titik 2025

  @BDD_F05_03 @R_F05_02 @api
  Scenario: BDD-F05-03 - Tahun kosong tidak fallback ke terbaru
    Given indikator uji hanya memiliki observasi reviewed-published tahun 2025
    When client meminta dashboard tahun 2024
    Then kartu menyatakan available false dan value null bukan angka dari tahun 2025

  @BDD_F05_04 @R_F05_02 @browser
  Scenario: BDD-F05-04 - Rentang kosong tetap memperlihatkan filter aktif
    Given kategori dan tahun yang sah tidak mempunyai observasi uji
    When pengunjung menerapkan filter tersebut
    Then empty state serta pilihan filter tetap terlihat dan tidak diganti angka terbaru global

  @BDD_F05_05 @R_F05_03 @api
  Scenario: BDD-F05-05 - Tahun di luar domain ditolak
    Given client menggunakan parameter year bernilai 0 lalu 10000 pada request yang terpisah
    When client meminta dashboard untuk setiap nilai tersebut
    Then setiap respons berstatus 400 tanpa error internal dan tanpa data tahun alternatif

  @BDD_F05_06 @R_F05_03 @api
  Scenario: BDD-F05-06 - Parameter berulang dan kategori asing ditolak
    Given tersedia request kategori tidak dikenal serta request dengan dua parameter year
    When client mengirim masing-masing request filter
    Then setiap respons berstatus 400 dan tidak diam-diam memilih nilai parameter terakhir

  @BDD_F05_07 @R_F05_04 @browser
  Scenario: BDD-F05-07 - Reset filter kembali ke konteks terbaru
    Given dashboard sedang memakai filter kategori dan tahun historis yang sah
    When pengunjung memilih reset filter
    Then kontrol kembali ke tanpa filter dan kartu diambil dari konteks terbaru tanpa label tahun historis yang tertinggal

  @BDD_F05_08 @R_F05_04 @browser
  Scenario: BDD-F05-08 - Request filter lama tidak menimpa pilihan aktif
    Given request filter tahun 2024 ditunda sementara request tahun 2025 dapat selesai
    When pengunjung mengganti tahun 2024 menjadi 2025 lalu respons lama dilepas
    Then nilai periode dan label filter tetap konsisten tahun 2025
