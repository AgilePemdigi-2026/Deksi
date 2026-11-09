# Reset Password Admin — verifikasi BE lokal

Tanggal: 3 November 2026. Branch `feat/2-reset-password-be`, base `57608774398ee86f8eb8b60ce596ef71eefd6556`. Snapshot ini **belum commit/push/PR/merge**. [Kontrak dan batas operasi](RESET_PASSWORD_API.md).

## Hasil aktual

| Pemeriksaan | Hasil | Cakupan |
|---|---|---|
| `manage.py test admin_auth.tests --settings=backend.test_settings_reset --noinput -v 2` | **74 PASS**, exit 0 | 47 existing auth + 27 reset, termasuk HTTP localhost nyata; bukan seluruh suite indikator/proyek |
| Suite eksplisit `admin_auth.tests.reset_concurrency` dengan settings file DB scratch | **3 PASS**, exit 0 | SQLite file-backed, thread/koneksi terpisah; suite ini tidak ikut default discovery `test*.py` |
| Penambahan kontrol validator similarity | **PASS**, targeted rerun | Menambah input username-similar pada satu test yang sudah PASS; tidak menambah jumlah test unik |
| Penambahan kontrol dua sesi API/Admin independen | **PASS**, targeted rerun | Sesi Admin diperiksa terpisah dari sesi API agar flush satu cookie tidak menjadi bukti palsu untuk yang lain |
| Ruff check | **PASS**, exit 0 | Admin auth, settings/URL terkait; tidak menonaktifkan rules |
| Ruff format check | **PASS**, 13 file | File Python baru serta middleware yang disentuh; tidak memformat ulang settings/URL legacy |
| Django check | **PASS**, 0 issues | Test settings terisolasi |
| Migration drift check | **PASS**, no changes detected | `makemigrations --check --dry-run`, bukan migrate DB aplikasi |
| `pip check` | **PASS** | Runtime existing Login BE; tidak memasang dependency |
| AST parse + `git diff --check` | **PASS** | Semua Python changed/new dan whitespace Git |
| Protected worktrees | **PASS** | Login BE, reset FE published dan checkpoint React6/7 tetap HEAD yang dipin dan bersih |
| Cleanup test DB | **PASS** | File concurrency scratch dan sidecar tidak tersisa; proses tes/LiveServer selesai |

Total test **unik 77**: 74 suite auth/reset + 3 concurrency. Rerun bukan test unik tambahan. Dua kontrol diperluas sesudah full suite terakhir; app code tidak berubah dan kedua method terkait dijalankan ulang PASS. Tidak mengklaim seluruh suite 74 dieksekusi ulang setelah perubahan test-only tersebut.

Runtime: Python 3.14.7, Django 6.1.2, SQLite 3.53.1. Interpreter: venv existing pada lane Login BE, dipanggil eksplisit; PYTHONPATH/PYTHONHOME inherited dibersihkan dan usersite dimatikan pada runner. Peringatan import dari editor yang tidak memakai interpreter ini bukan hasil tes runtime.

## Jalur yang benar-benar dieksekusi

- Request valid → 202 generik → satu email locmem dengan trusted fragment link; tidak memakai SMTP atau console.
- Unknown, inactive, nonstaff, unusable dan duplicate lintas-role/Unicode → tidak mengirim mail. Tidak memilih staff pertama jika ada kandidat lain.
- Case aliases dan whitespace luar email berbagi identity limit. Unknown identities tetap terkena IP limit; forwarded header tidak dapat mengganti IP.
- Readonly check berulang dan GET/method rejection tidak mengonsumsi native token. Expiry diuji dengan controlled clock pada/sesudah 1800 detik tanpa sleep.
- Native short/common/similar/numeric/mismatch dan unchanged password ditolak sebagai kode aman. Unicode dan whitespace password dipertahankan. Body-byte cap terpisah dari field-character cap.
- Confirm → native hashed password berubah; password lama gagal; tidak auto-login; replay/check token lama ditolak. Dua sesi lama independen ditolak melalui API dan Django Admin.
- Dua request confirm HTTP-stack Django client serentak pada dua koneksi SQLite file: **tepat satu 200, satu 400**; hanya password pemenang berlaku dan native password_changed hook terpanggil sekali.
- Delapan koneksi mengambil kuota identity dengan limit 3: **tepat tiga diterima**, persisted count 3. Jendela tetap berganti dan cleanup maksimum 200 expired buckets dibuktikan.
- Role dicabut antara validation dan CAS: tidak ada perubahan password. Host yang diizinkan hanya untuk skenario test tidak mengontrol origin link; konfigurasi production allowlist tidak dilonggarkan.
- CSRF/cross-origin, JSON/type/size/UTF-8/surrogate/duplicate-key/recursion/method/media errors, global disabled/mail configuration, safe failure response/log dan privacy headers termasuk penolakan CSRF diuji.
- **HTTP socket nyata localhost:** Login lama → request reset → baca outbox in-process → check link → confirm → old cookie/password ditolak → Login password baru berhasil. Ini bukan Chrome actual form FE.

## Perbaikan dari RED yang dipertahankan

1. Request/check/confirm awalnya 404; tracer perilaku masing-masing menjadi GREEN.
2. Tanpa limiter, mail keempat masih dikirim dan request IP ke-21 tetap 202. Counter HMAC shared memperbaiki kedua reproduksi.
3. Error input khusus semula tertangkap lagi sebagai ValueError generik: 413 menjadi 400 dan invalid_reset_link menjadi invalid_request. Penanganan subtype diperbaiki; dua reproduksi PASS.
4. Penolakan CSRF semula menggunakan Referrer-Policy same-origin. Middleware khusus prefix reset memperbaikinya ke no-referrer/no-store/noindex.
5. Percobaan test Host pertama ditolak ALLOWED_HOSTS (400) sebelum mencapai skenario link. Fixture diubah dengan allowlist **test-only**, bukan melonggarkan aplikasi.
6. Ruff awal gagal pada format/import/unused code dan idiom class attribute migration. Diperbaiki terarah pada file baru, dengan ClassVar pada migration, tanpa menghapus aturan lint. Failure log awal tetap disimpan.

## Requirement → bukti dan batas

| ID induk | Status tahap BE |
|---|---|
| F2-01 Entry/navigasi | FE belum dihubungkan; bukan acceptance BE |
| F2-02 Input | BE PASS untuk kasus yang tercantum; FE tetap prototype |
| F2-03 Eligibility | BE PASS pada fixtures unique/role/Unicode/ambiguous |
| F2-04 Privacy | Injected response/log cases PASS; proxy/provider/log deployment belum diaudit |
| F2-05 Throttling | SQLite shared atomic counter PASS; distributed production/load belum diuji |
| F2-06 Native token | Native expiry/replay/state/malformed cases PASS |
| F2-07 Link safety | BE origin/fragment/header/method cases PASS; FE hosting/history/email-client compatibility pending |
| F2-08 Password policy | Native validator codes, unchanged, mismatch, whitespace/Unicode dan limits PASS |
| F2-09 Atomicity | Dua koneksi SQLite tepat satu commit PASS; engine lain dan seluruh interleaving tidak diklaim |
| F2-10 Session | Old password dan dua sesi API/Admin independen ditolak; tidak auto-login PASS |
| F2-11 Recovery | BE codes/CSRF/rate/safe failure PASS; timeout/HTML/retry adapter FE belum dibuat |
| F2-12 Abuse | Source reset tidak mengubah Axes/role/email, regresi Login PASS; bukan bukti seluruh kombinasi lockout/reset |
| F2-13 Mail | Locmem + real HTTP PASS; notifikasi sesudah perubahan dan actual form FE belum dikerjakan |
| F2-14 UI | Tidak diubah; acceptance visual tetap terpisah |
| F2-15 Responsive | Tidak diuji ulang di tahap BE |
| F2-16 Regression | 47 auth existing PASS, protected paths/worktrees terjaga; tidak mengklaim dataset/chart live benar |
| F2-17 Production privacy | **BLOCKED**: timing synchronous email, worker/shared delivery, proxy/hosting/load dan gate produksi belum diselesaikan |
| F2-18 Real mail | **NOT RUN**, tidak diotorisasi |

Lensa kualitas: security pada token/privacy/limiter; reliability pada atomicity/error; compatibility pada regresi Login dan FE contract; maintainability pada fasilitas native/no dependency baru. Bukan sertifikasi ISO/security audit menyeluruh.

## Bukti dan aturan handoff

Logs RED/GREEN, final commands/exit codes dan source hashes disalin ke `.test-artifacts/reset-password/` (di-ignore). Tidak mengarsip raw link/uid/token/cookie runtime; source hanya memiliki fixture sintetis. Receipt menyebut cakupan dan gate, bukan menandai canonical Hermes verification sebagai full PASS.

File migration adalah deliverable source yang diizinkan, bukan bukti migration dijalankan pada database pengguna. Tidak ada `db.sqlite3`, `.env` atau venv baru pada worktree BE ini. Tidak ada FE/indikator/requirements/provider/model/profile changes.

**Tersisa:** audit/publikasi sesuai izin baru; FE HTTP adapter dan tes actual form; email provider/inbox serta solusi timing dan penilaian deployment. Default reset tidak diaktifkan secara diam-diam. Tidak ada server QA persisten baru setelah test selesai.

## Perbaikan lanjutan — validasi alamat frontend

Audit lanjutan menemukan bahwa bagian akun URL yang kosong dan port 0 belum ditolak oleh validator origin. Solusi terarah: cek keberadaan username/password dengan `is not None`, serta izinkan port eksplisit hanya 1–65535. Tidak menambah parser/dependency atau mengubah FE/SMTP/schema.

- RED aktual: 2 test dijalankan, dengan 4 subtest gagal karena konfigurasi salah masih mendapat 202, bukan 503. Bukti awal disimpan.
- GREEN terbaru: **29 tes reset PASS**, mencakup dua test baru dan alur locmem → reset → Login melalui HTTP nyata. Enam konfigurasi invalid ditolak sebelum lookup akun; tujuh origin valid/batas port tetap diterima.
- Ruff check, format check dua file kode, dan Django check terbaru PASS. Pengujian memakai database terisolasi; tidak ada migrasi database pengguna.
- Suite 74 dan concurrency 3 pada tabel sebelumnya adalah bukti tahap sebelum perbaikan ini; bukan klaim dijalankan ulang sekarang. Dua test baru menambah koleksi reset dari 27 menjadi 29. Regresi Login existing dan algoritma concurrency tidak diubah atau dihitung sebagai eksekusi baru.
- Receipt dan log lanjutan berada di `.test-artifacts/reset-password/origin-validation-fix/`; receipt baseline dipertahankan sebelum snapshot aktif diperbarui. Commit/push/PR tetap belum dilakukan.
