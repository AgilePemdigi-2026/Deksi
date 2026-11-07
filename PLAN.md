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

## Ekspansi dan hasil — 7 November 2026

Instruksi lanjutan pengguna meminta penanganan skenario skipped/failed. Batas tanpa perbaikan produk, install, publikasi atau perubahan lane lain tetap berlaku.

1. **Ekspansi bindings dan diagnosis harness:** seluruh 72 skenario baseline kini terikat, ditambah regresi tahun kosong. Tiga kasus berlabel needs_confirmation dijalankan sebagai kontrak kandidat, tanpa menutup review Q02/Q03/Q04. Kasus official diberi label success DTO mock, bukan dipromosikan menjadi E2E backend. Perbaikan hanya pada QA: wait/navigation, oracle query/timestamp/focus, backlog test server dan startup Chrome file race. Log gagal awal dipertahankan.
2. **Run lengkap dan handoff:** `qa/artifacts/20261107-003936-sprint1-verified` menghasilkan 68 PASS / 4 FAIL dari baseline 72, ditambah satu regresi FAIL. Tidak ada skenario atau langkah skipped/undefined pada run ini; 214 langkah PASS dan 5 FAIL. Exit runner 1 tetap dipertahankan. Unit harness tambahan 2 PASS dan ruff F PASS adalah bukti terpisah. Lihat RESULTS.md, README.md, FE_HANDOFF.md dan receipt run.

Stop teknis: implementasi dan eksekusi baseline tersedia; kegagalan tersisa tercatat, tidak diperbaiki pada produk. Kedua worktree pinned clean, 9 file feature baseline byte-identical, database/proses/165 port milik run dibersihkan. Koordinasi pemilik frontend baru berupa handoff lokal, belum pesan terkirim; acceptance manusia, SRS penuh, Selenium dan produksi tidak diklaim selesai.

## Penyesuaian as-built v2 — 7 November 2026

Instruksi pengguna: "sesuaikan bdd dengan fitur dan dashboard asli", lalu "lanjutkan". Scope tetap QA, bukan perbaikan produk atau publikasi.

1. **Pemetaan aplikasi aktual:** baca kontrol/routing React serta kontrak Django; source integration masih pada checkpoint yang sama. Buat `qa/features/as-built/` (72 skenario), `as-built-manifest.json` dan `AS_BUILT_ALIGNMENT.md`. Pertahankan 69 skenario dan ganti tiga observasi as-built dengan ID baru, bukan menulis ulang hasil baseline. Klasifikasi official mock hanya tinggal di suite baseline; as-built memeriksa unclassified/formula unavailable melalui backend nyata. Rincian HTTP/transport dibuka lewat kontrol aplikasi yang sebenarnya, sedangkan gap banner not-found/state utama tetap dicatat sebagai acceptance terbuka.
2. **Verifikasi:** tiga skenario baru PASS pada run terarah; kontrol baseline not-found masih FAIL sesuai requirement lama. Tujuh unit harness/katalog PASS, termasuk RED→GREEN deadline keseluruhan command CDP, dan ruff F PASS. Dua run foreground terpotong batas tool (420 dan 360 detik); disimpan sebagai INTERRUPTED dan tidak dianggap hasil suite lengkap. Resource scratch keduanya dibersihkan setelah dipastikan tidak ada proses pemilik yang hidup. Run final dilanjutkan sebagai proses terpantau agar batas command tidak memotongnya; hasil akhir hanya boleh diambil setelah `run.json`, `behave.json` lengkap dan `cleanup.json` tersedia.

Pemeriksaan statis terpisah `qa/as-built-static-verification.json` mengonfirmasi 72 ID, sembilan feature as-built, sembilan baseline tidak berubah, 17 source pin cocok dan kedua worktree produk clean. Ini bukan bukti seluruh aplikasi PASS. Kegagalan tahun kosong dan overflow tetap guard yang aktif; pengurangan jumlah FAIL pada katalog baru tidak berarti gap produk lama diperbaiki. Lihat `RESULTS_BASELINE_V1.md` untuk hasil baseline historis dan RESULTS.md untuk laporan akhir yang sudah dieksekusi.

**Penutupan eksekusi aktual:** proses final `proc_c02414e0b7b5` sudah exited, exit 1. Run `20261107-131142-as-built-final` lengkap: katalog as-built 72 = 71 PASS / 1 FAIL; dengan regresi 73 = 71 PASS / 2 FAIL. Seluruh 219 langkah mendapat hasil (217 PASS / 2 FAIL), tanpa skipped/undefined. Reporter exit 0 memvalidasi 72 ID, hash dan ketiadaan DTO sukses mock. Receipt cleanup tersedia; 165 port milik run tidak lagi listening, DB disposable dihapus dan source produk tetap clean. Dua FAIL adalah overflow desktop dan tahun kosong → Detail terbaru. Penyesuaian QA selesai; perbaikan produk, gap acceptance lama, koordinasi pemilik FE dan persetujuan manusia tetap bukan pekerjaan yang diklaim selesai.

## Perbaikan dua FAIL — izin lanjutan 7 November 2026

Pengguna meminta memperbaiki FAIL atau menghapus jika di luar fitur. Pemeriksaan menunjukkan keduanya relevan dengan dashboard, filter dan Detail, sehingga **tidak ada tes dihapus**. Izin ini menggantikan batas no-product-edits hanya untuk dua perbaikan lokal tersebut, bukan lane sesi lain atau publikasi.

1. **Implementasi minimal:** branch lokal `fix/sprint1-bdd-layout-empty-year` dari base FE yang sama. Ubah hanya Dashboard.tsx (guard tahun kosong dan tombol hero tanpa kartu) dan dashboard.css (max-width artboard, bukan overflow hidden). Simpan manifest v2 sebelum mengunci hash overlay v2.1. Pertahankan seluruh feature baseline/as-built dan bukti RED sebelumnya; perkuat oracle regresi agar penolakan harus eksplisit serta menyebut tahun.
2. **Verifikasi selesai:** targeted tiga skenario PASS, termasuk konteks historis valid. Run penuh `20261107-183251-product-fixes-full`, proses `proc_ca035f0dae46`, exit 0: **72/72 katalog PASS, dengan regresi 73/73 PASS, 219/219 langkah PASS, 0 FAIL/skipped/undefined**. Reporter exit 0; hash/manifest/cleanup cocok, tanpa DTO sukses mock. Frontend Sprint 1 95 test PASS, QA 7 PASS, build PASS, ruff F PASS; Oxlint exit 0 dengan empat warning pada file yang tidak disentuh. Backend tetap clean, frontend hanya dua file perubahan, DB disposable dihapus dan 165 port milik run tidak listening.

Kandidat masih lokal belum commit/push/PR atau diterapkan ke lane pemilik FE. Export `PRODUCT_FIXES.patch` cocok dengan kandidat melalui reverse-apply check. Hasil sebelum perbaikan dipertahankan di RESULTS_AS_BUILT_V2_BEFORE_FIXES.md; hasil sekarang di RESULTS.md. Gap acceptance lama, review SRS/visual/manusia dan pengiriman handoff tetap belum ditutup.
