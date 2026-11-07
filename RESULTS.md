# BDD Sprint 1 — perbaikan lokal as-built v2.1, 7 November 2026

**Dua FAIL sudah diperbaiki pada produk lokal, bukan dihapus dari BDD. Seluruh suite berhasil dijalankan.**

| Cakupan | PASS | FAIL | SKIPPED / undefined |
|---|---:|---:|---:|
| 72 skenario as-built v2.1 | 72 | 0 | 0 |
| Ditambah regresi: 73 skenario | 73 | 0 | 0 |
| Seluruh 219 langkah | 219 | 0 | 0 |

Run: `qa/artifacts/20261107-183251-product-fixes-full/`. Exit runner **0**, reporter **0**. Ini satu run lengkap, bukan hasil parsial yang digabungkan. Bukti: `behave.json`, `run.json`, `cleanup.json`, `summary.md`, `summary.json`, `boundary-check.json`. Hasil sebelum perbaikan dipertahankan di `RESULTS_AS_BUILT_V2_BEFORE_FIXES.md` dan artifact historis.

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
| Browser nyata tanpa fault injection | 35 | 0 |
| Browser nyata dengan fault injection berlabel | 10 | 0 |

Fitur 1–8 masing-masing mempunyai 8 skenario PASS; kelompok lintas fitur 8 PASS. Regresi tambahan juga PASS. Ini hasil katalog tersebut, bukan penerimaan seluruh kebutuhan SRS atau pengalaman pengguna.

## Dua perbaikan produk yang diizinkan

1. **BDD-X-06 — layout dashboard:** ukuran artboard berbasis viewport sebelumnya melampaui ruang setelah scrollbar desktop. `dashboard.css` kini membatasi artboard dengan `max-width:100%`, bukan menyembunyikan overflow. Targeted browser membuktikan dashboard `scrollWidth=1265` dan `clientWidth=1265`; seluruh halaman yang diuji juga tidak overflow pada lebar 375 dan desktop emulasi 1280. Skenario yang sama PASS lagi pada run penuh.
2. **REG-EMPTY-YEAR-DETAIL — konteks filter:** `Dashboard.tsx` kini menolak navigasi jika kartu unavailable untuk tahun yang dipilih dan menampilkan pesan eksplisit tahun tersebut. Browser tetap pada filter 2024, tidak menampilkan Detail 2025. Tombol hero tanpa kartu PDB juga tidak lagi membuka latest diam-diam. Oracle diperkuat untuk memeriksa pesan penolakan dan tahun, bukan hanya tidak adanya redirect. Kontrol konteks valid `BDD-X-03` tetap PASS: tahun yang memiliki data tetap dapat membuka Detail dan Source Trace observasi yang sesuai.

Perubahan produk **hanya dua file** di `E:/Deksi-BDD-Sprint1/frontend-checkpoint/frontend/src/features/dashboard/`: `Dashboard.tsx` dan `dashboard.css`. Branch lokal `fix/sprint1-bdd-layout-empty-year`, belum commit/push dan belum diterapkan ke lane FE sesi lain. `PRODUCT_FIXES.patch` tersedia dan lolos `git apply --reverse --check` terhadap kandidat lokal. Reproduksi historis beserta pembaruan ada di [FE_HANDOFF.md](FE_HANDOFF.md), **belum dikirim kepada pemilik FE**.

## Baseline dan gap lama tidak ditutup

Baseline v1 tetap tersedia dengan `--suite baseline`, sembilan file aslinya tidak berubah. Hasil historis 68 PASS / 4 FAIL dari 72, ditambah regresi FAIL, disimpan di [RESULTS_BASELINE_V1.md](RESULTS_BASELINE_V1.md) dan artifact sebelumnya.

Kontrol baseline terpisah sebelumnya mereproduksi FAIL not-found; seluruh baseline belum dijalankan ulang pada kandidat perbaikan ini. **Tiga perubahan cakupan pada v2 tetap terpisah dari dua perbaikan produk v2.1.** Banner not-found khusus, pemisahan state utama dan dukungan official/derived masih gap acceptance. Q01–Q09, rekonsiliasi SRS final dan review visual/manusia tetap terbuka. Tidak ada skenario dihapus.

## Verifikasi dan cleanup

- **95 test frontend Sprint 1 PASS**, **7 unit QA PASS**, build TypeScript/Vite PASS dan ruff F PASS. Dashboard targeted unit juga 9 PASS (subset/overlap suite Sprint 1, bukan tambahan 9 test unik). Log `qa/product-fixes-*.log`.
- Oxlint exit 0 dengan empat warning di file yang tidak disentuh: `tests/dashboard.browser.mjs`, `src/components/EconomicSummary.tsx`, `src/api.ts`, `src/components/TrendChart.tsx`. Bukan lint tanpa warning; tidak diperbaiki di luar scope.
- Deadline command CDP diuji RED→GREEN. Dua run foreground terpotong batas tool 420/360 detik, memiliki `interruption.json`, dikecualikan dari hasil final dan scratch-nya dibersihkan setelah proses pemilik tidak hidup.
- Run final memakai proses terpantau; proses sudah keluar. Seluruh 73 skenario dan 219 langkah memiliki hasil lengkap.
- Reporter memeriksa 72 ID sesuai manifest, hash QA/feature, tanpa DTO sukses mock dan cleanup.
- **165 port milik run diperiksa: tidak ada yang masih listening.** Database disposable dihapus dan cleanup Chrome/Vite berhasil. Backend clean; frontend hanya dua file perubahan yang diizinkan. Sembilan feature baseline dan sembilan feature as-built tidak berubah. Bukti: `boundary-check.json`.

## Checkpoint dan batas

Base FE `e35d97899d345f18a3341bc19beba431f94179d9` **ditambah overlay lokal dua file**, dikunci hash pada manifest v2.1; BE `d9c673fac84992b91c160bfaa4f0de33a8ce548b`. SHA base FE belum memuat perbaikan. Ref lokal diperiksa, bukan klaim refresh seluruh GitHub. Browser nyata **Chrome/CDP, NON-Selenium**. Data/akun/reviewer tetap sintetis dan disposable; email locmem, CSRF asli.

Tidak ada perubahan database demo/container aktif, dependency, konfigurasi provider/model, commit/push/PR, provider resmi/AI atau email nyata. Python hooks bukan sandbox OS. Ini bukan sertifikasi aksesibilitas, persetujuan visual, SMTP atau produksi. Command rerun: [README.md](README.md).
