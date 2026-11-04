@regression @browser @REG_EMPTY_YEAR_DETAIL
Feature: Gap konteks filter kosong ke Detail

  Scenario: REG-EMPTY-YEAR-DETAIL - Tahun tanpa observasi tidak diam-diam membuka nilai terbaru
    Given fixture PDB hanya memiliki observasi publik tahun 2025 dan browser terisolasi tersedia
    When pengunjung memilih tahun 2024 tanpa data lalu menekan Detail PDB
    Then navigasi mempertahankan konteks kosong atau memberi penolakan eksplisit tanpa menampilkan nilai terbaru tahun 2025
