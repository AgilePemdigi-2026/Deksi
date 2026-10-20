<?php

/*
|--------------------------------------------------------------------------
| Konfigurasi DEKSI (Deteksi Ekonomi Indonesia)
|--------------------------------------------------------------------------
| Data global dashboard publik. Deret nilai indikator ada di
| resources/data/indicators.json yang dibaca App\Support\IndicatorRepository.
*/

return [
    'nama' => 'DEKSI',
    'nama_panjang' => 'Deteksi Ekonomi Indonesia',
    'badge' => 'Platform Data & Analisis',

    'status_pembaruan' => [
        'terakhir_diperbarui' => '15 Okt 2024, 09:00 WIB',
        'periode_analisis' => 'Q2 2024 / Semester II',
        'sumber_terverifikasi' => ['BPS', 'BI', 'KEMENKEU', 'BKPM'],
    ],

    'tautan' => [
        // Placeholder: halaman milik anggota lain / fitur lain (Sprint 1).
        'masuk' => '#',
        'detail_indikator' => '#',
        'source_trace' => '#',
        'panel_analisis' => '#',
        'sinkronisasi_api' => '#',
    ],
];
