# F6 — port frontend editorial: implementation handoff

## Scope dan identitas

- Branch: `feat/6-detail-indikator-fe`.
- Worktree: `E:/Deksi-Team/.hermes/worktrees/feature-6-detail-fe`.
- Base dan HEAD saat handoff: `505e97116f132c8630ec08d07525b8aec9e00536`.
- Implementasi masih perubahan lokal, **belum commit/push/PR**.
- Digest kandidat source/test/config: `56c0a4cf0d3d402f6a9695a6b603c949d2f715a2707379c594cba870c04a9d48`. Daftar hash per file ada di [receipt](F6_FRONTEND_VERIFICATION.json).
- Backend, Login, checkpoint gabungan lama, font/aset/global theme/layout editorial tidak diedit. `git diff --exit-code HEAD -- backend` dan perlindungan aset/style lulus.

## Yang diimplementasikan

1. Route publik `/indikator/:code`, wiring anchor Detail dari kartu dashboard, pilihan indikator dan kontrol periode untuk konteks sumber yang tersedia. Dashboard dimount pada komponen sendiri dengan JSX lama; hook dashboard tidak dipasang ketika membuka Detail langsung. Route invalid atau selector revisi yang tidak didukung tidak berubah menjadi latest.
2. Nilai/satuan/periode, pembanding dari backend bila cocok, chart+tabel histori, source metadata, date-only release, acquisition time dan unavailable states. Decimal string ditampilkan tanpa melewati float. Chart memakai angka numerik endpoint histori, bukan sumber nilai presisi untuk detail atau perhitungan ekonomi.
3. Guard konteks response mengikat semua field DTO yang dinormalisasi, termasuk source/RAW/rilis/status yang tersedia. Pilihan periode hanya menawarkan kandidat yang cukup lengkap dan tidak ambigu. Perubahan guard menampilkan penolakan dan placeholder pemilih, bukan otomatis memilih latest. Guard **bukan** snapshot immutable, ID observasi, revisi resmi atau bukti kebenaran angka.
4. Endpoint summary, native trend dan source-trace dibaca independen dengan cancellation; kegagalan sumber tidak menghapus ringkasan/histori yang valid. Respons salah indikator, angka tidak sesuai, ambiguity dan pinned context hilang ditolak. Tidak ada import fixture atau API AI dalam runtime.
5. F7 belum dipasang pada branch F6. Tombol Source Trace sengaja disabled dan direct URL Source Trace menampilkan keterbatasan, bukan dead link menuju halaman data palsu. Tidak menambahkan formula/input/revisi sintetis agar tampilan terlihat penuh.

## Kepemilikan file

- Baru: `src/features/indicators/{types.ts,data.ts,api.ts,DetailPage.tsx,features.css}`.
- Routing saja: `src/App.tsx`; markup dashboard dipertahankan.
- Wiring saja: `src/components/IndicatorCard.tsx`.
- Shared API: `src/api.ts` hanya mengekspor konstanta `API_BASE`; hook dan URL dashboard tidak diubah.
- Tests: `tests/indicator-{data,api,pages,browser}.test.mjs`, `tests/indicator-fixtures.mjs`. Fixture sintetis berada di direktori tes, tidak di public atau bundle aplikasi.
- `tests/editorial.test.mjs`: assertion placeholder Detail diubah menjadi assertion route Detail nyata sesuai integrasi; guard no-dead-anchor tetap ada.
- `package.json`: menambah script tes fitur dan browser fitur, tidak menambah/mengubah dependency atau lockfile.
- Dokumentasi: audit/rencana, receipt Batch 1 dan handoff/receipt F6 ini.

## Bukti eksekusi aktual

Dari direktori `frontend/`:

| Perintah / pemeriksaan | Hasil | Batas bukti |
|---|---|---|
| `npm run test:indicators` | 26 tes lulus | Parser/adapter, source guard, SSR halaman, null/zero, malformed/unsafe data dan route; menggunakan DTO sintetis terpisah. |
| `npm test` | 7 tes editorial lulus | Bukan alias suite fitur; keduanya dijalankan. |
| `npm run test:indicators:browser` | 8 kelompok pemeriksaan lulus | Browser Chrome nyata dengan API **diintersepsi sintetis**, bukan API Django live. |
| `npm run test:browser` | 5 kelompok editorial lulus | Suite existing: geometri dashboard, chart, disclosure/focus, responsive dan empty/error; API sintetis. |
| `npm run build` | Exit 0 | TypeScript dan Vite; ada warning chunk lebih besar 500 kB, tidak disembunyikan. |
| `npm run lint` | Exit 0 | Tiga warning pada kode existing `api.ts`, `EconomicSummary.tsx`, `TrendChart.tsx`; tidak ada warning pada folder fitur baru. |
| HTTP preview | Detail, modul TSX dan CSS masing-masing 200 | Membuktikan frontend tersaji, bukan data ekonomi/API live. |
| Git diff/scratch | Check lulus; profile browser milik tes dibersihkan | Tidak menutup browser pengguna. |

Browser fitur memeriksa deep link tanpa request hook dashboard, zero dan chart gap, pemilihan periode melalui keyboard native, reload exact guard, penolakan rilis berubah tanpa fallback, invalid revision tanpa loader API, partial failure, error/retry via Enter, state loading yang mengosongkan nilai lama, responsive 390/768/1440, dan navigasi dashboard → Detail → dashboard.

Saat menyiapkan browser harness ada kegagalan yang dibedakan dari kegagalan produk: Enter memerlukan karakter CR; scrollbar membuat viewport berbeda dari client width; reload perlu menunggu dokumen baru; nested selector perlu escaping; AbortController React StrictMode membatalkan request yang sudah dicegat. Harness kini hanya menerima `Invalid InterceptionId` bila ada event `Network.loadingFailed` **canceled** untuk network ID yang sama; runtime exception aplikasi tetap wajib nol. Kegagalan harness tersimpan di `.artifacts/feature6-browser/failure-*.json` dan catatan receipt. Tidak menonaktifkan cancellation atau melemahkan perlindungan frontend untuk meluluskan harness.

Reproduksi browser memerlukan Chrome existing dan scratch eksplisit:

```bash
HERMES_TEST_SCRATCH='C:/Users/Pongo/AppData/Local/hermes/cache/scratch' npm run test:indicators:browser
HERMES_TEST_SCRATCH='C:/Users/Pongo/AppData/Local/hermes/cache/scratch' npm run test:browser
```

Paket installed fondasi disalin ke node_modules worktree terisolasi setelah kesamaan lockfile diverifikasi. Tidak ada install/download, upgrade, atau penulisan cache ke node_modules worktree fondasi. Artifacts/runtime tetap ignored; staging belum dilakukan.

## Preview dan batas acceptance

Preview lokal dijalankan melalui `npm run dev -- --host 127.0.0.1 --port 5186 --strictPort`:

`http://127.0.0.1:5186/indikator/inflasi`

Proses preview lokal biasa, bukan service persisten. Halaman menggunakan API aktual yang dikonfigurasi aplikasi; bila API belum tersedia, tampil error/kosong. Tidak ada mode demo atau endpoint intersepsi pada server preview. Screenshot `.artifacts/feature6-browser/detail-desktop-synthetic.png` hanya untuk memperlihatkan state berisi pada browser tests; judul/instansi jelas UJI SINTETIS, bukan data ekonomi live. Screenshot empty juga berasal dari simulasi tes.

Persetujuan arah visual F6: **diterima untuk melanjutkan**, setelah pengguna melihat preview/screenshot dan menyatakan "oke tahap berikutnya". Ini berlaku untuk source digest kandidat di atas dan layout F6 yang ditampilkan, bukan otomatis untuk layout F7 atau audit estetika/aksesibilitas menyeluruh. Tidak ada klaim memenuhi seluruh WCAG, backend formula, official-data correctness, atau end-to-end Source Trace. API live pada Batch 1 timeout; tidak menyalakan/mengubah Django untuk batch frontend ini.

## Gate berikutnya

### Batas pengenalan verifikasi otomatis

Setelah reminder workspace `unverified`, dilakukan pemeriksaan read-only melalui `hermes verify --help` dan `--detect-only --json`, bukan pengulangan suite. Semua 15 hash source/test/config masih cocok dengan receipt hasil uji. Detector pada root worktree memilih recipe **Django** (`pip install -r requirements.txt`, `python manage.py test`, lalu runserver 8000); detector pada subdirektori `frontend/` memilih **Vite**, tetapi menyertakan bootstrap `npm install` dan default test/lint, bukan suite fitur/browser tambahan. Perbedaan root deteksi sudah terbukti; penyebab persis ledger belum dibuktikan dan status canonical tidak diklaim telah diperbaiki. Tidak menjalankan bootstrap/backend atau mengubah manifest/ledger/guard untuk menghapus reminder. Hasil eksekusi yang hash-nya cocok tetap berlaku, sedangkan canonical recognition tetap `unverified` dan visual acceptance pending. Pemeriksaan tambahan menunggu gate visual/commit yang diminta pengguna.

Izin checkpoint dicatat 2 November 2026 pukul 23:06 UTC+07: pengguna menjawab **"Izinkan checkpoint lokal F6 dan lanjut frontend F7"** pada pertanyaan yang mengikat source digest `56c0a4cf0d3d402f6a9695a6b603c949d2f715a2707379c594cba870c04a9d48`. Izin hanya commit lokal kandidat F6 dan worktree/branch dependency `feat/7-source-trace-fe`; **bukan push, PR, merge, perubahan backend atau izin commit F7 otomatis**. F7 dimulai dari commit dependency tersebut dan diff dilaporkan terhadapnya. Receipt uji sebelumnya tetap bukti historis sebelum keputusan ini; tidak ditulis ulang menjadi eksekusi atau persetujuan baru.
