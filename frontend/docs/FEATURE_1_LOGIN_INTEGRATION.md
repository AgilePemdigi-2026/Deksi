# Feature 1 — Integrasi Login React dan Django

Status 3 November 2026: implementasi lokal pada `feat/1-login-admin-fe`, belum commit/push/PR. Backend tetap pada worktree/branch `feat/1-login-admin-be`; tidak disalin atau digabung ke branch frontend.

## Scope dan perilaku

- `/admin/login` memakai API Django asli: CSRF bootstrap, login, pemeriksaan sesi dan logout.
- `/` tetap dashboard publik tanpa login. Transport indikator `src/api.ts`, aset dan checkpoint fitur 6/7 tidak diubah.
- Default development: origin auth `http://<hostname-frontend>:8000`. Gunakan `127.0.0.1` pada kedua service atau `localhost` pada kedua service; jangan mencampur hostname.
- Default production: API pada origin frontend yang sama, melalui routing/reverse proxy deployment. Tidak ada proxy produksi yang dipasang oleh perubahan ini.
- Override build-time opsional `VITE_AUTH_API_ORIGIN`, misalnya `https://api.example.test`. Nilai harus origin HTTP(S) tanpa username/password, path, query atau fragment. Konfigurasi salah ditolak tanpa mengirim kredensial. Variabel Vite ini publik, bukan tempat secret.
- Semua request auth memakai credentials include, no-store dan penolakan redirect. POST memakai JSON serta X-CSRFToken. Token CSRF hanya berada di closure memori client; tidak ada JWT/token sesi dalam localStorage/sessionStorage.
- Password tidak dipangkas. Backend tetap memutuskan identitas username/email, ambiguitas dan kelayakan Admin aktif/staff. Pesan error tidak menyalin teks mentah server atau nilai input.
- Setelah POST login, frontend membaca ulang sesi server. Jika cookie tidak tersimpan atau identitas berbeda, UI tidak mengklaim login berhasil.
- Setelah sukses, form disembunyikan, password dibersihkan, identitas server ditampilkan dan tombol Keluar tersedia. Tidak dibuat dashboard Admin React baru dan tidak ada redirect ke route yang belum tersedia.
- Reload memeriksa sesi kembali. Tombol Periksa status sesi memungkinkan rekonsiliasi readonly jika hasil request tidak pasti. Status frontend bukan batas otorisasi; backend tetap wajib memeriksa kewenangan pada setiap operasi Admin.
- Logout memakai CSRF terbaru dan membaca ulang sesi sebelum menyatakan keluar. Cookie lama tidak dapat digunakan kembali pada tes integrasi.
- Submit ganda dijaga dengan ref sinkron serta tombol pending. Error 400/401/403/429 dipetakan secara aman; 5xx/HTML/error network tidak disebut password salah. Hasil login yang tidak pasti menonaktifkan submit sampai status sesi diperiksa, bukan mengulang password otomatis.
- CSRF gagal menghapus token cache. Percobaan berikutnya yang disengaja mengambil token baru; tidak ada replay POST otomatis.
- Timeout per request adalah 10 detik, dengan pembatalan saat komponen dilepas. Tidak ada polling berulang, password reset atau pendaftaran baru.

## Menjalankan dua branch

Gunakan frontend dari worktree FE dan backend dari worktree BE secara bersamaan. Backend pada branch frontend lama tidak otomatis memiliki implementasi auth baru.

1. Siapkan backend sesuai `backend/docs/LOGIN_ADMIN_API.md` pada branch BE: environment privat, database lokal yang dipilih secara eksplisit dan akun Admin aktif/staff yang diprovisikan operator. Jangan memigrasikan database bersama atau memakai fixture pengujian sebagai akun sehari-hari.
2. Jalankan Django dari worktree BE pada hostname yang sama dengan frontend, umumnya port 8000.
3. Jalankan Vite dari `frontend/` pada port 5173 atau preview 62942 yang sudah tercantum pada allowlist development backend. Port lain harus ditambahkan secara eksplisit oleh konfigurasi backend yang sesuai.
4. Development HTTP memerlukan konfigurasi cookie development; production tetap memerlukan HTTPS, Secure cookies dan origin deployment yang benar. Jangan memakai `backend.test_settings_auth` untuk produksi.
5. Jika menggunakan origin auth khusus, tetapkan `VITE_AUTH_API_ORIGIN` sebelum dev/build. Ubah pula allowlist CORS dan CSRF backend secara terarah, bukan wildcard atau penonaktifan middleware.

Akun sintetis hanya dibuat dalam database memory test runner. Tidak ada akun Admin nyata/default atau database development persisten yang diprovisikan dalam pekerjaan ini. Server QA ditutup setelah tes; hasil PASS tidak berarti ada backend baru yang tetap berjalan pada port 8000.

## Perintah pemeriksaan

Dari `frontend/`, dependency lokal yang sudah ada dipakai; tidak ada dependency baru atau perubahan lockfile.

```text
npm test
npm run build
npm run lint
npm run test:browser
```

Untuk pengujian form terhadap backend nyata, tetapkan `DEKSI_AUTH_BACKEND_ROOT` ke folder `backend` worktree BE, lalu:

```text
npm run test:integration:login
```

Runner memilih interpreter `.venv` backend tersebut; opsional `DEKSI_AUTH_PYTHON` dapat menunjuk interpreter proyek yang sudah diverifikasi. Interpreter tidak tersedia adalah kegagalan, bukan alasan pindah ke Python global atau melewati tes.

Tetapkan `HERMES_TEST_SCRATCH`/`TMPDIR` ke direktori scratch yang diizinkan. `DEKSI_AUTH_ARTIFACTS` mengatur lokasi receipt/screenshot integrasi dan `DEKSI_BROWSER_ARTIFACTS` mengatur artifact regression. Jalankan dua script browser secara terpisah dengan folder artifact berbeda bila kedua JSON receipt perlu disimpan: perintah gabungan existing memakai nama `verification.json` yang sama, walaupun output terminal memuat keduanya.

Integration runner memakai settings test backend dan SQLite shared-memory Django, akun sintetis, Vite serta Chrome berprofil baru. Origin port QA di-allowlist secara eksplisit dalam override test-only. Tidak ada interception respons pada tes integrasi; request berasal dari handler form aplikasi, bukan direct-fetch pengganti submit. Request readonly tambahan pada harness memeriksa sesi server.

## Hasil aktual terakhir

| Pemeriksaan | Hasil dan cakupan |
|---|---|
| `npm test` | PASS: 25 metode Node, terdiri dari 12 baseline/SSR/validasi dan 13 client auth |
| `npm run test:integration:login` | PASS: 4 metode Django + Chrome dengan aplikasi sebenarnya |
| `npm run test:browser` | PASS: 5 grup dashboard dan 8 grup Login; API di suite regression ini sintetis |
| `npm run build` | PASS: TypeScript dan Vite production build |
| `npm run lint` | Exit 0: 0 error, 3 warning bawaan di API indikator/EconomicSummary/TrendChart; tidak ada warning baru Login |

Keempat metode integrasi mencakup: login melalui tombol dan konfirmasi server; dua submit langsung menghasilkan satu POST; penolakan password/nonstaff/nonaktif, CSRF stale dan retry disengaja serta lockout kelima; tiga reload berturut-turut, logout melalui tombol dan replay cookie lama. Grup/assertion/reload bukan tambahan metode tes unik.

Profil browser dan database uji final dibersihkan; tidak tercatat unhandled exception browser atau exception request Django pada keempat receipt final. Build masih memperingatkan bundle lebih dari 500 kB; batas tidak dinaikkan untuk menyembunyikannya.

## Riwayat kegagalan dan batas bukti

- RED pertama membuktikan form lama tidak mengirim POST auth. RED logout membuktikan kontrol Keluar belum ada, lalu GREEN setelah implementasi.
- Harness awal sempat mengganti origin FE antar-metode, padahal middleware CSRF Django menyimpan trusted-origin dalam cached_property. Port FE sekarang stabil per instance live server; ini perbaikan harness, bukan pelonggaran CSRF.
- Pengamat respons sempat menghitung OPTIONS sebagai hasil POST; kini requestId dipakai untuk membedakan metode. Interception pada regression UI hanya mengabaikan Invalid InterceptionId bila berkorelasi dengan Network.loadingFailed canceled untuk request yang sama; error lain tetap menggagalkan tes.
- Satu run lanjutan mengalami kegagalan restore sesi sesaat dengan pesan hasil tidak dapat dipastikan. Penyebab tepat kegagalan itu belum dikonfirmasi. Dua focused run berikutnya dan run penuh terakhir lulus, termasuk tiga reload per kasus. Bukti gagal tetap disimpan; PASS berikutnya bukan bukti bahwa penyebab historis sudah diketahui atau diperbaiki.
- Putaran verifikasi paralel via wrapper tool sempat terinterupsi tanpa receipt lengkap. Hasilnya tidak dihitung PASS. Perintah standar kemudian dijalankan melalui terminal secara langsung dan hasil final dicatat.
- Log Broken pipe saat request QA dibatalkan/halaman ditutup tetap disimpan; bukan alasan mengabaikan assertion atau melonggarkan keamanan.
- Tes backend 47 metode sebelumnya tidak diulang seluruhnya: hash 23 berkas pada receipt backend tetap sama. Pengujian baru memverifikasi integrasi browser ke backend tersebut.
- Screenshot desktop status berhasil dan mobile diperiksa, tetapi tampilan status akun yang baru belum memperoleh approval visual manusia. Approval desain dasar sebelumnya tidak dibatalkan.
- Tidak memverifikasi deployment HTTPS, reverse proxy, multiworker, akun nyata, reset password atau data ekonomi live. Bug agregasi tren baseline tidak disentuh.

Bukti rinci berada pada bundle/receipt integrasi sesi ini. Belum ada commit, push, PR, merge atau perubahan shared branch yang dilakukan untuk integrasi ini.
