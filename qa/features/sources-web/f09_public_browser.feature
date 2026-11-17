@sources_web @browser
Feature: Katalog sumber publik menggunakan data API sebenarnya
  @ASBUILT_F09_WEB_01
  Scenario: ASBUILT-F09-WEB-01 - Pengunjung melihat detail sumber sintetis
    Given browser katalog sumber menggunakan data sintetis yang direview
    When pengunjung membuka katalog dan detail sumber sintetis
    Then browser menampilkan identitas dan indikator sumber yang sesuai respons Django
