# Verifikasi backend Sprint 1 gabungan

## Bukti langsung pada kandidat

Interpreter existing: `E:/Deksi-Team/.hermes/worktrees/feature-1-login-be/backend/.venv/Scripts/python.exe`. Python dijalankan eksplisit; usersite dan inherited PYTHONPATH/PYTHONHOME dinonaktifkan/dibersihkan. Bukan environment baru atau dependency install.

| Pemeriksaan | Hasil aktual | Bukti lokal |
|---|---|---|
| Suite gabungan `admin_auth.tests indicators.tests`, `backend.test_settings_sprint1` | 177 unik: 176 PASS, 1 SKIP, exit 0 | `.artifacts/sprint1-unified/combined-regression.log` |
| Reset concurrency, SQLite file-backed scratch, 3 test eksplisit | 3 PASS, exit 0 | `reset-concurrency.log` |
| Django check | PASS, 0 issues, exit 0 | `django-check.log` |
| Migration drift | PASS, no changes detected, exit 0 | `migration-drift.log` |
| Dependency check | PASS, exit 0 | `dependencies.log` |
| Lint auth/integrasi/new tests | PASS, exit 0 | `ruff-check-targeted.log` |
| Format auth/new settings/new integration tests | PASS, exit 0 | `ruff-format.log` |
| AST semua source backend saat pemeriksaan awal | PASS, 104 file sebelum helper kanonik baru | `static-results.json` |
| Whitespace diff | PASS, exit 0 | `whitespace.log` |
| Source guard publik Batch 1 + auth checkpoint | MATCH pada inspeksi pascaregresi | source hashes di receipt |

**180 tes unik keseluruhan: 179 PASS, 1 SKIP.** Empat tes smoke dan seluruh rerun bukan tambahan tes unik. SKIP: tes symlink RAW karena proses Windows tidak memiliki privilege untuk membuat symlink; path-traversal, containment dan download tests lain tetap berjalan. Pengujian BDD terpisah, PostgreSQL dan browser React tidak diklaim oleh jumlah tersebut.

## Jalur integrasi baru yang dieksekusi

- Semua app auth/axes/indicators aktif, middleware CSRF/auth/reporting/Axes serta authentication backends aplikasi dipakai bersama.
- Seluruh migration graph conflict-free dan satu leaf per app; tabel feedback, candidate observation, auth limiter dan Axes ada pada database uji yang sama. Upgrade dua jalur indikator tetap diuji oleh suite existing.
- HTTP socket loopback nyata: ringkasan/filter/trend/Source Trace/categories/update-status publik sebelum Login, sesudah Login, sesudah invalidasi sesi oleh Reset, dan setelah Logout.
- Nilai sintetis presisi dan review boundary publik tetap dipertahankan. Ini bukan angka ekonomi resmi.
- Feedback anonymous tetap memerlukan CSRF. Token sebelum Login ditolak setelah rotasi; token baru dari Login diterima. Dua feedback dibaca balik dari DB sebagai pending.
- Reset request melalui locmem menghasilkan native capability; check/confirm berjalan; sesi lama dan password lama ditolak, replay reset ditolak, password baru dapat Login. Tidak ada auto-login.
- Tes existing tetap menguji role/nonstaff, lockout, expiry/privacy/reporting, input bounds, native Admin dan permission moderasi.
- Concurrency: dua confirm menghasilkan tepat satu commit, kuota identity dibagi koneksi, fixed window/cleanup dibatasi; SQLite saja, bukan jaminan seluruh engine/interleaving produksi.

## Verifikasi kanonik terpisah

Recipe default hasil deteksi ditolak karena memuat install, interpreter ambigu, settings DB tidak terisolasi dan listener `0.0.0.0:8000`. Deteksi pertama sempat timeout; deteksi kedua selesai. Pengguna secara eksplisit mengizinkan recipe lokal khusus kandidat ini, bukan perubahan profil/global.

Bootstrap dan build kanonik awal sudah dijalankan: `ok: true`, dependency/lint/format/check/drift PASS; readiness null karena start sengaja tidak dijalankan pada pemeriksaan terarah tersebut. Hasil itu bukan full recipe PASS.

Perintah full kanonik yang diotorisasi:

```text
hermes verify --json --timeout 1800 --ready-timeout 35
```

Keluaran aktual disimpan sebagai `.artifacts/sprint1-unified/canonical-full-final.json`. Berkas tersebut adalah otoritas status full: wajib `source: manifest`, semua phase exit 0, `ok: true` dan readiness HTTP 200 pada `/api/indicators/`. Selama belum ada hasil lengkap tersebut, status full tetap pending. Pemeriksaan cleanup dan hash sesudah run dicatat dalam `.artifacts/sprint1-unified/final-inspection.json`; dokumen ini tidak mengantisipasi hasil run yang belum selesai.

Bootstrap tidak menginstal apa pun. Build adalah lint/check/drift, bukan binary build. Test mencakup suite gabungan plus concurrency. Startup WSGI menjalankan migrate DB memory dalam proses yang sama, bound `127.0.0.1:55947`, auto-shutdown 20 detik, dan teardown koneksi. Readiness bukan bukti dataset riil atau frontend terhubung. Full berarti full recipe backend ini, bukan full produk/deployment.

## Kegagalan dan batas yang dipertahankan

- Percobaan suite foreground pertama terputus oleh batas waktu tool setelah sebagian tes; bukan hasil PASS penuh, bukan assertion failure. Log dipertahankan sebagai `combined-regression-interrupted.log`; rerun background menyelesaikan seluruh 177 test dengan exit 0. Direktori scratch milik run terputus dibersihkan.
- Lint luas menemukan tujuh issue gaya pada migration tim `0004_feedback_model.py`. File dipertahankan byte-identical dan dikecualikan dari target lint terarah, bukan mengubah rules atau riwayat migration. Jangan menyebut seluruh repo lint-clean.
- Reporting reset pada uji konfigurasi invalid mencetak pesan aman generik; parser daftar test harus memperhitungkan pesan log di tengah baris dan membandingkan IDs unik dengan `Ran 177 tests`.
- Reset aplikasi biasa tetap disabled; locmem hanya uji in-process. SMTP/inbox, timing synchronous delivery, proxy/CORS produksi dan provider belum dinilai.
- Pengujian tidak mengubah frontend, data resmi, provider AI, package install, database kerja atau credential/.env. Visual acceptance tidak diklaim. Publikasi adalah langkah terpisah: pengguna kemudian mengizinkan audit cepat, commit dan push branch integrasi ini, bukan PR atau merge shared branch.
- Bukti tes mula-mula diperoleh pada overlay lokal uncommitted. Saat mengambil hasil dari Git, pastikan checkout memakai checkpoint integrasi yang sudah diterbitkan, bukan parent BE7. SHA publikasi dan readback remote dicatat dalam receipt lokal publikasi.
