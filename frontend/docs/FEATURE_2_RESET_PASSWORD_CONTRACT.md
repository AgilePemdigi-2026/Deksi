# Fitur 2 — kontrak Reset Password Admin v1

Tanggal: 3 November 2026. Versi: **DEKSI-RESET-1 — untuk review, belum API implementasi**.

Dokumen ini menetapkan bentuk payload dan pemetaan state untuk tahap selanjutnya, bukan bukti endpoint/email sudah berfungsi. Base FE: `c288b46128db918d2d2965b72ec599d6cbe6e768`; base BE kandidat: `57608774398ee86f8eb8b60ce596ef71eefd6556`. Lane FE saat ini `feat/2-reset-password-fe`. Implementasi BE, schema/migrasi limiter atau outbox, provider email dan deployment belum diotorisasi pada batch ini.

Fixture mesin: [password-reset.contract.json](../tests/fixtures/password-reset.contract.json). Semua identitas/password/capability di fixture adalah placeholder sintetis, bukan hasil API. Pengujian keselarasan fixture tidak membuktikan implementasi backend.

## Halaman dan pemisahan runtime

- `/admin/forgot-password`: email → permintaan diterima generik, kirim ulang, ubah email, kembali Login.
- `/admin/reset-password`: pemeriksaan capability → dua password → selesai, atau tautan tidak dapat digunakan. Loading/error adalah variant, bukan route baru.
- `/admin/login`: tautan Lupa kata sandi menuju forgot. Login API/session existing tidak diubah.
- Interface UI `RecoveryService` memiliki `request(email, signal?)`, `check({uid, token}, signal?)`, `confirm(credentials, newPassword, confirmPassword, signal?)`, seluruhnya `Promise<void>`.
- **Adapter HTTP reset belum dibuat.** Default `unavailableRecovery` selalu menolak `not_connected`. Hanya `tests/recovery-preview/entry.tsx` menginjeksi service sukses sintetis. Fixture tidak menjadi fallback runtime dan tidak diimpor entry produksi.

## Payload HTTP v1 yang ditargetkan

Semua POST menggunakan JSON, CSRF cookie/header existing fitur 1, cookie credentials dan origin allowlist eksplisit. CSRF bootstrap tetap `GET /api/auth/csrf/`. Tidak ada JWT, registrasi publik atau profil akun pada response reset.

| Endpoint POST | Body | Response sukses |
|---|---|---|
| `/api/auth/password-reset/request/` | `{email}` | 202 `{code:"reset_request_accepted", accepted:true}` |
| `/api/auth/password-reset/check/` | `{uid, token}` | 200 `{valid:true}` |
| `/api/auth/password-reset/confirm/` | `{uid, token, newPassword, confirmPassword}` | 200 `{code:"reset_complete", authenticated:false}` |

202 hanya mengakui permintaan diproses secara generik, **bukan** konfirmasi email terdaftar, antrean berhasil atau email sampai. Unknown, nonstaff, inactive, unusable password, email ambigu dan identity throttled memiliki bentuk/status sama. Kegagalan target-specific tidak boleh menghasilkan 503 yang hanya terlihat untuk akun eligible. Status 503 `reset_unavailable` hanya untuk outage global yang diketahui tanpa membedakan akun.

Error: 400 `invalid_request` / `invalid_reset_link` / `password_validation_failed`; 403 `csrf_failed`; 413 `request_too_large`; 415 `unsupported_media_type`; 429 `rate_limited` untuk IP; 503 `reset_unavailable`. Error tidak memuat `detail` exception, email/user ID/token atau password.

Field validation menggunakan `fields: {newPassword?: string[], confirmPassword?: string[]}` dengan **kode**, bukan pesan mentah: `password_too_short`, `password_too_common`, `password_too_similar`, `password_entirely_numeric`, `password_unchanged`, `password_mismatch`. Client memetakan allowlist ke bahasa Indonesia; unknown code menjadi pesan generik. HTML/non-JSON/response oversize/bentuk tidak sesuai tidak boleh dianggap sukses. Promise sukses adapter kelak hanya setelah status dan schema sukses cocok.

## Batas input

Usulan yang perlu diwujudkan/dibuktikan di BE: JSON body maksimum 16 KiB; email maksimum 254 karakter; uid/token masing-masing 1–256 karakter ASCII `[A-Za-z0-9_-]`; password masing-masing maksimum 4096 karakter, tanpa trim. Body-byte cap berlaku lebih dahulu dan independen dari cap karakter: dua password panjang, Unicode dan JSON escaping dapat melampaui 16 KiB walau masing-masing field di bawah 4096. Tampilkan error input aman, bukan memotong password. FE tidak menyalin password policy menjadi regex/min-length baru.

Trim hanya whitespace luar email yang dimasukkan pengguna. Perbandingan email BE harus konsisten dengan policy native yang disepakati (case-insensitive dan penanganan Unicode diuji), jangan menambah normalisasi Gmail/dot/plus yang dapat menggabungkan akun berbeda. Hitung seluruh kandidat sebelum memeriksa role. Jika lebih dari satu kandidat, fail closed; jangan memilih akun staff pertama atau memigrasikan email menjadi unique diam-diam.

## Kebijakan yang direkomendasikan, belum pengaturan aktif

- Tepat satu kandidat email, kemudian `is_active && is_staff && has_usable_password()`. Periksa ulang saat check dan commit.
- Native Django `PasswordResetTokenGenerator`, form/set-password dan validators; TTL usulan **1800 detik**. Tinjau semua consumer `PASSWORD_RESET_TIMEOUT` sebelum memilih setting global atau generator terarah.
- Password baru berbeda dari password saat ini melalui `check_password` setelah capability valid; bukan menambahkan password-history framework.
- Check tidak mengonsumsi token. GET/scanner tidak mengubah state. Password berubah hanya setelah confirm commit.
- Request ulang tidak menjamin latest-only. Semua token yang masih valid dapat berlaku sampai expiry/perubahan state; commit password membatalkan token lama.
- Setelah commit tidak auto-login dan tidak mempertahankan sesi lama dengan `update_session_auth_hash`. Password lama dan cookie lama harus ditolak pada request berikutnya oleh API serta Django Admin.
- Axes Login tetap independen; reset tidak menghapus lockout, mengubah role/email atau mengunci akun melalui `user_login_failed` palsu.

## Link dan email contract

Link yang direncanakan: origin FE HTTPS dari konfigurasi server tepercaya + `/admin/reset-password` + fragment berisi uid/token. **Bukan** origin dari request Host/Origin/next. FE mengambil capability ke memori lalu `replaceState`, mengirimnya hanya dalam POST body ketika adapter nyata tersedia. Fragment baru pada page yang sama harus diperiksa ulang dan membersihkan input lama. Malformed/duplicate/extra fragment fields ditolak, bukan diperbaiki. Tidak menulis capability/password/email ke browser storage atau console. Reload sesudah fragment dibersihkan meminta membuka ulang email; ini batas yang disengaja, bukan alasan menyimpan token.

`Referrer-Policy: no-referrer`, `Cache-Control: no-store`, robots noindex dan tidak ada script/tracker pihak ketiga wajib diwujudkan pada hosting FE/BE nyata. **Saat ini header itu hanya dipasang server harness preview**, bukan perubahan konfigurasi deployment produksi. Fragment tidak menjamin token hilang dari ekosistem email, perangkat atau history sebelum JavaScript aktif. Kompatibilitas email-client/history/back memerlukan tes gabungan tersendiri.

Tahap awal yang direkomendasikan: Django locmem **MAILERS** dan DB terisolasi; jangan memakai console mailer karena isi reset email/token akan masuk terminal. Baca outbox in-process tanpa mengarsip capability mentah. Email text/plain wajib: pengirim DEKSI yang dikonfigurasi, subject jelas, satu link pemulihan, TTL 30 menit bila nilai itu sudah diterapkan, instruksi abaikan bila bukan permintaan sendiri dan jalur bantuan operator. Notifikasi sesudah perubahan direkomendasikan tanpa password; delivery notification belum diputuskan. Real sender/domain/provider/SMTP dan inbox test merupakan gate terpisah; tidak meminta credential di chat.

## Limiter, timing dan concurrency — gate keputusan

**Belum ada izin schema/migrasi baru, queue/worker atau dependency. Jangan mengklaim kontrak ini mengaktifkan proteksi.** Rekomendasi sebelum Batch 3:

1. Reset limiter terpisah: request IP 20/15 menit; identity-email 3/15 menit dengan HMAC canonical email untuk alamat eligible maupun unknown dan respons tetap 202; check+confirm 20/15 menit per-IP. Jangan percaya forwarded header tanpa trusted proxy. UI resend/pending hanya UX, bukan security limiter.
2. Cari datastore bersama yang sudah disetujui. Jika tidak ada, minta persetujuan tabel counter minimal berindeks unique scope/key/window, key HMAC, counter atomik serta cleanup terbatas; jangan diam-diam memakai LocMemCache sebagai perlindungan multiworker atau memperkenalkan Redis/Celery. **Pilihan schema tetap pending review, belum dibuat.**
3. Timing enumeration produksi tidak selesai dengan response generik atau sleep tetap. Rekomendasi produksi adalah outbox/worker shared yang benar-benar dijalankan dan diukur; itu perlu keputusan schema/ops terpisah. Untuk scope awal tetap local-only/locmem, label internet-facing readiness BLOCKED. Tidak memulai worker/thread background per-request atau mengirim email dummy.
4. Target atomic confirm: dua request valid untuk token sama tepat satu commit. Revalidasi account/token di transaction dan gunakan locking/CAS yang efektif pada engine aktual, menjaga native password lifecycle dan predicate state terkait token. Jangan mengandalkan `select_for_update` SQLite sebagai row lock. Implementasi dan tes dengan barrier dua koneksi/engine aktual wajib sebelum menyebut race-safe. Engine dan primitive akhir ditentukan setelah inspeksi BE Batch 3, bukan klaim sudah selesai di prototype.

Jika local-only test implementation dengan mitigasi produksi belum aktif dipilih, laporan harus membedakan PASS fungsional lokal dari limiter/timing/SMTP yang belum siap. API local-only tidak boleh dipromosikan menjadi public deployment tanpa gate ini.

## Pemulihan saat gagal

- UI validasi email/mismatch hanya untuk usability; server memvalidasi lagi.
- Disable kontrol ketika pending dan gunakan synchronous in-flight ref agar double submit tidak menggandakan request.
- CSRF/rate-limit memiliki pesan aman; retry selalu tindakan eksplisit, tidak otomatis mengirim password ulang.
- Confirm network/HTML/5xx/invalid schema berarti hasil **tidak pasti**, bukan pasti gagal. Kunci submit ulang; tawarkan Login/Minta tautan baru. Jangan auto-login atau mengumumkan password berubah tanpa response commit terkonfirmasi.
- Abort/unmount/fragment baru membatalkan handler dan membersihkan state UI. Abort bukan rollback server; adapter nyata harus mempertahankan perbedaan itu.
- Tidak meneruskan raw server error ke UI. Exception reporter, provider log dan retained receipts wajib diperiksa terhadap jalur reset baru sebelum backend selesai.

## Acceptance dan batas bukti

Fixture memuat N01–N16 sebagai **kasus kontrak, bukan test backend yang sudah PASS**. Matrix F2-01…F2-18 di rencana induk tetap berlaku. Prototype menguji route, validation/focus, accepted/success/error state sintetis, fragment parsing/cleanup, show-hide, duplicate guard, responsive dan navigasi. Eligibility, native token expiry, throttling shared, atomic commit, session invalidation, log redaction, email locmem dan real inbox **NOT RUN untuk fitur 2**.

Gate berikut: review visual dua halaman/lima state, persetujuan contract/policy dan pilihan mitigasi limiter/timing untuk scope BE. Backend branch/adapter nyata, layanan email dan publication tidak otomatis diizinkan oleh file ini.
