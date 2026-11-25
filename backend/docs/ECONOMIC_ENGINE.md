# Economic Engine BPS dan preview penjelasan Gemini

## Scope branch

Branch ini memuat kalkulasi deterministik porsi PMTB/PDB dan konsumsi rumah tangga/PDB, API read-only, kartu dashboard, guard Source Trace, tes, dan preview development untuk jawaban Gemini tersimpan. Ini bukan penyelesaian seluruh Economic/Diagnostic Engine atau deployment produksi.

Angka dihitung backend, bukan AI/frontend. Input wajib selaras sumber, periode, frekuensi, unit, status review/publikasi, price basis dan bukti RAW. Data hilang bukan nol. Formula `komponen / pdb_nominal * 100`, versi rumus 2; metode `bps-gdp-shares.v3`. Rilis yang tidak diketahui tetap kosong dan status revisi `unknown`. Perdagangan barang tetap unavailable sampai kesesuaian metodologinya diverifikasi.

API aplikasi: `GET /api/economic-engine/gdp/` dan `GET /api/economic-engine/trade/`. Parameter quarter mengikuti kontrak pada kode/test. Angka engine pada dashboard tidak mengikuti filter tren di atasnya; UI menyatakan konteks ini.

## Preview Gemini, bukan generasi otomatis publik

Panel **Penjelasan Gemini** pada development preview menampilkan respons nyata tersimpan dari sampel historis **Q1 2025**: porsi PMTB/PDB **28,03%**, konsumsi rumah tangga/PDB **54,56%**. File fixture jelas berlabel workflow review/publikasi simulasi dan narasi belum disetujui manusia. Ini bukan statistik resmi baru, data nasional terbaru, atau verifikasi independen BPS.

`backend/indicators/tests/fixtures/gemini_engine_preview/` memuat paket fakta/request tanpa credential dan respons JSON asli yang diperlukan pemeriksaan hash/korespondensi. Tidak ada API key atau header autentikasi. Preview menghitung ulang dari capture BPS terpilih, mengulang timestamp review **simulasi** historis, dan menolak jika seluruh packet berbeda dari snapshot yang menjadi input Gemini.

Endpoint `/api/preview-engine-narrative/` hanya terdapat pada server preview loopback, bukan URLconf produksi. Panel hanya aktif pada development flag yang ditetapkan runner; endpoint tersebut tidak ikut bundle JavaScript produksi. Membuka halaman/retry hanya GET lokal, tidak melakukan inference atau membaca key.

Alur yang dibahas “klik publik → minta generasi bila belum ada → cache bersama → review → publikasi” belum diimplementasikan untuk fakta engine. Fondasi draft/review Admin dan adapter Gemini berada pada branch terpisah `feat/ai-facts-foundation`; kedua branch belum digabungkan atau dideploy oleh publikasi ini.

## Menjalankan preview

Prasyarat: interpreter backend dengan dependency repository yang sudah tersedia, Node.js, dependency frontend yang kompatibel dengan package-lock, direktori scratch existing, serta capture/fixture yang disertakan. Launcher tidak menginstal dependency atau membaca `.env` aplikasi. Contoh dari root repository, sesuaikan lokasi interpreter/dependency:

```text
<backend-python> -B backend/tools/run_gemini_dashboard_preview.py --scratch <absolute-existing-scratch> --dependencies <absolute-existing-frontend-node_modules>
```

Buka `previewUrl` pada baris `GEMINI_DASHBOARD_READY`, bukan menyalin URL historis. Preview bind `127.0.0.1`, otomatis berhenti paling lambat satu jam, memakai SQLite memori dan RAW scratch. Biarkan terminal terbuka; Ctrl+C untuk berhenti. Tidak ada migrasi database aktif atau perubahan konfigurasi provider. Default `--saved-result` sudah menunjuk fixture relatif repository; override hanya bila memakai arsip lain yang cocok sepenuhnya.

Dependency dipakai via junction selektif pada Windows; launcher yang diverifikasi lokal ini mengandalkan `cmd.exe / mklink /J`. Jangan mengklaim launcher sudah diuji lintas OS. Child process dan log/runtime lokal tidak termasuk commit. RAW preview dibersihkan pada stop/expiry normal; salinan frontend/log di scratch dapat dibersihkan setelah semua proses milik preview berhenti. Jangan menghapus junction dependency secara rekursif atau menghentikan proses proyek lain.

## Pengujian offline

Dengan dependency backend existing, dari root:

```text
<backend-python> -B backend/indicators/tests/run_economic_engine_tests.py --scratch <absolute-existing-scratch> indicators.tests.test_economic_engine indicators.tests.test_engine_narrative_preview
```

Dari frontend dengan dependency yang sudah disiapkan:

```text
node --test tests/economic-engine.test.mjs tests/engine-narrative-preview.test.mjs tests/indicator-data.test.mjs tests/indicator-api.test.mjs tests/indicator-pages.test.mjs tests/source-trace.test.mjs
npm run build
npm run lint -- src/features/dashboard/EconomicEngine.tsx src/features/dashboard/EngineNarrativePreview.tsx src/features/dashboard/engineNarrativePreviewClient.ts tests/engine-narrative-preview.test.mjs tests/economic-engine.test.mjs tests/economic-engine.preview.mjs
```

Bukti lokal sebelum publication packaging: 81 kasus frontend unik lolos, 28 fokus diulang setelah guard DEV; 33 backend lolos termasuk 7 reader. Typecheck/build dan lint frontend target lolos. Full Ruff backend tidak dijalankan karena tidak tersedia. Browser actual menguji teks identik, digest, dua nilai, refresh, kegagalan/mismatch narasi, retry, Source Trace dan viewport 1440/768/390/320. Kontrol 503/mismatch diinjeksi hanya pada fetch narasi browser; keberhasilan memakai Vite proxy dan Django actual.

Pemeriksaan publication packaging pada salinan index Git: 33 tes backend dan 81 frontend lolos; TypeScript/build dan lint frontend target lolos. Launcher preview dijalankan dari salinan tersebut dengan fixture relatif repository, HTTP engine/narasi berhasil dan digest/nilai cocok; proses milik run dihentikan normal dan RAW dibersihkan. Tidak ada inference atau key read pada tes/preview. Receipt/log/screenshot terperinci sengaja tetap lokal, bukan dianggap hasil GitHub Actions. Tidak ada klaim seluruh suite produk/CI/production atau review bahasa manusia sudah lulus.

## Keamanan dan batas publication

Jangan commit `.env`, key, credential, database, browser profile atau log autentikasi. `.gitattributes` mempertahankan byte fixture yang terikat checksum pada checkout Windows. Paket contoh hanya memuat fakta publik historis dan jawaban model yang sudah dipindai; history revisi dan review produksi tidak diubah. Push feature branch tidak memberi izin merge, PR, deploy, atau publikasi narasi. Review manusia tetap terpisah dari validator teknis.
