# Handoff lokal untuk pemilik frontend DEKSI

Tanggal: 7 November 2026 (UTC+07). **Dokumen lokal ini belum dikirim sebagai pesan/issue/PR kepada pemilik lane frontend. Koordinasi masih pending.** Saat baseline di bawah diambil, tidak ada source produk yang diubah.

**Pembaruan setelah izin memperbaiki FAIL:** bagian bernomor di bawah adalah temuan baseline historis, bukan status semua temuan saat ini. Dua perbaikan lokal dibuat di branch `fix/sprint1-bdd-layout-empty-year` pada `E:/Deksi-BDD-Sprint1/frontend-checkpoint`: guard menolak Detail tahun tanpa data dengan pesan eksplisit, dan artboard dibatasi lebar kontainernya agar tidak melampaui scrollbar. Targeted `20261107-183152-product-fixes-targeted` menghasilkan PASS untuk `REG-EMPTY-YEAR-DETAIL`, `BDD-X-06`, serta kontrol konteks valid `BDD-X-03`. Patch tersedia di `PRODUCT_FIXES.patch`; belum commit/push/diterapkan ke lane pemilik. Hasil penuh terbaru dan status review tetap lihat `RESULTS.md`. Tidak ada skenario dihapus atau fitur baru ditambahkan untuk menutupi gap kontrak lama.

## Bukti yang dipin

- FE `integration/sprint1-docker-fe` — `e35d97899d345f18a3341bc19beba431f94179d9`.
- BE `integration/sprint-1-unified-be` — `d9c673fac84992b91c160bfaa4f0de33a8ce548b`.
- Run: `qa/artifacts/20261107-003936-sprint1-verified/`.
- Hasil: 72 baseline = 68 PASS, 4 FAIL; regresi tambahan = 1 FAIL. Tidak ada skenario/step SKIPPED atau undefined pada run ini. Seluruh 219 langkah memiliki hasil: 214 PASS, 5 FAIL.
- Semua data di bawah sintetis dan disposable, bukan data resmi. Browser Chrome nyata/CDP, bukan Selenium. Tidak menyentuh database demo atau container aktif.

## 1. Konteks tahun kosong dialihkan ke data terbaru — prioritas utama

ID: `REG-EMPTY-YEAR-DETAIL`. Reproduksi:
1. Fixture hanya memiliki PDB published-reviewed Q1 2025, nilai 1234.50.
2. Dashboard → pilih tahun 2024. Kartu benar menunjukkan `Belum tersedia`.
3. Tekan Detail PDB.
4. Aktual: `/indikator/pdb` tanpa konteks tahun, kemudian nilai Q1 2025 tampil.

Harapan: pertahankan konteks kosong atau beri penolakan eksplisit; jangan diam-diam pindah ke terbaru. Kandidat lokasi: `frontend/src/features/dashboard/Dashboard.tsx:73`, jalur `!card.available`. **Tidak diperbaiki oleh lane BDD.**

Bukti: folder `REG-EMPTY-YEAR-DETAIL/`, khususnya `evidence.json` (`empty_year_before_navigation`, `empty_year_after_navigation`), `empty-year-before.png` dan `browser-final.png`.

Kontrol yang PASS: `BDD-X-03`, tahun historis 2024 yang benar-benar memiliki observasi A mempertahankan nilai, periode, satuan dan empat selector pada kartu → Detail → Source Trace → kembali Detail. Jadi masalah di atas khusus konteks kosong, bukan bukti seluruh navigasi historis rusak. Q02 tetap menunggu review manusia.

## 2. Detail kode indikator asing tidak menunjukkan state not-found yang jelas

ID: `BDD-F06-02`. Buka `/indikator/unknown_bdd`.
- API trend dan trace mengembalikan 404; ringkasan menyatakan tidak tersedia.
- Aktual UI: judul `unknown_bdd`, status sebagian data belum tersedia dan field kosong, bukan state indikator tidak ditemukan.
- Tidak ditemukan substitusi nilai PDB dalam run ini; bagian yang gagal ialah state not-found, bukan kebocoran angka PDB.

Bukti: `BDD-F06-02/evidence.json` (`final_dom`, `server_requests`) dan screenshot. Area pemeriksaan: `frontend/src/features/indicators/useDetailData.ts` dan `DetailPage.tsx`.

## 3. Source Trace tidak membedakan not-found dan kegagalan transport dengan jelas

ID: `BDD-F07-08`.
1. Buka trace kode asing, backend nyata memberi 404.
2. Buka trace PDB dengan transport request yang sengaja digagalkan oleh harness.
3. Aktual: kedua kondisi jatuh ke tampilan metadata belum tersedia; pesan not-found yang berbeda tidak tampil.

Fault transport diberi label dalam `fault_injections`; ini bukan gangguan jaringan eksternal yang diada-adakan. Bukti: `BDD-F07-08/evidence.json`. Area: `useDetailData.ts`, adapter error, `SourceTracePage.tsx:25`.

## 4. Overflow horizontal dashboard pada viewport desktop

ID: `BDD-X-06`. Fixture nama indikator panjang, viewport emulasi 390 dan 1280 CSS px, seluruh halaman Sprint 1 dibuka.
- Pada viewport 1280, dashboard: `clientWidth=1265`, `scrollWidth=1280`, sehingga ada overflow horizontal 15 px.
- Halaman Login/Reset/Detail/Trace pada viewport sama: keduanya 1265, tidak ada overflow halaman.
- Pada viewport 390, halaman yang diperiksa: `clientWidth=375`, `scrollWidth=375`.

Bukti: `BDD-X-06/evidence.json` → `viewport_checks`. Periksa layout/CSS dashboard; penyebab CSS spesifik belum dipastikan. Jangan mengubah assertion dengan toleransi 15 px agar hijau. Ini pemeriksaan geometri, bukan persetujuan visual atau sertifikasi aksesibilitas.

## 5. Klasifikasi official belum dirender — uji kontrak MOCK, bukan bug E2E yang sudah terbukti

ID: `BDD-F07-03`.
- Backend nyata pada fixture saat ini menghasilkan `valueKind=unclassified`.
- Untuk menguji Given baseline `official`, harness mempertahankan seluruh angka/metadata sintetis dari respons fixture dan hanya mengganti `valueKind` menjadi `official` dalam DTO mock yang diberi label.
- Aktual UI tetap `Belum diklasifikasikan API`; label official/resmi untuk nilai tersebut tidak muncul.
- `SourceTracePage.tsx:30` berisi label tipe kalkulasi tetap. Kontrak dan dukungan backend/adapter perlu disepakati sebelum dianggap acceptance E2E.

Bukti: `BDD-F07-03/evidence.json` → `api_mocked=true`, `mock_scope`, `fault_injections`. Jangan menyebutnya bukti angka resmi terverifikasi. Tidak ada provider resmi dipanggil.

## Perbaikan produk dan verifikasi berikutnya

Handoff ini tidak memberi izin edit lane FE/BE, commit, push, PR atau merge. Pemilik frontend perlu mengonfirmasi scope perbaikan, terutama kasus tahun kosong. Setelah checkpoint koreksi diserahkan secara eksplisit, pin worktree BDD baru ke checkpoint itu dan jalankan ulang skenario terkait sebelum regresi yang relevan. Jangan memindahkan hasil PASS lama menjadi bukti checkpoint baru.
