# Backend Sprint 1 — kandidat gabungan lokal

## Lokasi dan status

- Worktree: `E:/Deksi-Team/.hermes/worktrees/sprint-1-unified-be`.
- Branch: `integration/sprint-1-unified-be`.
- Parent Git: BE7 `5c9e20de5d71d74d2c9aabcf00dbf85d04ee8fe3`.
- Overlay publik: source backend lengkap dari `sprint-1-dashboard-be`, termasuk perubahan noncommitted Batch 1, bukan hanya HEAD branch.
- Overlay auth: delta backend checkpoint Reset `a99830be1f6c877dd79feb704db191231afe0c7b`, yang mewarisi Login `57608774398ee86f8eb8b60ce596ef71eefd6556`.
- Kandidat awal dibentuk sebagai overlay uncommitted. Pengguna kemudian mengizinkan audit cepat, commit dan push **branch integrasi ini saja**. Sesudah checkpoint integrasi diterbitkan, checkout branch membawa source gabungan; gunakan SHA/ref Git aktual untuk memastikan checkpoint, bukan HEAD parent BE7 di atas. PR dan merge branch tim tetap membutuhkan izin terpisah.
- Worktree publik Batch 1 dan auth asli dipertahankan. Source hashes baseline tersimpan di `.artifacts/sprint1-unified/sources-before.json`.

## Cakupan delapan fitur Sprint 1

| Fitur | Implementasi existing yang disatukan |
|---|---|
| 1 Login Admin | `admin_auth/`, API `/api/auth/`, native Django Admin, account/role/session/Axes policy |
| 2 Reset Password Admin | Request/check/confirm reset, native token, limiter/CAS, invalidasi sesi |
| 3 Ringkasan | `/api/indicators/`, nilai terpublikasi dan review boundary |
| 4 Grafik | `/api/indicators/<code>/trend/`, presisi/provenance seri |
| 5 Filter | `/api/indicators/dashboard/`, `/api/indicators/categories/` |
| 6 Detail | Resource ringkasan/histori existing; tidak menambah endpoint `/detail/` fiktif |
| 7 Source Trace | `/api/indicators/<code>/source-trace/` dan RAW download berizin publikasi |
| 8 Feedback | POST `/api/feedback/`, bootstrap GET `/api/feedback/categories/`, moderasi Admin |

Katalog/manajemen sumber Sprint 2 tidak ditambahkan. Integrasi mempertahankan file source publik dan auth; titik penyatuan konfigurasi adalah `backend/settings.py`, `backend/urls.py`, dan union `.gitignore`. Riwayat migrasi existing dipertahankan; merge migrasi indikator Batch 1 ikut disalin.

## Konfigurasi dan batas aktivasi

**Reset tetap disabled pada settings aplikasi biasa.** Source existing sengaja menolak SMTP/console; uji lokal mengaktifkannya hanya dengan mail backend locmem. Ini implementasi lokal yang dapat diuji, bukan fitur pengiriman email produksi yang telah aktif. Tidak ada provider/email nyata, AI, instalasi paket, migrasi DB kerja, .env atau data resmi yang digunakan.

`backend.test_settings_sprint1` mewarisi test settings Reset yang memakai konfigurasi aplikasi aktual: semua app, URL, middleware keamanan dan authentication backends tergabung. Override hanya mengisolasi database SQLite memory, cookie/origin localhost, log dan email locmem; RAW dibatasi ke task-owned scratch. Settings menolak keberadaan `.env` di worktree kandidat sebelum mengimpor baseline.

Untuk menjalankan suite gabungan, dari `backend/` dengan interpreter existing yang telah diverifikasi:

```text
manage.py test admin_auth.tests indicators.tests --settings=backend.test_settings_sprint1 --noinput -v 2
```

Diperlukan environment test-only: `SECRET_KEY` sintetis, `DEBUG=False`, `BPS_API_KEY` kosong, `HERMES_TEST_SCRATCH` menunjuk scratch yang diizinkan dan `DEKSI_TEST_RAW_ROOT` menunjuk direktori milik test di bawahnya dengan prefix `sprint1-unified-`. Jangan menunjuk data kerja atau menyalin credential. Runner verifikasi lokal dengan environment eksplisit disimpan di `.artifacts/sprint1-unified/run_verification.py`; file ini adalah artifact lokal, bukan perintah deployment.

Concurrency menggunakan suite eksplisit `admin_auth.tests.reset_concurrency` dengan `backend.test_settings_reset_concurrency` dan database `reset-concurrency-*.sqlite3` di scratch. Suite ini tidak ikut default `test*.py` discovery.

## Handoff session frontend

- Session frontend tetap pemilik eksklusif `frontend/` dan port Prototype 2. Kandidat ini tidak mengubah frontend atau reference prototype.
- Backend Batch 1 tetap referensi yang tidak disentuh selama penyatuan; jangan mengganti runtime session frontend secara diam-diam.
- Kontrak publik tidak berubah: lihat [kontrak dashboard Batch 1](../dashboard-foundation/README.md), [Login](../LOGIN_ADMIN_API.md), dan [Reset](../RESET_PASSWORD_API.md).
- Bootstrap feedback dari `/api/feedback/categories/` mengembalikan `csrfToken` dan cookie. Kirim cookie + header `X-CSRFToken`; cookie CSRF sekarang HttpOnly mengikuti konfigurasi auth. Jangan membacanya dari `document.cookie`.
- Login merotasi CSRF: token feedback sebelum Login harus dianggap kedaluwarsa. Gunakan token respons Login atau bootstrap ulang feedback setelah pergantian status auth. Jangan mematikan CSRF atau menyimpan token auth ke localStorage.
- Origin FE aktual perlu masuk allowlist CORS/CSRF secara eksplisit. Test origin `62944` bukan izin CORS global atau keputusan port frontend produksi.
- Uji browser–React terhadap kandidat ini dan human visual acceptance tetap pekerjaan integrasi frontend, terpisah dari tes HTTP backend.

## Bukti verifikasi

Regresi gabungan aktual: **177 tes, 176 PASS dan 1 SKIP** (izin symlink Windows). Concurrency reset eksplisit: **3 PASS**. Check Django, migration drift dan dependency check lulus. Hasil awal empat tes gabungan, termasuk socket HTTP localhost, tersedia di `.artifacts/sprint1-unified/combined-smoke.log`; empat tes tersebut juga ikut suite 177, bukan tes unik tambahan. Baca [verifikasi](VERIFICATION.md) dan receipt source-hash. Jangan menganggap bukti historis di dokumen fitur/Batch 1 sebagai hasil kandidat gabungan yang baru.

Pengguna juga mengizinkan `.hermes/environment.json` khusus worktree ini. Recipe memakai `backend/scripts/verify_sprint1.py`: bootstrap hanya mengecek runtime/dependensi/port, build menjalankan lint/check/drift, test menjalankan suite gabungan dan concurrency, start menjalankan WSGI loopback dengan DB memory yang dimigrasikan di proses yang sama. Server memiliki timer shutdown 20 detik. Hasil kanonik aktual berada di `.artifacts/sprint1-unified/canonical-full-final.json`; bila berkas belum ada atau `ok` bukan true, jangan menganggap verifikasi kanonik selesai.

Batas lint: migration tim `indicators/migrations/0004_feedback_model.py` dipertahankan byte-identical; pemeriksaan luas menemukan tujuh issue gaya existing pada file tersebut. Lint terarah source auth/integrasi publik/new tests lulus tanpa mematikan rules. Ini bukan klaim seluruh repository bebas lint.
