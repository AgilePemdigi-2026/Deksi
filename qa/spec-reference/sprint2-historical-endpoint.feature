# Acceptance historis: bukan suite aktif dan belum disetujui sebagai perubahan SRS.
# Aplikasi saat ini menyimpan endpoint tanpa probe. Penggantinya ASBUILT_F10_05 dan ASBUILT_F11_04.
Feature: Acceptance historis keterjangkauan endpoint

  @BDD_F10_05 @R_F10_03 @api
  Scenario: BDD-F10-05 - Endpoint http tak terjangkau ditolak, data lama aman
    Given admin staf sudah login
    And payload tambah sumber api_bps dengan endpoint tak terjangkau
    When client POST ke "/api/admin/sources/create/" dengan payload tambah
    Then respons 400 menyebut endpoint dan sumber tidak tersimpan

  @BDD_F11_04 @R_F11_03 @api
  Scenario: BDD-F11-04 - Endpoint berubah tak terjangkau ditolak, config lama kept
    Given admin staf sudah login
    And sumber "BPS_T" revision 1 sudah ada
    And endpointUrl baru tak terjangkau
    When client PATCH ke "/api/admin/sources/BPS_T/update/" dengan payload ubah
    Then respons 400 menyebut endpoint dan revision tetap 1
