# BDD Sprint 1 — hasil as-built v2, 7 November 2026

**BDD sudah disesuaikan dengan fitur dan dashboard React–Django aktual, lalu dijalankan penuh.**

| Cakupan | PASS | FAIL | SKIPPED / undefined |
|---|---:|---:|---:|
| 72 skenario as-built v2 | 71 | 1 | 0 |
| Ditambah regresi: 73 skenario | 71 | 2 | 0 |
| Seluruh 219 langkah | 217 | 2 | 0 |

Run: `qa/artifacts/20261107-131142-as-built-final/`. Exit runner **1** karena dua temuan dipertahankan. Reporter memvalidasi hasil dengan exit **0**, bukan berarti aplikasi seluruhnya PASS. Ini satu run lengkap, bukan hasil parsial yang digabungkan. Bukti: `behave.json`, `run.json`, `cleanup.json`, `summary.md`, `summary.json`, `boundary-check.json`.

## Penyesuaian

- Suite default `as-built`; sembilan feature di `qa/features/as-built/`, 72 ID dalam `qa/as-built-manifest.json`.
- 69 skenario dipertahankan. Tiga skenario memakai ID baru, bukan menulis ulang hasil acceptance lama.
- `ASBUILT-F06-02`: kode asing tetap asing dan unavailable, rincian HTTP 404 bisa dibuka, tanpa angka PDB/fallback atau Login.
- `ASBUILT-F07-03`: backend asli mengirim unclassified, formula/input belum tersedia, revisi null dan snapshot bukan immutable; tidak memaksakan DTO official buatan.
- `ASBUILT-F07-08`: rincian respons dibuka lewat kontrol asli dan membedakan HTTP 404 dari transport gagal, tanpa provenance pengganti.
- **Tidak ada DTO sukses mock pada suite as-built.** Fault error/latency/storage tetap eksplisit dan berlabel. Pemetaan fitur, route, API dan delta lengkap: [AS_BUILT_ALIGNMENT.md](AS_BUILT_ALIGNMENT.md).

## Hasil menurut lapisan

| Lapisan katalog as-built | PASS | FAIL |
|---|---:|---:|
| API view/model/database disposable asli | 27 | 0 |
| Browser nyata tanpa fault injection | 34 | 1 |
| Browser nyata dengan fault injection berlabel | 10 | 0 |

Fitur 1–8 masing-masing mempunyai 8 skenario PASS; kelompok lintas fitur 7 PASS / 1 FAIL. Ini hasil katalog tersebut, bukan penerimaan seluruh kebutuhan SRS atau pengalaman pengguna.

## Dua kegagalan yang tetap ada

1. **BDD-X-06:** dashboard overflow horizontal 15 px pada viewport emulasi 1280 (`clientWidth=1265`, `scrollWidth=1280`). Halaman lain pada pemeriksaan yang sama tidak overflow. Bukti: `BDD-X-06/evidence.json` → `viewport_checks`.
2. **REG-EMPTY-YEAR-DETAIL:** memilih 2024 tanpa data lalu membuka Detail PDB masih diam-diam menampilkan Q1 2025 terbaru. Bukti: folder skenario, screenshot dan field `empty_year_before_navigation` / `empty_year_after_navigation`.

Source produk tidak diperbaiki. Reproduksi tetap di [FE_HANDOFF.md](FE_HANDOFF.md), sebuah handoff lokal yang **belum dikirim kepada pemilik FE**.

## Baseline dan gap lama tidak ditutup

Baseline v1 tetap tersedia dengan `--suite baseline`, sembilan file aslinya tidak berubah. Hasil historis 68 PASS / 4 FAIL dari 72, ditambah regresi FAIL, disimpan di [RESULTS_BASELINE_V1.md](RESULTS_BASELINE_V1.md) dan artifact sebelumnya.

Kontrol baseline terpisah tetap mereproduksi FAIL not-found; itu bukan run ulang seluruh baseline setelah perubahan as-built. **Penurunan FAIL pada v2 berasal dari perubahan cakupan yang diberi versi, bukan perbaikan produk.** Banner not-found khusus, pemisahan state utama dan dukungan official/derived masih gap acceptance. Q01–Q09, rekonsiliasi SRS final dan review visual/manusia tetap terbuka.

## Verifikasi dan cleanup

- Tujuh unit QA PASS dan ruff F PASS, terpisah dari 72 BDD. Log: `qa/as-built-harness-verified.log`.
- Deadline command CDP diuji RED→GREEN. Dua run foreground terpotong batas tool 420/360 detik, memiliki `interruption.json`, dikecualikan dari hasil final dan scratch-nya dibersihkan setelah proses pemilik tidak hidup.
- Run final memakai proses terpantau; proses sudah keluar. Seluruh 73 skenario dan 219 langkah memiliki hasil lengkap.
- Reporter memeriksa 72 ID sesuai manifest, hash QA/feature, tanpa DTO sukses mock dan cleanup.
- **165 port milik run diperiksa: tidak ada yang masih listening.** Database disposable dihapus dan cleanup Chrome/Vite berhasil. Kedua worktree produk clean, sembilan file baseline utuh. Bukti: `boundary-check.json`.

## Checkpoint dan batas

FE `e35d97899d345f18a3341bc19beba431f94179d9`; BE `d9c673fac84992b91c160bfaa4f0de33a8ce548b`. Ref lokal diperiksa, bukan klaim refresh seluruh GitHub. Browser nyata **Chrome/CDP, NON-Selenium**. Data/akun/reviewer tetap sintetis dan disposable; email locmem, CSRF asli.

Tidak ada perubahan produk, database demo/container aktif, dependency, konfigurasi provider/model, commit/push/PR, provider resmi/AI atau email nyata. Python hooks bukan sandbox OS. Ini bukan sertifikasi aksesibilitas, persetujuan visual, SMTP atau produksi. Command rerun: [README.md](README.md).
