# DEKSI — hasil BDD Sprint 1

Run aktual: `20261111-022903-feedback-admin-final`. Exit aplikasi: **0**.

Suite `sprint2-admin-feedback-v1` — 10 skenario: **{'passed': 10}**.

Gagal: **0**, dilewati/tak terdefinisi: **nihil**.
Langkah aktual: **{'passed': 30}**.

## Lapisan bukti

| Lapisan | Hasil |
|---|---|
| api-real-view-disposable-db | {'passed': 10} |

Chrome nyata via CDP, bukan Selenium. Kegagalan yang diinjeksi diberi label; respons sukses mock bukan bukti E2E.
Q02/Q03/Q04 dieksekusi sebagai kontrak kandidat, **bukan persetujuan manusia**. Visual review dan rekonsiliasi SRS lengkap tetap pending.

## Peta syarat dan endpoint

| ID | Nama | REQ | Endpoint | Status |
|---|---|---|---|---|
| BDD-F15-01 | Daftar menampilkan kategori tanggal dan status | R_F15_01 | `-` | PASSED |
| BDD-F15-02 | Daftar kosong ditangani sebagai hasil valid | R_F15_02 | `-` | PASSED |
| BDD-F15-03 | Daftar umpan balik dilindungi untuk Admin | R_F15_03 | `-` | PASSED |
| BDD-F16-01 | Detail mempertahankan laporan indikator dan status | R_F16_01 | `-` | PASSED |
| BDD-F16-02 | Detail laporan tak dikenal tidak ditemukan | R_F16_02 | `-` | PASSED |
| BDD-F17-01 | Kata kunci menyaring laporan terkait | R_F17_01 | `-` | PASSED |
| BDD-F17-02 | Pencarian tanpa hasil menghasilkan daftar kosong | R_F17_02 | `-` | PASSED |
| BDD-F18-01 | Perubahan status menyimpan catatan waktu dan audit | R_F18_01 | `-` | PASSED |
| BDD-F18-02 | Status tidak valid tidak mengubah laporan | R_F18_02 | `-` | PASSED |
| BDD-F18-03 | Pengunjung anonim tidak dapat mengubah status | R_F18_03 | `-` | PASSED |

## Cakupan endpoint (tercatat server uji)

| Method | Path | Status HTTP | Jumlah |
|---|---|---|---:|
| GET | `/api/admin/feedback/` | 200 | 5 |
| GET | `/api/admin/feedback/` | 401 | 1 |
| GET | `/api/admin/feedback/3/` | 200 | 1 |
| GET | `/api/admin/feedback/7/` | 200 | 1 |
| GET | `/api/admin/feedback/8/` | 200 | 1 |
| GET | `/api/admin/feedback/999999/` | 404 | 1 |
| GET | `/api/auth/csrf/` | 200 | 1 |
| POST | `/api/admin/feedback/7/status/` | 200 | 1 |
| POST | `/api/admin/feedback/8/status/` | 400 | 1 |
| POST | `/api/admin/feedback/9/status/` | 401 | 1 |

## Cakupan syarat

| REQ | Skenario | Jumlah |
|---|---|---:|
| R_F15_01 | BDD-F15-01 | 1 |
| R_F15_02 | BDD-F15-02 | 1 |
| R_F15_03 | BDD-F15-03 | 1 |
| R_F16_01 | BDD-F16-01 | 1 |
| R_F16_02 | BDD-F16-02 | 1 |
| R_F17_01 | BDD-F17-01 | 1 |
| R_F17_02 | BDD-F17-02 | 1 |
| R_F18_01 | BDD-F18-01 | 1 |
| R_F18_02 | BDD-F18-02 | 1 |
| R_F18_03 | BDD-F18-03 | 1 |

## Rincian skenario

### BDD-F15-01 — Daftar menampilkan kategori tanggal dan status
Status: **PASSED**; REQ: R_F15_01; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki dua laporan umpan balik sintetis dengan kategori dan status berbeda [passed]
- When Admin meminta daftar umpan balik [passed]
- Then daftar berisi kedua laporan dengan kategori tanggal dan status [passed]
Request server:
- GET /api/admin/feedback/ -> 200
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F15-01\evidence.json`

### BDD-F15-02 — Daftar kosong ditangani sebagai hasil valid
Status: **PASSED**; REQ: R_F15_02; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki daftar umpan balik kosong [passed]
- When Admin meminta daftar umpan balik [passed]
- Then respons sukses menampilkan daftar kosong tanpa error [passed]
Request server:
- GET /api/admin/feedback/ -> 200
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F15-02\evidence.json`

### BDD-F15-03 — Daftar umpan balik dilindungi untuk Admin
Status: **PASSED**; REQ: R_F15_03; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given pengunjung anonim belum memiliki sesi Admin [passed]
- When pengunjung meminta daftar umpan balik Admin [passed]
- Then server menolak akses daftar dengan status 401 [passed]
Request server:
- GET /api/admin/feedback/ -> 401
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F15-03\evidence.json`

### BDD-F16-01 — Detail mempertahankan laporan indikator dan status
Status: **PASSED**; REQ: R_F16_01; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki laporan sintetis terkait indikator PDB [passed]
- When Admin membuka detail laporan tersebut [passed]
- Then detail menunjukkan indikator terkait dan status yang sama dengan daftar [passed]
Request server:
- GET /api/admin/feedback/3/ -> 200
- GET /api/admin/feedback/ -> 200
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F16-01\evidence.json`

### BDD-F16-02 — Detail laporan tak dikenal tidak ditemukan
Status: **PASSED**; REQ: R_F16_02; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki sesi valid tanpa laporan terpilih [passed]
- When Admin meminta detail laporan yang tidak ada [passed]
- Then server mengembalikan status 404 tanpa detail laporan [passed]
Request server:
- GET /api/admin/feedback/999999/ -> 404
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F16-02\evidence.json`

### BDD-F17-01 — Kata kunci menyaring laporan terkait
Status: **PASSED**; REQ: R_F17_01; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki laporan dengan kata kunci indikator dan laporan pembanding [passed]
- When Admin mencari umpan balik menggunakan kata kunci indikator [passed]
- Then hanya laporan yang cocok ditampilkan [passed]
Request server:
- GET /api/admin/feedback/ -> 200
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F17-01\evidence.json`

### BDD-F17-02 — Pencarian tanpa hasil menghasilkan daftar kosong
Status: **PASSED**; REQ: R_F17_02; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki laporan umpan balik sintetis [passed]
- When Admin mencari umpan balik menggunakan kata kunci yang tidak ada [passed]
- Then pencarian sukses menampilkan nol hasil [passed]
Request server:
- GET /api/admin/feedback/ -> 200
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F17-02\evidence.json`

### BDD-F18-01 — Perubahan status menyimpan catatan waktu dan audit
Status: **PASSED**; REQ: R_F18_01; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki laporan pending dan token CSRF valid [passed]
- When Admin mengubah status menjadi resolved dengan catatan penanganan sintetis [passed]
- Then status catatan waktu pembaruan dan audit log tersimpan [passed]
Request server:
- GET /api/admin/feedback/7/ -> 200
- POST /api/admin/feedback/7/status/ -> 200
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F18-01\evidence.json`

### BDD-F18-02 — Status tidak valid tidak mengubah laporan
Status: **PASSED**; REQ: R_F18_02; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given Admin memiliki laporan pending dan token CSRF valid [passed]
- When Admin mengirim perubahan dengan status yang tidak valid [passed]
- Then server menolak perubahan dan tidak membuat audit log [passed]
Request server:
- GET /api/admin/feedback/8/ -> 200
- POST /api/admin/feedback/8/status/ -> 400
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F18-02\evidence.json`

### BDD-F18-03 — Pengunjung anonim tidak dapat mengubah status
Status: **PASSED**; REQ: R_F18_03; endpoint: `-`; lapisan: api-real-view-disposable-db.
Langkah:
- Given laporan pending tersedia tanpa sesi Admin dan token CSRF valid [passed]
- When pengunjung anonim mengirim perubahan status [passed]
- Then server menolak perubahan dan status laporan tetap pending [passed]
Request server:
- GET /api/auth/csrf/ -> 200
- POST /api/admin/feedback/9/status/ -> 401
Bukti: `C:\Users\KESIT\Downloads\PPL PRAK\qa\artifacts\20261111-022903-feedback-admin-final\BDD-F18-03\evidence.json`


## Kegagalan aktual

Nihil — 0 gagal, langkah non-passed: **nihil**.

## Batas dan keselamatan

- Kode backend: live working tree `unknown` (unknown), BUKAN checkpoint pin as-built.
- DB sqlite disposable per skenario; test server LiveServer milik run; port acak.
- Endpoint http pada skenario negatif menunjuk 127.0.0.1:9 (loopback, refused cepat); audit hook melarang koneksi non-loopback.
- `.env` aplikasi diparkir selama run lalu dikembalikan; settings uji menimpa SECRET_KEY/DEBUG/BPS dan memaksa sqlite+locmem.
- Spec `qa/features/f09_*.Data` tetap dokumen; yang tereksekusi ialah `qa/features/sources/*.feature` + `steps/source_steps.py`.
- Receipt cleanup PASS; hash source QA cocok dengan run.
- Tidak ada perbaikan produk, install, commit, push atau PR. Python audit hook bukan sandbox OS.
