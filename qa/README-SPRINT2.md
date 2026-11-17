# BDD Sprint 2 — kandidat aplikasi saat ini

Paket ini menguji perilaku aplikasi pada basis `11700194ab543af8198a4f72df78f1a3822d6bc6` menggunakan suite `sprint2-current`. Skenario dan binding untuk F09–F18 berada di `features/`; runner berada di `run_bdd.py`. Lihat `SPRINT2_ALIGNMENT.md` untuk perbedaan dengan acceptance sumber historis. Katalog dan manifest Sprint 1 yang diwarisi bukan bukti bahwa suite Sprint 1 telah diuji pada basis ini; beberapa mode lamanya memerlukan checkpoint terpisah.

## Hasil lokal

Setelah dua skenario historis dipindahkan, run `sprint2-archive-separated` menghasilkan **63 skenario lulus, 0 gagal, 0 dilewati** dan **227 langkah lulus, 0 gagal, 0 dilewati** pada suite aktif. Ini tidak mengubah status acceptance historis.

Pada 18 November 2026, run lokal terisolasi `sprint2-current-final` menghasilkan **63 skenario lulus, 0 gagal, 2 dikecualikan**, dan **227 langkah lulus, 0 gagal, 9 dilewati**. Dua skenario yang dikecualikan adalah `BDD_F10_05` dan `BDD_F11_04`: acceptance historis mengharapkan probe endpoint, sedangkan aplikasi saat ini menyimpan metadata endpoint tanpa probe. Dua skenario `ASBUILT_F10_05` dan `ASBUILT_F11_04` yang memeriksa perilaku tersebut termasuk dalam 63 skenario lulus. Ini bukan persetujuan perubahan SRS.

Run menggunakan Chrome/CDP, React/Vite, Django dan SQLite disposable; data dan respons provider yang digunakan untuk uji adalah sintetis. Tidak ada klaim uji provider nyata, kondisi produksi, PostgreSQL concurrency, penerimaan visual manusia, atau CI GitHub. Salinan hasil historis yang diformat tersedia di `reports/sprint2-current-final-behave.json`; artefak lokal lain tidak termasuk dalam commit. Satu perubahan spasi import dilakukan setelah run dan diperiksa dengan Ruff.

Dua skenario historis sekarang disimpan di `spec-reference/sprint2-historical-endpoint.feature`, di luar suite aktif; penggantinya tetap di `features/sources-current/`. Pemindahan ini bukan persetujuan perubahan SRS dan hasil lama tetap memiliki dua skenario yang dikecualikan.

## Menjalankan suite saat ini

Dari root checkout terisolasi, gunakan interpreter dengan dependensi aplikasi serta Behave/Behave-Django dan websocket-client yang sudah tersedia, dependensi frontend sesuai lockfile, serta Chrome terpasang. Runner menolak `backend/.env` dan `backend/.env.bdd-hidden`; jangan gunakan database atau kredensial produksi. Tetapkan `HERMES_TEST_SCRATCH` ke direktori scratch yang aman dan dapat ditulis.

```text
python -I -B qa/run_bdd.py --suite sprint2-current --label sprint2-current
```

Bukti run baru ditulis ke `qa/artifacts/`, yang diabaikan Git. Langkah ini pernah dijalankan pada mesin Windows dalam lingkungan terisolasi; instruksi ini belum diverifikasi lintas platform atau sebagai instalasi baru.
