# Integrasi Economic Engine dan AI pada main

> Kelanjutan 26 November 2026: [PUBLIC_ENGINE_AI.md](PUBLIC_ENGINE_AI.md) menjelaskan tombol produksi, antrean Gemini, review Admin, konfigurasi runtime dan batas verifikasinya. Catatan di bawah tetap bukti historis integrasi awal, bukan status aktivasi fitur baru.

Izin pengguna pada 25 November 2026: direct push dua fitur ke main, tanpa API key. Base main yang dipertahankan: `c722e7ac3ca4599d4566ea0f616f5af988a09b51`. Head feature: engine `e9f8dc330c65c8991267a21ec0de831dd712fbff` dan AI `30847de08944990e467856a7f4e4caa398decd91`.

## Hasil integrasi

- Main terbaru dan kedua feature dipadukan di worktree terpisah; fitur/config/route tim tetap dipertahankan, bukan mengganti main dengan tree branch lama.
- Konflik `.gitattributes` diselesaikan dengan gabungan kedua aturan preservasi byte fixture. Secret, `.env` populated, log, database, dependency dan metadata agent tidak menjadi isi commit.
- Main mempunyai leaf migrasi `0025_merge_20261124_2326`; AI menambah `0025_ai_narrative_drafts`. Uji awal benar-benar gagal karena dua leaf. `0026_merge_ai_narrative_main` menghubungkan kedua leaf dengan **operations kosong**, tanpa mengubah migration historis.
- Migrasi AI asli tetap menambah tabel draft/review. Merge migration kosong tidak berarti seluruh rangkaian migrasi tidak mempunyai perubahan schema. Compose produksi menjalankan migrate saat startup; push bukan bukti deploy atau migrasi pada database aktif telah diuji/diterapkan.
- Engine deterministik tetap terpisah dari narasi AI. Gemini tetap adapter/pilot ber-credential server-side dan preview development; ini belum generasi anonim publik, shared-cache engine atau publikasi narasi otomatis. Tidak ada key server yang diaktifkan oleh commit.

## Pemeriksaan actual pada hasil gabungan

- **168 backend** lolos: runner SQLite terisolasi memuat fakta/narasi/provider/Gemini pilot, engine, reader fixture, regresi detail/Source Trace/dashboard/RAW/candidate, dan dua cek integrasi baru. Tidak ada koneksi provider atau `.env` aplikasi.
- **155 frontend** lolos dari 15 file test unik: gabungan manifest default, Sprint 1, dashboard, indikator, Source Trace dan narasi, ditambah engine/preview. Daftar dideduplikasi; ini bukan klaim semua suite browser/BDD.
- TypeScript + production build exit 0. Lint target exit 0 dengan satu warning existing set-state-in-effect pada AdminAnalysisPage. Build memperingatkan chunk utama lebih dari 500 kB; tidak mengubah threshold atau menutupinya lewat refactor di luar scope.
- `makemigrations indicators --check --dry-run`: tidak ada drift. Uji upgrade SQLite memori dari leaf main lama ke leaf gabungan berhasil, membuat tabel draft/review, mempertahankan seluruh isi tabel indicators yang sudah ada pada fixture, dan apply berikutnya tidak memiliki rencana baru. Ini bukan uji PostgreSQL/backup/pemulihan produksi.
- Launcher preview dari tree gabungan memakai fakta/response fixture relatif repository, API Vite proxy/Django actual HTTP 200 dan seluruh binding result digest/nilai cocok. Tidak ada inference/key read; proses milik uji dihentikan normal dan RAW/frontend/junction sementara dibersihkan. Uji visual browser sebelumnya hanya digunakan untuk komponen yang byte-nya tidak berubah; tidak dinaikkan menjadi review manusia.

Runner backend yang disertakan, dari root dengan interpreter/dependency existing:

```text
<backend-python> -B backend/indicators/tests/run_engine_ai_tests.py --scratch <absolute-existing-scratch>
```

Template key berada di `backend/.env.gemini-pilot.example` dan sengaja kosong. Key nyata hanya di local ignored file atau environment proses server; tidak dalam frontend, Git, command arguments atau fixture publik. Scan mencakup pencarian nilai key pengguna secara exact pada seluruh blob perubahan, ditambah signature secret. Scan signature bukan audit keamanan menyeluruh.

Dokumen feature [Economic Engine](ECONOMIC_ENGINE.md) dan [Gemini pilot](GEMINI_ENGINE_PILOT.md) menjelaskan batas awal masing-masing branch. Dokumen ini memperbarui status integrasinya di main; status historis di bukti lama tidak dipalsukan sebagai hasil CI/deploy.

## Batas tersisa

Tidak ada klaim CI remote sudah hijau, deploy telah selesai, produksi sudah memakai Gemini, migrasi database aktif sudah dijalankan, atau narasi sudah direview manusia. Tidak menjalankan provider request tambahan, instalasi dependency, bypass branch protection, force push atau perubahan credential. Snapshot input/review simulasi tetap diberi label. Push kode tidak memublikasikan draft narasi menjadi analisis resmi.
