# Status aktif F7 backend — Batch 2

Tanggal: 2026-11-03. Scope: integrasi implementasi saat ini dan persiapan branch, bukan implementasi lifecycle Batch 1.

## Baseline dan koreksi

- Branch `feat/7-source-trace-be`, checkpoint `a9c6367b7077341a0ae43276463fbd08546a5c28`, parent checkpoint F6 `652ec018ddad455358a9d552593c11b52c4be03b`.
- Perubahan lokal shared tetap milik F6. Delta F7 menambah perluasan fixture/harness untuk exact history, sumber campuran dan periode kosong. Penataan checkpoint final belum diartikan selesai sebelum ancestry dan tree aktual diperiksa.
- FE pasangan: worktree `feature-7-source-trace-fe`, berbasis `94a05cd1fe5044d3d7e0f71ad6d0487edd5f921f` dengan koreksi lokal adapter/tabel/grafik. Backend worktree membawa FE lama; jangan menggunakannya sebagai pengganti pasangan ini.

## Bukti yang dibedakan

- Canonical terakhir yang telah dijalankan sebelum dokumen ini: 42 test backend dieksekusi, 41 PASS dan 1 SKIP symlink Windows; check/drift/scoped lint PASS. Hasil disimpan oleh CLI dan dibaca balik dari ledger root/session yang tepat.
- Integrasi actual FE → Django: 11 kelompok PASS dengan data sintetis di database/RAW scratch, tanpa intersepsi API. Mencakup navigasi, zero/exact values, selektor historis, RAW valid/korup, guard perubahan konteks, sumber campuran, gap Januari–Maret dan responsif. Cleanup database, profil browser serta proses milik task telah dibuktikan.
- Unit FE F6 40, F7 12, editorial 7; build/lint dan browser gabungan 18 kelompok mempunyai receipt terpisah pada source yang sama. Ini tidak dijumlahkan dengan backend atau dipromosikan menjadi eksekusi baru.
- Satu percobaan terdahulu timeout pada koneksi awal Chrome `Runtime.enable`; kegagalan dipertahankan, lalu verifikasi ulang berhasil. Penyebab host yang pasti belum dibuktikan.
- Runtime real-loopback dibuktikan oleh harness; standalone `hermes verify` start/readiness sengaja tidak digunakan. Data resmi dan persetujuan visual bukan hasil test teknis.

## Gate tersisa

[Status fondasi F6](../indicator-detail/CURRENT_STATUS.md) menjelaskan risiko importer/review. Data lama → kandidat → review → data baru BELUM diuji karena staging kandidat belum dibuat. Ini batas wajib laporan, bukan PASS yang boleh diasumsikan dari mutasi fixture lama.

API tidak menjanjikan snapshot immutable atau formula versi; revisi/official verification tetap eksplisit unavailable/unassessed. PostgreSQL/deploy dan akuisisi sumber resmi belum dilakukan. Dashboard existing menghasilkan warning tick-key pada fixture angka ekstrem; tiga lint warning frontend bawaan serta build chunk warning tetap terpisah dari kegagalan test.

`EVALUATION.md` dan `VERIFICATION.json` awal adalah bukti checkpoint historis. `AUDIT_FIXES_VERIFICATION.json` mencatat koreksi audit berikutnya. Artifact canonical dan report Batch 2 pada `.artifacts/` adalah bukti lokal, bukan file produk yang otomatis di-commit.

## Publikasi

Belum push/PR/merge. Commit lokal dan integrasi dependency memerlukan persetujuan checkpoint; lakukan backup/hash overlay terlebih dahulu dan jangan rewrite checkpoint lama. FE companion juga perlu keputusan publikasi terpisah. Jangan menyebut seluruh backend siap produksi selama gate lifecycle di atas belum ditutup.
