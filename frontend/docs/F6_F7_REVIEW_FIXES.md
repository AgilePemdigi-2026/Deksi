# F6/F7 frontend — dua batch koreksi hasil review

Pengguna mengizinkan perbaikan empat temuan dalam dua batch. Scope tetap frontend, tanpa install/dependency baru, backend, Login, commit/push/PR/merge atau perubahan identitas Git. Hasil teknis aktual dan waktu pemeriksaan ada di [receipt](F6_F7_REVIEW_FIXES.json).

## Batch 1 — ketahanan data

1. `src/features/indicators/api.ts`: setiap resource memiliki deadline default 10 detik, termasuk parsing JSON. Timeout membatalkan request tersebut dan menjadi warning parsial; resource lain yang berhasil tetap digunakan. Parent abort tetap menghentikan seluruh request. Timer dan event listener dibersihkan pada completion/error/abort. Parameter timeout pada adapter dapat dipendekkan untuk unit test, bukan pengaturan operasional Admin.
2. `types.ts`, `api.ts`, `data.ts`, `DetailPage.tsx`: metadata frequency/dataType histori tidak lagi dibuang. Grafik menolak perbedaan satuan, jenis pengukuran, atau frekuensi. Nilai asli, periode, jenis data dan frekuensi tetap dapat dibaca pada tabel. Metadata titik mengambil nilai payload ketika metadata per titik tidak tersedia sesuai bentuk API existing; null yang tercampur metadata dikenal juga menolak penyambungan. Tidak membuat konversi/agregasi ekonomi frontend.

## Batch 2 — keterbacaan

3. `data.ts`, `DetailPage.tsx`: skala Y numerik ditambahkan; margin plot memberi ruang label. Seri konstan/satu titik menampilkan satu tick, seri kosong tidak membuat skala palsu; nol, negatif, dan angka besar diuji. Format skala memakai maksimal lima digit signifikan dan notasi ilmiah untuk besaran ekstrem, hanya sebagai label grafik. Nilai presisi sumber pada ringkasan tidak diubah.
4. `SourceTracePage.tsx`, `source-trace.css`: periode observasi tampil berdekatan dengan nilai dan satuan pada ringkasan F7. Periode historis tetap berasal dari reading terpilih; contextError tidak diganti periode latest.

## Bukti RED → GREEN

Empat reproduksi di `.artifacts/review-b1-timeout-red.log`, `review-b1-mixed-red.log`, `review-b2-axis-red.log`, dan `review-b2-period-red.log` masing-masing menunjukkan satu tes gagal sebelum perbaikannya. Receipt menyimpan alasan kegagalan dan hash. Tes kompatibilitas tambahan mencakup body JSON macet, parent cancellation yang diabaikan transport, skala konstan/nol/negatif/kosong/besar.

## Pemeriksaan akhir aktual

| Pemeriksaan | Hasil | Scope |
|---|---|---|
| `npm run test:indicators` | 32/32 PASS, 0 skip | F6 helper, adapter, SSR dan regresi koreksi |
| `npm run test:source-trace` | 12/12 PASS, 0 skip | F7 SSR/context, termasuk assertion periode baru |
| `npm test` | 7/7 PASS, 0 skip | Editorial unit |
| `HERMES_TEST_SCRATCH=... npm run test:source-trace:browser` | 18 kelompok PASS: 8 F7 + 10 F6/shared/koreksi; 0 runtime exceptions | Chrome disposable nyata, API sintetis; menguji default timeout 10 detik dan keyboard retry pada kedua screen, grafik campuran, skala Y, periode terpilih, navigasi/cancellation dan 390/768/1440px |
| `HERMES_TEST_SCRATCH=... npm run test:browser` | 5 kelompok editorial PASS, 0 runtime exceptions | Regresi browser dashboard dengan API sintetis |
| `npm run build` | Exit 0 | TypeScript/Vite; warning chunk >500 kB masih ada |
| `npm run lint` | Exit 0 | Tiga warning existing di shared API, EconomicSummary, TrendChart; tidak ada warning fitur baru |
| `git diff --check` | Exit 0 | Whitespace |

Seluruh tes tersebut dijalankan pada batch koreksi, bukan mengganti angka historis. Log akhir memakai nama `.artifacts/review-*-final.log`. Bukti browser terdahulu dan log lama dipertahankan di `.artifacts/pre-review-fixes` sebelum output browser diperbarui. Screenshot baru tetap sintetis, bukan demonstrasi data ekonomi resmi; screenshot F6 desktop memperlihatkan label 2/1/0, crop F7 narrow memperlihatkan periode di bawah nilai tanpa overlap yang tampak. Ini bukan persetujuan estetika pengguna atau audit aksesibilitas menyeluruh.

Source/test/config digest saat verifikasi: `b87b4b0080290c12cfb1abc02d26b593e1c9a6ee66a6a0e68a93894fe3554325`.

## Git, dependency dan batas acceptance

- Semua koreksi saat ini berada di worktree `feature-7-source-trace-fe`, branch `feat/7-source-trace-fe`, di atas HEAD F6 `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`; belum di-commit/stage.
- Checkpoint F6 pada branch `feat/6-detail-indikator-fe` tetap bersih/tidak diubah. Artinya patch koreksi F6 belum diterapkan terpisah pada branch F6. Pemisahan commit/propagasi dependency memerlukan izin Git tersendiri; jangan mengklaim checkpoint F6 lama sudah memuat koreksi ini.
- Checkpoint gabungan lama `cc738a8bdd7a9af44870c5480e61991050577094` tetap bersih. Backend, Login, shared API dashboard, aset/font/global CSS, komponen dashboard dan package-lock tidak berubah.
- Receipt F7 awal tetap bukti historis. Gunakan receipt koreksi ini untuk source terkini; jangan membandingkan hash baru terhadap receipt lama lalu menganggap tes lama berlaku pada perubahan ini.
- API live tidak diuji ulang pada batch ini. Integrasi Django/data nyata, immutable revision, formula/input backend dan review estetika F7 tetap belum diselesaikan. Tidak menjalankan canonical bootstrap/backend verifier untuk menghilangkan reminder.
