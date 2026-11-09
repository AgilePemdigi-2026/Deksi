# Login Admin — Django session API

## Scope dan baseline

Branch kerja: `feat/1-login-admin-be`, base `0e92899ce54f85440fe920ca457dfd91f747e1aa`. Ini implementasi backend, bukan perubahan UI atau deployment. Frontend tetap pada branch terpisah. Tidak ada pendaftaran publik, reset password atau perubahan model User.

Publik tetap tanpa akun. Login hanya untuk pengguna aktif dengan `is_staff=True`. Flag staff tidak memberikan seluruh permission model Django secara otomatis. Username dan email didukung; identifier dipangkas di tepi dan dinormalisasi sesuai model. Password tidak dipangkas. Jika username/email cocok ke lebih dari satu akun, autentikasi ditolak, bukan memilih `.first()`.

## Endpoint

Semua path berikut berada pada origin backend. Cookie session bersifat HttpOnly dan tidak dikembalikan sebagai data JSON.

| Metode | Path | Respons |
|---|---|---|
| GET | `/api/auth/csrf/` | 200 `{csrfToken: string}` dan cookie CSRF. Token di JSON ter-mask, bukan session key. |
| POST | `/api/auth/login/` | JSON `{identifier: string, password: string}`. CSRF wajib. Sukses 200 `{authenticated: true, user: {id, username, isAdmin: true}, csrfToken: string}`. |
| GET | `/api/auth/session/` | Admin aktif: 200 `{authenticated: true, user: {id, username, isAdmin: true}}`. Anonim/kedaluwarsa/nonaktif: 200 `{authenticated: false, user: null}`. Role staff yang dicabut setelah login: 403 `forbidden`. |
| POST | `/api/auth/logout/` | CSRF wajib; 200 `{authenticated: false, user: null}`. Sesi lama dibatalkan. Idempotent ketika sudah anonim dengan CSRF valid. |

- Body login hanya `application/json`; maksimum 16 KiB, identifier 1–254 karakter dan bukan whitespace saja, password 1–4096 karakter. Spasi password tetap memiliki arti.
- Field lain tidak digunakan untuk role, redirect, expiry atau kontrol keamanan. Tidak ada redirect ke URL input pengguna.
- Respons endpoint/error auth tidak boleh dicache. Semua error aplikasi berikut berbentuk `{error: string, code: string}`.

| Status | Code | Makna |
|---|---|---|
| 400 | `invalid_request` | JSON rusak/non-object, field hilang, tipe/panjang salah, Unicode tidak valid atau body terlalu besar. Nilai input tidak dipantulkan. |
| 401 | `invalid_credentials` | Username/email tidak ditemukan/ambigu, password salah, nonaktif atau bukan staff. Pesan generik sama. |
| 403 | `csrf_failed` | Cookie/header CSRF hilang/tidak cocok atau origin tidak tepercaya. |
| 403 | `forbidden` | Pengguna bersesi tidak lagi memenuhi role Admin. |
| 415 | `unsupported_media_type` | Login tidak menggunakan JSON. |
| 429 | `rate_limited` | Percobaan masuk dibatasi. Jangan menganggap lockout permanen. |

Metode yang salah menghasilkan 405 native Django beserta `Allow`; body 405 tidak dijanjikan JSON. Error internal tak terduga tetap 500 generik native Django, bukan error kredensial palsu. Frontend harus menangani error non-JSON/network tanpa mengklaim login berhasil.

## Alur integrasi untuk koordinator Login FE

1. Pilih hostname konsisten. Development yang sesuai preview: frontend `http://127.0.0.1:62942` dan backend `http://127.0.0.1:8000`, atau `localhost` pada kedua sisi. Port boleh berbeda; jangan mencampur kedua hostname lalu melemahkan SameSite.
2. GET CSRF dengan `credentials: "include"`. Simpan token JSON hanya di memori halaman, bukan token sesi di localStorage.
3. POST login sebagai JSON, `credentials: "include"`, dan `X-CSRFToken` dari bootstrap. Jangan log password atau menaruhnya pada query string.
4. Login merotasi sesi/CSRF. Setelah sukses, ganti token CSRF di memori dengan `csrfToken` dari respons login. Token sebelum login tidak boleh digunakan untuk logout.
5. GET session untuk memulihkan status setelah reload. Halaman publik tetap tidak membutuhkan sesi.
6. POST logout memakai token terbaru dan credentials. Hapus state pengguna lokal setelah logout terkonfirmasi; cookie lama tidak boleh menjadi autentikasi lagi.
7. Pada `csrf_failed`, muat ulang bootstrap/form sesuai alur UX. Pada 429 tampilkan pesan tunggu generik; tidak ada countdown atau Retry-After yang dijanjikan, karena waktu tersisa tidak dihitung oleh API ini.

Jalur A tidak mengedit `frontend/src/api.ts` atau form Login. Login React masih disconnected sampai koordinator menyambungkannya pada branch FE fitur 1. API backend bekerja tidak sama dengan login browser end-to-end selesai.

## Sesi, cookie dan otorisasi

- Django auth dan database session native; tidak ada JWT atau implementasi hash password baru.
- Sinyal `user_logged_in` memberi expiry absolut 8 jam untuk Admin, baik login JSON maupun Django Admin bawaan. Membaca sesi tidak memperpanjang expiry. Autentikasi ulang adalah login baru.
- Django tetap memvalidasi status akun/session auth hash pada request berikutnya. Session API memeriksa role Admin kembali; pencabutan staff tidak memberikan akses dari state frontend lama.
- Cookie session/CSRF HttpOnly, SameSite=Lax. `Secure=True` saat `DEBUG=False`; HTTP development/test menggunakan override lokal yang eksplisit. Jangan memakai settings pengujian untuk produksi.
- CORS credentials hanya bersama allowlist eksplisit. Default development: localhost/127.0.0.1 port 5173 dan 62942. Default nondebug tidak mengizinkan origin mana pun sebelum konfigurasi.
- Konfigurasi `CORS_ALLOWED_ORIGINS` dan `CSRF_TRUSTED_ORIGINS` melalui environment untuk origin deployment sebenarnya. CORS bukan pengganti CSRF. Middleware CSRF tidak dinonaktifkan; halaman CSRF native Django Admin tetap dipertahankan.
- Traceback locals pada request auth/Admin login disensor melalui hook reporter Django, termasuk frame third-party. Ini tidak mengaudit semua proxy, layanan observability atau konfigurasi debug di deployment; jangan mengirim kredensial nyata ke alat debugging.

## Pembatasan percobaan dan retensi

- django-axes 9.0.0, handler database; 5 kegagalan dengan cooloff 15 menit.
- Counter berlaku per-IP dan identitas akun. Username/email alias akun yang sama memakai key HMAC canonical, bukan raw username/email. Pergantian User-Agent atau header X-Forwarded-For tidak boleh menghindari counter IP.
- Hanya REMOTE_ADDR yang dipercaya. Reverse proxy perlu konfigurasi tepercaya yang ditinjau tersendiri; tanpa itu beberapa pengguna dapat terlihat berasal dari IP proxy yang sama. Jangan langsung mempercayai header client.
- Percobaan selama lockout tidak memperpanjang cooloff; keberhasilan tidak otomatis menghapus seluruh riwayat kegagalan pada shared IP.
- Per-log sukses dan failure permanen dinonaktifkan. Counter agregat menyimpan IP, key HMAC, metadata terbatas dan timestamp; tidak menyimpan password JSON. Parameter sensitif form native juga dimask.
- Counter expired dibersihkan global pada kegagalan login berikutnya oleh Axes. Ini bukan jaminan penghapusan tepat saat batas 15 menit jika aplikasi tidak menerima traffic. Tidak ada scheduler baru yang diaktifkan.
- Uji yang dijalankan mencakup counter serial/multi-IP melalui API dan native Admin, bukan sertifikasi beban serentak multiworker atau proteksi DDoS. Shared-IP/account-lockout DoS tetap tradeoff kebijakan yang perlu ditinjau sebelum publikasi layanan.

## Environment dan pengujian lokal

Python perlu memenuhi persyaratan Django 6.1.2 (>=3.12); environment yang digunakan untuk verifikasi adalah Python 3.14.7 pada virtualenv branch ini.

Dari `backend/`, gunakan interpreter virtualenv dan manifest `requirements-auth.txt`. Manifest ini merujuk pin root serta menambahkan kebutuhan bootstrap yang sebelumnya tidak tercantum: corsheaders, environ, HTTPX, Axes, dan Ruff. Jangan memasang paket ke environment global atau virtualenv worktree lama.

`requirements-auth.lock` membekukan seluruh versi dari virtualenv yang benar-benar dipakai untuk verifikasi. Gunakan file itu untuk mereproduksi environment pengujian; tidak memuat paket Hermes, URL privat atau credential.

Untuk shell/operator yang mewarisi PYTHONPATH dari tool agent, bersihkan PYTHONPATH/PYTHONHOME dan nonaktifkan user site hanya pada proses verifikasi. Jangan mengubah PATH/config profil secara permanen. `python -I -m pip check` dapat dipakai untuk memastikan dependency virtualenv terisolasi.

Perintah tes, memakai executable virtualenv:

```text
python manage.py test admin_auth.tests --settings=backend.test_settings_auth --noinput -v 2
python manage.py check --settings=backend.test_settings_auth
python -m ruff check admin_auth backend/test_settings_auth.py backend/urls.py backend/settings.py
python -m ruff format --check admin_auth backend/test_settings_auth.py
python -I -m pip check
```

Gunakan environment test-only untuk `SECRET_KEY`, `DEBUG=False`, serta nilai kosong BPS_API_KEY/BPS_API_BASE_URL jika belum dikonfigurasi. Jangan mencetak atau mengambil secret dari `.env` existing. Tidak ada endpoint provider yang diperlukan oleh tes auth.

`backend.test_settings_auth` mengganti database menjadi SQLite memory milik test runner, origin test yang eksplisit dan cookie HTTP khusus pengujian. Test runner menerapkan migrasi auth/session/axes/indikator ke database uji ini; bukan ke database aplikasi existing. Fixture akun dan indikator sintetis hanya dibuat dalam tes. Tidak ada akun Admin default yang diprovisikan.

LiveServerTestCase menjalankan HTTP loopback nyata dan teardown server/database. CookieJar tidak menegakkan seluruh kebijakan browser SameSite, sehingga integrasi browser FE tetap harus diperiksa setelah wiring frontend.

Untuk development persisten nanti, gunakan database lokal baru yang dipilih secara eksplisit dan SECRET_KEY melalui mekanisme aman. Migrasi, akun operator dan konfigurasi deployment bukan alasan untuk memakai/mengubah database bersama atau mencetak kredensial.

## Batas verifikasi

Lihat `LOGIN_ADMIN_VERIFICATION.md` untuk hasil final dan cakupan sebenarnya. Bukti RED/GREEN dan log ada di `.test-artifacts/` yang diabaikan Git, bukan bagian source aplikasi.

Bug agregasi tren yang sudah ada pada baseline ditemukan ketika menambah uji publik: lihat [KNOWN_BASELINE_TREND_ISSUE.md](KNOWN_BASELINE_TREND_ISSUE.md). Tidak diperbaiki atau disembunyikan dalam branch Login. Uji auth pada PDB kuartalan tidak membuktikan seluruh mode agregasi atau kebenaran ekonomi live.

Belum ada commit, push, PR, deployment atau pengubahan frontend yang diotorisasi untuk jalur A ini.
