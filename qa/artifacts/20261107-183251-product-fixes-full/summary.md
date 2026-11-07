# DEKSI — hasil BDD Sprint 1

Run aktual: `20261107-183251-product-fixes-full`. Exit aplikasi: **0**.

Suite `sprint1-as-built-v2.1-local-fixes` — 72 skenario: **{'passed': 72}**.
Termasuk regresi tambahan: **{'passed': 73}**.

Langkah aktual: **{'passed': 219}**.

## Lapisan bukti

| Lapisan | Hasil |
|---|---|
| browser-real-React-Django | {'passed': 35} |
| api-real-view-disposable-db | {'passed': 27} |
| browser-labelled-fault-injection | {'passed': 10} |

Chrome nyata via CDP, bukan Selenium. Kegagalan yang diinjeksi diberi label; respons sukses mock bukan bukti E2E.
Q02/Q03/Q04 dieksekusi sebagai kontrak kandidat, **bukan persetujuan manusia**. Visual review dan rekonsiliasi SRS lengkap tetap pending.

## Semua skenario

| ID | Status | Lapisan |
|---|---|---|
| REG-EMPTY-YEAR-DETAIL | PASSED | browser-real-React-Django |
| BDD-F01-01 | PASSED | browser-real-React-Django |
| BDD-F01-02 | PASSED | api-real-view-disposable-db |
| BDD-F01-03 | PASSED | browser-real-React-Django |
| BDD-F01-04 | PASSED | api-real-view-disposable-db |
| BDD-F01-05 | PASSED | api-real-view-disposable-db |
| BDD-F01-06 | PASSED | browser-real-React-Django |
| BDD-F01-07 | PASSED | api-real-view-disposable-db |
| BDD-F01-08 | PASSED | browser-labelled-fault-injection |
| BDD-F02-01 | PASSED | api-real-view-disposable-db |
| BDD-F02-02 | PASSED | browser-real-React-Django |
| BDD-F02-03 | PASSED | api-real-view-disposable-db |
| BDD-F02-04 | PASSED | browser-real-React-Django |
| BDD-F02-05 | PASSED | browser-real-React-Django |
| BDD-F02-06 | PASSED | api-real-view-disposable-db |
| BDD-F02-07 | PASSED | api-real-view-disposable-db |
| BDD-F02-08 | PASSED | browser-labelled-fault-injection |
| BDD-F03-01 | PASSED | browser-real-React-Django |
| BDD-F03-02 | PASSED | api-real-view-disposable-db |
| BDD-F03-03 | PASSED | browser-real-React-Django |
| BDD-F03-04 | PASSED | api-real-view-disposable-db |
| BDD-F03-05 | PASSED | api-real-view-disposable-db |
| BDD-F03-06 | PASSED | browser-real-React-Django |
| BDD-F03-07 | PASSED | browser-labelled-fault-injection |
| BDD-F03-08 | PASSED | browser-labelled-fault-injection |
| BDD-F04-01 | PASSED | api-real-view-disposable-db |
| BDD-F04-02 | PASSED | browser-real-React-Django |
| BDD-F04-03 | PASSED | api-real-view-disposable-db |
| BDD-F04-04 | PASSED | browser-real-React-Django |
| BDD-F04-05 | PASSED | browser-real-React-Django |
| BDD-F04-06 | PASSED | browser-real-React-Django |
| BDD-F04-07 | PASSED | browser-labelled-fault-injection |
| BDD-F04-08 | PASSED | browser-labelled-fault-injection |
| BDD-F05-01 | PASSED | api-real-view-disposable-db |
| BDD-F05-02 | PASSED | browser-real-React-Django |
| BDD-F05-03 | PASSED | api-real-view-disposable-db |
| BDD-F05-04 | PASSED | browser-real-React-Django |
| BDD-F05-05 | PASSED | api-real-view-disposable-db |
| BDD-F05-06 | PASSED | api-real-view-disposable-db |
| BDD-F05-07 | PASSED | browser-real-React-Django |
| BDD-F05-08 | PASSED | browser-labelled-fault-injection |
| BDD-F06-01 | PASSED | browser-real-React-Django |
| ASBUILT-F06-02 | PASSED | browser-real-React-Django |
| BDD-F06-03 | PASSED | browser-real-React-Django |
| BDD-F06-04 | PASSED | browser-real-React-Django |
| BDD-F06-05 | PASSED | browser-real-React-Django |
| BDD-F06-06 | PASSED | browser-real-React-Django |
| BDD-F06-07 | PASSED | browser-real-React-Django |
| BDD-F06-08 | PASSED | browser-labelled-fault-injection |
| BDD-F07-01 | PASSED | api-real-view-disposable-db |
| BDD-F07-02 | PASSED | api-real-view-disposable-db |
| ASBUILT-F07-03 | PASSED | browser-real-React-Django |
| BDD-F07-04 | PASSED | browser-real-React-Django |
| BDD-F07-05 | PASSED | browser-real-React-Django |
| BDD-F07-06 | PASSED | api-real-view-disposable-db |
| BDD-F07-07 | PASSED | browser-real-React-Django |
| ASBUILT-F07-08 | PASSED | browser-labelled-fault-injection |
| BDD-F08-01 | PASSED | browser-real-React-Django |
| BDD-F08-02 | PASSED | api-real-view-disposable-db |
| BDD-F08-03 | PASSED | api-real-view-disposable-db |
| BDD-F08-04 | PASSED | browser-real-React-Django |
| BDD-F08-05 | PASSED | api-real-view-disposable-db |
| BDD-F08-06 | PASSED | api-real-view-disposable-db |
| BDD-F08-07 | PASSED | browser-labelled-fault-injection |
| BDD-F08-08 | PASSED | api-real-view-disposable-db |
| BDD-X-01 | PASSED | browser-real-React-Django |
| BDD-X-02 | PASSED | api-real-view-disposable-db |
| BDD-X-03 | PASSED | browser-real-React-Django |
| BDD-X-04 | PASSED | browser-real-React-Django |
| BDD-X-05 | PASSED | browser-real-React-Django |
| BDD-X-06 | PASSED | browser-real-React-Django |
| BDD-X-07 | PASSED | api-real-view-disposable-db |
| BDD-X-08 | PASSED | browser-real-React-Django |

## Perubahan cakupan, bukan perbaikan produk

Suite as-built memakai ID baru untuk tiga skenario yang disesuaikan. Baseline acceptance lama tetap tersedia dan tidak dinyatakan lulus oleh hasil ini.
- `BDD-F06-02` → `ASBUILT-F06-02`
- `BDD-F07-03` → `ASBUILT-F07-03`
- `BDD-F07-08` → `ASBUILT-F07-08`
Kebutuhan acceptance yang belum ditutup:
- Unknown-indicator dedicated not-found banner
- Source Trace prominent not-found versus network state
- Official classification API/adapter/UI support
- Q01-Q09 and full SRS/human visual acceptance remain open

## Perbaikan produk lokal yang diizinkan

Base FE di atas ditambah overlay belum di-commit pada `fix/sprint1-bdd-layout-empty-year`; SHA base tidak memuat perbaikan ini.
Perubahan source dikunci oleh product_source_hashes dalam suite_manifest run.json.
- frontend/src/features/dashboard/Dashboard.tsx
- frontend/src/features/dashboard/dashboard.css

## Kegagalan aktual

## Batas dan keselamatan

- Checkpoint BE: `d9c673fac84992b91c160bfaa4f0de33a8ce548b`.
- Checkpoint FE: `e35d97899d345f18a3341bc19beba431f94179d9`.
- Snapshot spesifikasi Batch 1 tidak diedit untuk mengejar PASS; tag historis `@not_run` tidak digunakan sebagai status hasil run.
- DB, RAW, browser/profile dan port milik pengujian. Email locmem, CSRF asli. Tidak ada provider resmi/AI atau email nyata.
- Receipt cleanup PASS; hash source QA cocok dengan run. Periksa `boundary-check.json` untuk pemeriksaan port dan Git setelah run.
- Perbaikan produk hanya pada overlay FE lokal di atas; tidak ada install, commit, push atau PR. Python audit hook bukan sandbox OS.
- Lihat `../../../FE_HANDOFF.md` untuk reproduksi dan koordinasi frontend yang masih pending.
