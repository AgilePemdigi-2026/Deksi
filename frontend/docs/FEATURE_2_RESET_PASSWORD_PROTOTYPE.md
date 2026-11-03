# Fitur 2 — prototype Reset Password Admin, Batch 2

**Catatan historis:** dokumen ini merekam tahap prototype sebelum publikasi dan integrasi berikutnya. Untuk status form FE–BE dan hasil tes terbaru, baca [laporan integrasi](FEATURE_2_RESET_PASSWORD_INTEGRATION.md). Preview sintetis tetap test-only dan tidak membuktikan pengiriman inbox nyata.

Tanggal: 3 November 2026. Status: **siap review visual dan kontrak; bukan reset backend siap pakai**.

Branch lokal `feat/2-reset-password-fe`, base fitur 1 `c288b46128db918d2d2965b72ec599d6cbe6e768`. Belum commit/push/PR. Worktree fitur 1 FE/BE dan checkpoint fitur 6/7 tidak diubah. Prototype HTML historis tidak ditimpa; gambar dan font Login tetap digunakan.

## Hasil item 3–4

1. Dua halaman React, lima state utama: minta reset, permintaan diterima, password baru, selesai, tautan tidak dapat digunakan. Termasuk pending, email/mismatch validation, error CSRF/rate-limit/unavailable/policy, show/hide terpisah, resend/edit email, keyboard/focus, dialog sumber dan responsive empat lebar.
2. [Kontrak DEKSI-RESET-1](FEATURE_2_RESET_PASSWORD_CONTRACT.md) beserta [contoh JSON dan N01–N16](../tests/fixtures/password-reset.contract.json). Payload/status sudah dituangkan sebagai target review; keputusan schema limiter dan timing/delivery produksi **masih gate manusia**, bukan dibuat seolah sudah diterapkan.

`RecoveryService` memisahkan UI dan integrasi. Sukses sintetis hanya diinjeksi dari test entry; default runtime menolak `not_connected` secara terlihat. Tidak ada HTTP adapter reset, pengiriman email, perubahan password/database atau auto-login. Build produksi diperiksa tidak memuat marker service/capability test preview. Pemeriksaan marker bukan security audit seluruh bundle.

## Menjalankan review lokal

Dari folder frontend worktree ini:

- `npm run preview:reset` — server loopback default port 62944, bukan deployment. Buka `http://127.0.0.1:62944/admin/forgot-password`.
- Isi **email contoh**, submit untuk state diterima; gunakan kontrol **Skenario review** untuk password baru, invalid link, error dan default service tanpa koneksi. Password baru boleh berupa data sintetis apa saja untuk demonstrasi kecocokan; ini tidak menguji policy server.
- Gunakan link Kembali ke Login/dashboard untuk navigasi. Login existing bukan simulasi reset: jangan memakai credential nyata dalam preview. Tidak memanggil provider atau mengirim data reset ke backend.
- `DEKSI_RESET_PREVIEW_PORT` dapat memilih port lain. Server perlu tetap berjalan agar URL berfungsi. Tidak mengubah port/server sesi lain.

## Verifikasi aktual

| Pemeriksaan | Hasil | Cakupan/batas |
|---|---|---|
| `npm test` | **31 PASS**, exit 0 | 25 existing + 6 reset/contract; unit, SSR, auth-client sintetis |
| `npm run test:browser` | **22 grup PASS**, exit 0 | 5 dashboard + 8 Login mocked-auth + 9 reset prototype, Chrome terisolasi |
| `npm run build` | **PASS**, exit 0 | TypeScript + Vite; warning bundle >500 kB tetap ada |
| `npm run lint` | **0 error / 3 warning**, exit 0 | Warning inherited EconomicSummary.tsx, src/api.ts, TrendChart.tsx; tidak ditekan |
| `git diff --check` | **PASS**, exit 0 | Tidak membuktikan auth/email |
| HTTP server preview | **200** pada tiga route auth | Test entry, no-store/no-referrer; bukan konfigurasi produksi |
| Empat lebar | **1440/1024/760/390**, tanpa horizontal overflow pada pemeriksaan DOM | Capture desktop/narrow dan form-first narrow; approval visual belum diterima |
| UI error/runtime | **0 Runtime.exceptionThrown** di tiga suite | Tidak berarti seluruh potensi error/provider sudah diuji |

9 grup reset mencakup: required/malformed email dan duplicate guard; resend/edit/focus; required/mismatch dan toggle terpisah; sukses sintetis tanpa auto-login dan tanpa field password tersisa; tautan invalid generik; fixture CSRF/429/unavailable/password policy; ambiguous confirmation tanpa replay serta default service gagal eksplisit; responsive/keyboard/dialog; reload tanpa capability/browser storage dan tanpa traffic API reset nyata.

Screenshot asli lima state dan empat lebar, log RED/GREEN, log final dan receipt berada pada evidence lokal. Salinan durable yang di-ignore: `.artifacts/reset-batch2/`. Jangan commit evidence, node_modules, dist, environment/DB atau profile browser. Browser QA dan server sementara suite sudah ditutup; server review yang sengaja dijalankan dilaporkan terpisah.

### Temuan yang diperbaiki selama pengujian

- Navigasi fragment baru pada reset page yang masih mounted semula mempertahankan state selesai. Reproduksi menunjukkan heading selesai dengan fragment baru masih terpasang. Handler `hashchange` sekarang membatalkan request sebelumnya, membersihkan field lama, mengonsumsi/membersihkan alamat dan memeriksa capability baru. Bukti RED disimpan, bukan dihapus.
- Fokus error password dari server semula dicoba saat input masih disabled. Fokus dijadwalkan sesudah render mengaktifkan input; kontrol browser memeriksa pesan dan actual activeElement.
- Kode field tak dikenal termasuk nama properti turunan object semula dapat lolos lookup pesan. Reproduksi `constructor` dipertahankan sebagai RED; mapping sekarang memeriksa own-property dan tipe string sebelum menampilkan allowlist/generic text.
- Harness awal salah membandingkan scrollWidth dengan viewport termasuk scrollbar. Assertion diperbaiki menjadi scrollWidth <= clientWidth; tidak mengubah aplikasi untuk menyembunyikan scrollbar atau horizontal overflow.
- Pemeriksaan focus sesudah edit email menunggu render/requestAnimationFrame, bukan membaca sebelum perubahan tampilan selesai.

## Traceability dan gate berikutnya

Bukti ini parsial untuk F2-01/02/07/08/11/14/15/16: terutama lapisan UI/sintetis. Tidak menaikkan seluruh requirement menjadi PASS. F2-03/04/05/06/09/10/12/13/17/18 memerlukan BE/privacy/security/email/integrasi atau acceptance terpisah. Penolakan old cookie/password, expiry/replay, shared throttling, atomic confirm, Django locmem dan real SMTP fitur 2 **NOT RUN**. Regresi Login di sini mocked-auth; empat tes integrasi Django fitur 1 terdahulu adalah bukti historis, tidak dijalankan ulang pada batch ini.

Persetujuan selanjutnya perlu terikat pada prototype/kontrak yang sekarang: arah visual dua halaman/lima state serta TTL/policy dan keputusan scope limiter/timing. Setelah gate tersebut, buat lane BE dari checkpoint yang diverifikasi ulang dan lakukan Batch 3. Tidak membuat branch BE kosong, dependency, schema/outbox/worker, provider/biaya atau publikasi otomatis. Foto Login tidak diganti; persoalan hak publikasi foto dashboard historis tidak diselesaikan oleh batch reset.
