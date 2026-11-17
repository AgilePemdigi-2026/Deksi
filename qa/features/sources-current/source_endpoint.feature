@sources_current @api
Feature: Kontrak operasional penyimpanan endpoint tanpa pemeriksaan jaringan
  Ekspektasi lama BDD-F10-05 dan BDD-F11-04 tetap dipertahankan terpisah untuk keputusan requirement.

  @ASBUILT_F10_05
  Scenario: ASBUILT-F10-05 - Endpoint baru disimpan tanpa memanggil jaringan
    Given Admin sumber sintetis siap membuat endpoint tanpa probe
    When Admin menyimpan sumber sintetis dengan endpoint yang belum diverifikasi
    Then sumber dan revisi pertama tersimpan tanpa memanggil probe

  @ASBUILT_F11_04
  Scenario: ASBUILT-F11-04 - Endpoint diubah tanpa memanggil jaringan
    Given Admin sumber sintetis siap mengubah endpoint tanpa probe
    When Admin menyimpan perubahan endpoint yang belum diverifikasi dengan versi revisi
    Then endpoint baru dan revisi kedua tersimpan tanpa memanggil probe
