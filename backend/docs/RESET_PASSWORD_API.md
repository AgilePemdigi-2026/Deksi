# Reset Password Admin — backend v1 lokal

Tanggal: 3 November 2026. Lane: `feat/2-reset-password-be`, base Login BE `57608774398ee86f8eb8b60ce596ef71eefd6556`. Implementasi mengikuti target `DEKSI-RESET-1` pada lane FE `feat/2-reset-password-fe` (`1e86028748fbb9487d920bbd6f782cad1998196a`). Tidak menggabungkan kedua branch.

**Status: backend fungsional telah diuji lokal; bukan internet-facing/SMTP readiness.** Default aplikasi `ADMIN_PASSWORD_RESET_ENABLED=False`. Bahkan jika diaktifkan, fase ini hanya menerima mailer Django `locmem`, trusted frontend origin valid dan timeout 1800 detik. Console/SMTP ditolak dengan 503 sebelum lookup akun. Ini disengaja: console membocorkan isi email/token, sedangkan provider nyata dan strategi timing/delivery belum diotorisasi.

FE yang dipush sebelumnya tetap prototype dengan service tidak terhubung; file FE tidak diubah pada pekerjaan BE ini. HTTP backend PASS bukan bukti tombol reset FE sudah memakai API.

## Endpoint dan autentikasi

Semua request reset POST JSON membutuhkan CSRF cookie/header existing. Bootstrap: `GET /api/auth/csrf/`. Auth/session Login tidak diganti, tidak ada JWT/registrasi/auto-login baru.

| Endpoint | Body | Sukses |
|---|---|---|
| `/api/auth/password-reset/request/` | `email` | 202 `{code:"reset_request_accepted", accepted:true}` |
| `/api/auth/password-reset/check/` | `uid, token` | 200 `{valid:true}`; tidak mengonsumsi token |
| `/api/auth/password-reset/confirm/` | `uid, token, newPassword, confirmPassword` | 200 `{code:"reset_complete", authenticated:false}` |

Error: 400 `invalid_request`, `invalid_reset_link`, `password_validation_failed`; 403 `csrf_failed`; 405 `method_not_allowed`; 413 `request_too_large`; 415 `unsupported_media_type`; 429 `rate_limited`; 503 `reset_unavailable` pada jalur konfigurasi/storage/internal failure yang aman. Confirm 503 dapat berarti hasil tidak pasti; client tidak boleh auto-replay password. Request eligible/unknown/target-processing-failure tetap 202 generik setelah parsing/limiter; tidak menyatakan mail diterima inbox.

`password_validation_failed` memiliki `fields.newPassword`/`fields.confirmPassword` berupa array kode allowlisted. Native codes short/common/similar/numeric ditambah `password_unchanged`, `password_mismatch`; kode lain diganti `password_invalid`. Tidak meneruskan pesan/form/error exception mentah.

Reset response memakai `Cache-Control` no-store, `Referrer-Policy: no-referrer`, robots noindex/nofollow. Middleware existing diperluas khusus prefix reset agar penolakan CSRF juga mendapat header tersebut. Header hosting halaman FE adalah tanggung jawab integrasi/deployment yang berbeda.

## Kebijakan akun dan password

- Lookup menghitung semua akun dengan email setara NFKC+casefold, termasuk nonstaff/inactive/unusable; tepat satu kandidat diperlukan sebelum active+staff+usable diperiksa. Ambigu tidak memilih akun pertama. Schema User/email tidak diubah menjadi unique.
- Trim hanya whitespace luar email input. Tidak menambah aturan alias Gmail/dot/plus. Policy Unicode mengikuti perbandingan canonical yang diuji, tanpa mengandalkan case-insensitivity SQLite yang terbatas.
- Karena kolom canonical/unique email belum tersedia, lookup memindai akun dengan iterator dan berhenti pada dua match. Biaya O(jumlah akun) adalah **batas yang perlu ditinjau sebelum deployment publik**, bukan klaim scalable. Tidak menambahkan index/normalisasi User diam-diam.
- Native `PasswordResetTokenGenerator` dan `SetPasswordForm`/validators digunakan. `PASSWORD_RESET_TIMEOUT=1800` setelah pencarian tidak menemukan consumer reset lain dalam source proyek yang diperiksa. TTL tepat 1800 detik masih diterima; sesudahnya ditolak.
- New password berbeda dari current melalui native hasher check tanpa setter/upgrade hash. Unicode dan whitespace dipertahankan; tidak dibuat regex password FE/BE yang berbeda.
- Dua field password masing-masing maksimal 4096 karakter; email 254; uid/token 256 ASCII URL-safe. Body maksimum 16 KiB diperiksa terpisah: dua password Unicode atau JSON escaping dapat melewati body cap walau di bawah cap karakter. Tidak memotong nilai diam-diam.
- JSON duplicate keys, nonobject, missing/extra fields, invalid UTF-8/surrogate, recursion dan invalid field types ditolak aman.
- Native uid decode harus round-trip canonical dan merupakan positive PK yang dapat ditampung engine; tidak memperbaiki malformed token.

## Tautan dan email lokal

Origin hanya dari `ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN` yang dipercaya; tidak dari Host/Origin/forwarded header/next. HTTPS wajib untuk nonloopback; HTTP hanya localhost/127.0.0.1/::1. Origin tidak menerima userinfo/path/query/fragment/whitespace atau port malformed.

Email text/plain menggunakan template `admin_auth/password_reset_email.txt`: satu link `/admin/reset-password` dengan capability pada fragment, TTL 30 menit, instruksi abaikan bila bukan permintaan sendiri. Tidak mengirim password atau mengumumkan akun pada respons API. `locmem` tidak mengirim ke inbox dan hanya hidup di proses; tidak menulis email ke file/console.

Request baru tidak menjanjikan latest-only. Tautan yang masih valid bisa tetap berlaku hingga timeout/state berubah. GET scanner tidak mengubah password; API check POST adalah readonly. Setelah commit password berubah, native token lama tidak valid.

Exceptions pada target email/request ditangkap dengan acknowledgement generik dan log statis tanpa exception string/trace/capability. Internal check/confirm failure juga hanya log statis dan respons aman. Auth reporter existing tetap membersihkan frame locals; tes injected failures tidak menemukan marker sensitif pada response/log yang diperiksa. Ini bukan audit semua infrastruktur logging/provider/proxy.

## Limiter dan schema yang disetujui

Pengguna menyetujui satu tabel counter + file migrasi dan tes database terisolasi. `ResetRateBucket` menyimpan HMAC key, integer count dan indexed expiry saja, tanpa email/IP/token/password plaintext. User/role/email dan tabel Axes tidak diubah.

- Request IP: 20 per **jendela tetap 15 menit**.
- Identity email: 3/jendela; berlaku juga untuk unknown dan canonical aliases. Jika terlampaui tetap 202 generik dan tidak mengirim mail.
- Check+confirm berbagi satu bucket IP: 20/jendela; ganti endpoint tidak mereset kuota.
- IP dari `REMOTE_ADDR` yang divalidasi, bukan forwarded header bebas.
- Counter memakai update bersyarat `F(count)+1`, insert unique dan penanganan race di transaksi pendek. Bukan cache proses/LocMemCache.
- Cleanup opportunistic paling banyak 200 bucket expired per pemanggilan. Beban key dari botnet/retention skala produksi belum diuji.
- Fixed-window dapat menerima burst di perbatasan dua jendela; bukan sliding-window dengan jaminan untuk setiap interval 15 menit.
- Reset tidak memanggil signal login-failed, tidak menghapus lockout Axes dan tidak mengubah session policy Login.

Migration `admin_auth/0001_initial` dibuat dan diterapkan **hanya pada database test**. Tidak dijalankan pada `db.sqlite3` aplikasi, database bersama atau produksi. Jangan menjalankan `migrate` pada database pengguna sebagai bagian membaca petunjuk ini.

## Atomic confirm dan sesi

Password divalidasi oleh form native, lalu hash baru dibuat dengan native `set_password` melalui `form.save(commit=False)`. Conditional write mengikat PK, hash sebelumnya, email, last_login dan active/staff; hanya satu request dengan snapshot token-bound yang sama boleh mengubah row. Tidak mengandalkan `select_for_update` SQLite. Native validator `password_changed` dipanggil melalui on-commit hook setelah write berhasil; raw password dibersihkan dari atribut sementara user.

Cookie/session lama gagal pada request berikutnya karena session auth hash berubah; tidak memakai `update_session_auth_hash` atau auto-login untuk mempertahankan sesi. CAS hanya mengubah field password, bukan email/role/last_login. Role yang dicabut di antara validasi dan write mencegah commit.

Bukti concurrency berlaku pada **SQLite file-backed 3.53.1** dalam suite terpisah, bukan PostgreSQL/MySQL atau jaminan semua interleaving deployment. Tidak menambahkan database constraint unique-email: perubahan email/pendaftaran lain harus tetap dikelola tim; ekuivalensi email lintas-row bukan constraint atomik baru.

## Perintah verifikasi yang benar-benar dijalankan

Cwd: `backend/` pada worktree BE fitur 2. Gunakan interpreter venv existing Login BE `E:/Deksi-Team/.hermes/worktrees/feature-1-login-be/backend/.venv/Scripts/python.exe`; tidak perlu memasang paket baru. Berikut `python` berarti interpreter tersebut, bukan pip/global Python lain.

```text
python manage.py test admin_auth.tests --settings=backend.test_settings_reset --noinput -v 2
python manage.py check --settings=backend.test_settings_reset
python manage.py makemigrations --check --dry-run --settings=backend.test_settings_reset
python -m ruff check admin_auth backend/test_settings_auth.py backend/test_settings_reset.py backend/test_settings_reset_concurrency.py backend/urls.py backend/settings.py
python -I -m pip check
```

Concurrency **tidak termasuk autodiscovery `test*.py`**. Set `HERMES_TEST_SCRATCH` ke scratch yang disetujui dan `DEKSI_RESET_TEST_DB` ke path baru milik tes bernama `reset-concurrency-*.sqlite3` di bawah scratch itu; lalu:

```text
python manage.py test admin_auth.tests.reset_concurrency --settings=backend.test_settings_reset_concurrency --noinput -v 2
```

Runner memakai file DB sementara; path divalidasi, koneksi thread ditutup di finally, test database dihapus sesudah suite. Jangan menunjuk file yang sudah digunakan proses/user lain. Bukti command/interpreter/path aktual tersimpan di `.test-artifacts/reset-password/` yang di-ignore.

## Gate yang belum selesai

- FE HTTP adapter dan actual form Chrome→BE reset belum dikerjakan; tidak ada perubahan pada lane FE.
- SMTP/provider/sender/domain/inbox dan deliverability tidak diuji atau diotorisasi.
- Synchronous target processing dapat berbeda timing antara eligible/unknown; **belum privacy-safe untuk internet**. Dibutuhkan keputusan dan pengujian async/shared delivery, bukan sleep/dummy send/thread per-request. Tidak menambah outbox/worker/Redis/Celery pada scope ini.
- Trusted proxy, hosting no-referrer/no-store, HTTPS dan load/engine produksi belum diverifikasi.
- Commit/push/PR/merge/deploy memerlukan izin tersendiri. Runtime default tetap fail-closed; jangan menyebut fitur publik aktif dari tes lokal.

Rincian hasil: [RESET_PASSWORD_VERIFICATION.md](RESET_PASSWORD_VERIFICATION.md). Known baseline trend defect tetap terpisah pada [KNOWN_BASELINE_TREND_ISSUE.md](KNOWN_BASELINE_TREND_ISSUE.md); tidak diperbaiki dalam branch auth/reset.
