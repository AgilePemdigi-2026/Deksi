# Fitur 2 — integrasi Reset Password FE–BE

Tanggal: 3 November 2026. **Status: form React terhubung ke Django dan lulus integrasi lokal terisolasi. Bukan SMTP/produksi readiness.**

## Kandidat dan perubahan

- FE: `feat/2-reset-password-fe`, basis prototype `1e86028748fbb9487d920bbd6f782cad1998196a`. Laporan ini mencatat verifikasi kandidat sebelum publikasi; identitas commit/status push dibuktikan lewat riwayat branch dan receipt publikasi, bukan diasumsikan dari dokumen ini.
- BE: `feat/2-reset-password-be`, `a99830be1f6c877dd79feb704db191231afe0c7b`, source tidak diubah.
- `src/App.tsx` sekarang memasok `createRecoveryClient(authOrigin())` ke kedua halaman recovery. Konfigurasi origin mengikuti Login (`VITE_AUTH_API_ORIGIN`); cookie credentials, CSRF dan origin allowlist tetap aktif. Tidak menggabungkan branch atau menyalin source BE ke FE.
- Client baru memeriksa pasangan HTTP status/payload untuk request/check/confirm, membatasi body JSON 16 KiB, menangani deadline termasuk stream, membatalkan operasi dan tidak otomatis mengulang password POST.
- Field error hanya memakai kode allowlisted. Respons HTML, malformed/oversize/invalid UTF-8, status/schema salah dan hasil confirm ambigu tidak menjadi sukses.
- Copy yang sebelumnya mengklaim semua pemulihan belum terhubung diperbarui tanpa perubahan desain. HTML aplikasi memakai meta `no-referrer`; header hosting produksi belum diverifikasi.
- Service sukses sintetis tetap terbatas pada preview test. Skenario `disconnected-preview` menginjeksi service unavailable secara eksplisit, bukan mengganti runtime normal. Fixture kontrak lama tetap contoh historis, bukan hasil API nyata.

## Verifikasi yang dieksekusi

Cwd semua perintah FE: `frontend/` pada worktree fitur 2.

| Pemeriksaan | Hasil | Batas bukti |
|---|---|---|
| `npm test` | 46 tes PASS, exit 0 | 31 existing + 15 client reset, transport sintetis/unit/SSR |
| `npm run test:browser` | PASS, exit 0 | Regresi UI dashboard/Login/reset memakai harness sintetis; bukan bukti BE |
| `npm run test:integration:reset` | 2 tes PASS, exit 0 | Chrome asli + React normal + Django nyata, tanpa interception atau injected successful service |
| `npm run test:integration:login` | 4 tes PASS, exit 0 | Regresi form Login asli, penolakan role/password/CSRF/lockout, reload, logout dan duplicate guard |
| `npm run build` | PASS, exit 0 | TypeScript + Vite; warning bundle >500 kB tetap ada |
| `npm run lint` | 0 error, 3 warning, exit 0 | Warning existing EconomicSummary, api, TrendChart; file tersebut tidak berubah |
| `git diff --check` | PASS, exit 0 | Git mengingatkan konversi LF→CRLF; tidak mengubah konfigurasi Git |

Bukti awal disimpan: harness pertama gagal karena klik link tersembunyi sesudah Login; setelah driver diperbaiki, RED yang sah menunjukkan form lama tidak mengirim POST reset. Perbaikan stream cancellation dan klasifikasi network failure juga mempunyai RED→GREEN tersendiri. Log lama tidak ditimpa.

### Alur browser yang benar-benar berhasil

1. Email unknown mendapat accepted generik tanpa email; stale CSRF ditolak tanpa auto-replay. Submit eksplisit berikutnya bootstrap ulang; double submit menghasilkan satu POST.
2. Form meminta reset akun sintetis. Django membuat satu email locmem; tautan hanya diteruskan lewat stdin IPC in-process ke driver, tanpa endpoint test publik/file email atau capability di receipt.
3. Tautan membuka form; check backend valid. Fragment dihapus dari alamat, storage kosong. Validator native menolak password lemah dan password yang sama.
4. Confirm lewat form mengubah password tepat sekali pada double submit, membersihkan field dan tidak auto-login.
5. Control browser terpisah membuktikan cookie sesi sebelum reset tidak bisa dipakai lagi. Form Login menolak password lama dan menerima password baru, termasuk whitespace yang dipertahankan.
6. Tautan bekas ditolak; reload tanpa fragment tidak memulihkannya. Halaman terhubung diuji pula pada lebar 390 px tanpa overflow.
7. Tes kedua membuktikan backend reset disabled mengembalikan 503, tidak mengubah password, tidak mengirim mail dan tidak menghasilkan accepted sintetis.

Django menggunakan DB test in-memory milik runner dan mailer locmem. Origin FE loopback sementara di-allowlist sebelum live middleware dibuat. Browser profile disposable dihapus, server test dihentikan dan DB test dihancurkan oleh runner. Tidak memigrasikan database pengguna. Runtime.exceptionThrown kosong pada run yang berhasil; ini bukan klaim seluruh kanal console/log bersih. LiveServer mencatat Broken pipe selama pergantian halaman/cancel; tes tetap PASS dan penyebab transport rinci tidak ditelusuri. Tidak ada credential nyata, raw outbox, request body/cookie atau capability disimpan pada receipt.

Bukti integrasi awal di `.artifacts/reset-integration/`. Evaluasi/perbaikan pra-push berikutnya di `.artifacts/reset-review/`: log RED/GREEN, unit/build/lint/browser, kedua suite integrasi, screenshot dan receipt dengan source hashes. Seluruh perintah pada tabel dijalankan ulang setelah perbaikan validasi origin. Direktori evidence di-ignore; tidak ikut dipublikasikan otomatis.

## Evaluasi dan perbaikan pra-push

Temuan konkret: URL API dengan userinfo kosong (`https://@auth.example.test`), tanpa authority separator (`https:auth.example.test`), atau backslash dapat dinormalisasi `URL()` dan tidak ditolak sebelum request. Client Reset maupun Login pada lane FE fitur 2 memiliki celah validasi yang sama. Ini kegagalan fail-closed terhadap konfigurasi tidak sesuai format, bukan bukti eksploitasi akun atau kompromi server.

Perbaikan minimal menolak whitespace, `@`, backslash dan scheme tanpa `://` pada kedua client, sambil mempertahankan same-origin dan HTTP/HTTPS origin valid. Tes negatif menunjukkan dua failure sebelum perbaikan, lalu seluruh 46 tes unit/regresi PASS setelahnya; jumlah contoh dalam loop tidak dihitung sebagai tes tambahan. Integrasi Reset 2 tes, Login 4 tes dan 22 grup browser sintetis juga PASS pada kandidat yang diperbaiki. Tidak mengubah source BE, branch fitur 1, role, session policy, CSRF/CORS atau desain.

## Mengulang integrasi lokal

Gunakan dependensi dan interpreter existing yang telah diverifikasi; tidak perlu install. Pada Git Bash dari frontend worktree ini:

```bash
export HERMES_TEST_SCRATCH='C:/Users/Pongo/AppData/Local/hermes/cache/scratch'
export DEKSI_AUTH_BACKEND_ROOT='E:/Deksi-Team/.hermes/worktrees/feature-2-reset-be/backend'
export DEKSI_AUTH_PYTHON='E:/Deksi-Team/.hermes/worktrees/feature-1-login-be/backend/.venv/Scripts/python.exe'
export DEKSI_RESET_ARTIFACTS="$PWD/.artifacts/reset-integration/reproduction"
npm run test:integration:reset
```

Harness adalah tes sekali jalan, bukan server preview yang ditinggalkan hidup. `DEKSI_AUTH_PYTHON` dapat menunjuk interpreter kompatibel di mesin lain; jangan memakai environment yang tidak diperiksa.

## Gate tersisa

- **Default BE tetap `ADMIN_PASSWORD_RESET_ENABLED=False`; integrasi ini tidak mengaktifkan reset pada database/aplikasi pengguna.** Test settings saja yang mengaktifkan locmem untuk tes. Runtime normal tetap fail-closed sampai konfigurasi/operasional disetujui.
- Inbox/SMTP/provider/sender/domain, async delivery/timing privacy, trusted proxy, HTTPS dan header cache/robots hosting produksi belum diotorisasi/diuji. Locmem bukan email yang sampai inbox.
- Bukti HTTP/backend lama dan tes concurrency BE tetap bukti historis yang terpisah; tidak dihitung ulang sebagai tes baru dalam integrasi ini.
- Human visual acceptance tetap keputusan pengguna. Izin awal integrasi tidak mencakup publikasi; pengguna kemudian mengizinkan evaluasi/perbaikan dan push ke branch fitur bila pemeriksaan lulus. PR/merge/deploy tidak termasuk izin tersebut. Checkpoint fitur 6/7 tidak diubah.

Kontrak payload tetap [DEKSI-RESET-1](FEATURE_2_RESET_PASSWORD_CONTRACT.md); [catatan prototype](FEATURE_2_RESET_PASSWORD_PROTOTYPE.md) adalah baseline historis sebelum integrasi.
