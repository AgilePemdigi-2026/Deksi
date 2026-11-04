# Verifikasi Login Admin — backend jalur A

Status: implementasi backend dan verifikasi teknis scope auth selesai; belum terintegrasi dengan Login React, belum commit/push/PR dan bukan persetujuan deployment.

- Branch: `feat/1-login-admin-be`.
- Base: `0e92899ce54f85440fe920ca457dfd91f747e1aa`.
- Interpreter: virtualenv branch, Python 3.14.7; Django 6.1.2, Axes 9.0.0. Dependency lengkap dibekukan pada `requirements-auth.lock`; manifest sumbernya `requirements-auth.txt`.

## Hasil aktual final

| Pemeriksaan | Hasil |
|---|---|
| Django auth suite, 47 test methods | PASS, exit 0; 47 unik, bukan penjumlahan rerun/subtest |
| HTTP loopback nyata | PASS, termasuk dalam satu LiveServerTestCase di 47 test methods |
| Django system check | PASS, exit 0, tanpa isu |
| Ruff check pada kode auth/test serta settings/URL terkait | PASS, exit 0 |
| Ruff format check pada file baru milik pekerjaan ini | PASS, 15 file sudah terformat |
| pip check dengan interpreter terisolasi | PASS, tidak ada broken requirements |

Perintah dan urutan integrasi ada pada [LOGIN_ADMIN_API.md](LOGIN_ADMIN_API.md). Source pipeline indikator tidak diubah. Frontend tidak diubah.

## Cakupan

- Login username/email, ambiguitas email dan tabrakan username/email.
- Penolakan password salah, akun hilang, nonaktif dan nonstaff dengan error generik.
- Body, tipe, ukuran, media type, password whitespace dan invalid Unicode.
- CSRF aktif pada login/logout; cookie/header wajib cocok, origin asing ditolak, token pra-login tidak bisa digunakan setelah rotasi.
- Cookie flags dan konfigurasi origin development/nondebug, bukan bukti deployment HTTPS.
- Session rotation, expiry absolut 8 jam pada API dan Django Admin native, role/aktif dicabut, logout dan replay sesi lama.
- Rate limit lima kegagalan/15 menit; alias username/email canonical lintas IP, pergantian nama/UA/header palsu, lockout tidak diperpanjang, cooldown pulih, serta kegagalan native Admin dan API memakai counter yang sama.
- Penyimpanan/log failure tidak memuat password atau identifier mentah; production traceback locals disensor ketika kegagalan internal diinjeksi pada titik auth yang berbeda, termasuk native Admin.
- Akses publik anonim: summary, tren PDB kuartalan/native dan agregasi tahunan yang eksplisit, serta Source Trace dengan fixture sintetis.
- HTTP nyata: bootstrap CSRF → login → session → token lama ditolak → logout → replay cookie lama ditolak. Server dan database uji di-teardown oleh Django.

Fixture sintetis tidak membuktikan data ekonomi aktual, semua mode agregasi, atau browser auth end-to-end. CookieJar bukan browser SameSite engine. BDD/tes frontend tidak dijalankan di jalur backend ini.

## Riwayat yang tidak boleh disamakan dengan final PASS

Log RED/GREEN dan kegagalan awal disimpan terpisah di `.test-artifacts/` yang diabaikan Git. Suite awal 44 test methods lulus. Tambahan probe publik dengan observasi annual menemukan error baseline pada kode agregasi tren, sehingga expanded run 47 test methods sempat gagal satu kasus.

Rincian [KNOWN_BASELINE_TREND_ISSUE.md](KNOWN_BASELINE_TREND_ISSUE.md) mempertahankan input dan traceback. Uji auth kemudian memakai data PDB kuartalan yang didukung dan menambah request agregasi tahunan eksplisit; assertion tetap HTTP 200 tanpa akun. Tidak ada patch pada `indicators/`. Rerun final 47 test methods lulus. Ini tidak menyatakan bug annual/monthly baseline sudah diperbaiki.

Warning dependency pada instalasi awal berasal dari PYTHONPATH tool agent yang membuat metadata parent terlihat. Instalasi ulang proses-terisolasi melengkapi dependency ke virtualenv baru; environment global/historis tidak dimodifikasi. pip check pada environment terisolasi lulus. Diagnostic IDE yang memakai interpreter global bukan hasil import interpreter proyek.

## Batas review dan sisa pekerjaan

- Review source dilakukan pada alur input, auth backend, role, session lifecycle, CSRF/CORS, logging, rate limiting dan caller native Admin. Tidak ada audit keamanan menyeluruh atau sertifikasi beban multiworker/proxy/deployment.
- Endpoint auth saat ini memakai alur sinkron; integrasi backend async langsung yang baru tidak divalidasi oleh suite ini.
- Mengganti daftar authentication backend dapat membuat sesi Django lama yang menyimpan path ModelBackend perlu login kembali; tidak ada operasi penghapusan massal sesi yang dilakukan di sini.
- Konfigurasi produksi masih memerlukan SECRET_KEY aman, HTTPS, origin nyata, database operasional serta kebijakan proxy/lockout yang ditinjau. Jangan menggunakan settings atau password fixture pengujian untuk produksi.
- Tidak ada akun Admin nyata yang diprovisikan atau database existing dimigrasikan. Test runner menggunakan SQLite memory.
- Langkah integrasi berikutnya adalah menyambungkan form Login pada branch FE fitur 1 oleh koordinator, bukan dari worker frontend fitur 6/7 dan bukan perubahan otomatis oleh jalur A.
- Backend belum di-commit, di-push, dibuatkan PR atau di-merge. Izin publikasi FE sebelumnya tidak berlaku ke branch ini.
