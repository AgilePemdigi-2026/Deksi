    # BDD Sprint 1 — Batch 2, jalur awal

Tanggal: 4 November 2026 (UTC+07). Izin: user mengizinkan area BDD terpisah, fixture/database disposable, browser/port terisolasi; tidak ada izin install, kode produk, commit/push/PR, database/container aktif, provider atau email nyata.

## Checkpoint yang diperiksa
- BE integration/sprint-1-unified-be: d9c673fac84992b91c160bfaa4f0de33a8ce548b.
- FE integration/sprint1-docker-fe: e35d97899d345f18a3341bc19beba431f94179d9; mewarisi e4d0588. Ref lokal integration terbaru belum menyediakan FE yang lebih baru pada inspeksi awal. Cek ulang sebelum penguncian run.
- Worktree FE clean; BE hanya mempunyai .hermes/ dan NUL untracked. Tidak diubah/disalin sebagai overlay.
- Draft referensi: E:/Semester 5/PPL Prak/Deksi/docs/bdd-sprint1; 72 skenario, acceptance detail tetap draft dan Q01–Q09 terbuka.

## Item 1 — area pengujian dan API nyata
- Buat detached worktree BE dan FE dalam E:/Deksi-BDD-Sprint1. Tidak switch/merge/rebase lane pemilik lain.
- Source produk pinned dan tanpa edit. Dependency existing Python dan frontend boleh dibaca/digandakan lokal; tidak install atau menggunakan cache writable pemilik lain.
- Gunakan Behave-Django dengan settings uji terpisah, CSRF middleware asli, SQLite disposable, akun/data SYNTHETIC dan locmem. Larang socket nonloopback. Tidak menggunakan ExistingDatabaseTestRunner.
- Pertama implementasikan BDD-F03-05 untuk memastikan draft dan published tanpa review tidak bocor melalui API. Buktikan baseline step undefined (bukan RED produk), lalu implementasikan assertion.

## Item 2 — browser React nyata
- Implementasikan BDD-F03-01 tanpa mock API: browser → Vite proxy di port ephemeral → Django LiveServer → test DB.
- Browser/profile terpisah; dependency Selenium tersedia tetapi cache chromedriver belum ditemukan. Tidak download driver tanpa izin. Jika driver tetap tidak tersedia, gunakan Chrome/CDP melalui websocket-client existing dan laporkan browser nyata NON-Selenium dengan jelas.
- Uji oracle fixture PDB 1234.50 / triliun rupiah / Q1 2025, akses anonim, request HTTP nyata dan tidak memakai database demo.
- Setelah dua jalur awal terverifikasi, nilai ekspansi berdasarkan kestabilan kontrak dan temuan; jangan memberi PASS pada 70 skenario lainnya atau melemahkan assertion untuk menyamarkan gap.
- Reproduksi filter tahun kosong → detail latest bila aman sebagai regression terpisah; beri handoff ke pemilik FE tanpa mengedit produk. Jangan mengklaim pesan terkirim bila hanya menulis handoff lokal.

## Verifikasi dan stop
- Catat command, interpreter, checkpoint tree/hash, run result, DB/profil/port cleanup, sumber spec, dan status semua 72 skenario.
- Pisahkan parser PASS, API Django client, browser E2E nyata, mock NOT RUN, visual review PENDING dan acceptance produksi NOT TESTED.
- Jika gagal produk: simpan FAIL dan bug; tidak repair produk. Jika harness salah: perbaiki hanya QA, simpan kegagalan awal dan rerun terarah.
- Teardown semua server/proses milik run; jangan menyentuh port/proses/container lain. Source worktree dibandingkan terhadap commit untuk membuktikan tidak ada edit produk.
