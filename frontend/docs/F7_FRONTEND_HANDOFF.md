# Frontend F7 — Source Trace Data

**Status persiapan publikasi terbaru:** pengguna mengizinkan commit/push dua feature branch tanpa PR/merge. Seluruh koreksi F6 kini ada pada branch F6 di commit `13a7680e96c1170cb9dcc041577e626760d8d76f`; worktree F7 sudah fast-forward ke dependency tersebut dan overlay F7 dipulihkan tanpa konflik. Seluruh 22 file overlay cocok dengan backup pra-pemisahan setelah memperhitungkan CRLF/LF existing. Lihat [handoff publikasi](F7_PUBLICATION.md) dan [receipt verifikasi pasca-pemisahan](F7_PUBLICATION.json) untuk bukti terkini; uraian di bawah adalah riwayat tahap sebelumnya. Publikasi remote baru dinyatakan sukses setelah readback SHA, bukan oleh dokumen ini.

**Koreksi presisi skala F6 setelah evaluasi akhir:** formatter kini menambah digit signifikan hanya ketika label berbeda masih bertabrakan. Contoh `5.000001`–`5.000002` menghasilkan skala `5,000002 / 5,0000015 / 5,000001`, tanpa mengubah nilai sumber. Tes baru terbukti RED sebelum patch, lalu suite F6 33/33 dan F7 12/12 PASS, build/lint exit 0 (warning existing tetap ada). Fingerprint source paling baru ada pada [receipt presisi skala](F6_AXIS_PRECISION_FIX.json); receipt dua batch di bawah menjadi bukti tahap sebelumnya. Browser tidak diulang pada patch formatter ini; verifikasi mencakup helper, render SSR halaman aktual dan build. Tidak mengubah backend atau membuat commit.

**Pembaruan setelah evaluasi:** empat temuan F6/F7 diperbaiki dalam dua batch atas izin pengguna. Lihat [hasil koreksi terbaru](F6_F7_REVIEW_FIXES.md) dan [receipt source terkini](F6_F7_REVIEW_FIXES.json). Angka tes, digest dan receipt di bawah adalah bukti sebelum koreksi, dipertahankan sebagai riwayat; bukan fingerprint source terbaru. Patch koreksi F6 berada pada worktree F7, belum dipropagasi ke checkpoint F6 terpisah. API nyata dan review estetika F7 tetap pending.

Tanggal: 3 November 2026, UTC+07. **Frontend functional selesai pada cakupan tes di bawah; review estetika F7 dan integrasi backend nyata belum selesai.**

## Preview

- Runtime: http://127.0.0.1:5187/indikator/inflasi/sumber
- Worktree: `E:/Deksi-Team/.hermes/worktrees/feature-7-source-trace-fe`.
- Vite process: `proc_3b03b094a703` (PID 1756), tidak dijanjikan persisten melewati lifecycle sesi.
- Route dan modul TSX/CSS/hook diperiksa HTTP 200 pada 3 November 2026 07:47:29 UTC+07. Ini bukti delivery frontend, bukan payload API valid.
- Screenshot browser aktual, **API sintetis, bukan angka ekonomi resmi**: `.artifacts/feature7-browser/source-desktop-synthetic.png` dan `source-mobile-synthetic.png`. Ada label UJI SINTETIS pada gambar, bukan mode demo pada aplikasi.
- Tiga GET API lokal yang diperiksa 07:45:49 UTC+07 mengalami `ConnectTimeout`. Runtime tidak memasukkan fixture sebagai fallback; pengguna dapat melihat loading/error/missing sesuai koneksi API.

## Branch, base dan checkpoint

| Fitur | Branch | Base | HEAD / keadaan |
|---|---|---|---|
| F6 | `feat/6-detail-indikator-fe` | `505e97116f132c8630ec08d07525b8aec9e00536` | `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`, checkpoint lokal berizin, worktree bersih |
| F7 | `feat/7-source-trace-fe` | `14be3d9780f65ea0ea85244c1f089ae93f8dec3c` | HEAD masih base F6; delta F7 lokal belum di-commit |

Checkpoint gabungan lama `cc738a8bdd7a9af44870c5480e61991050577094` tetap bersih/tidak diubah. Origin lokal diperiksa sebagai `https://github.com/AgilePemdigi-2026/Deksi.git`; tidak ada fetch/push/PR/merge pada batch F7. Tidak mengubah identitas Git atau branch Login.

## Item 5 — hasil implementasi

- Halaman Source Trace editorial monokrom: ringkasan indikator/nilai/satuan/status backend, hubungan metadata, ruang formula/input/hasil yang eksplisit belum tersedia, metadata publikasi/observasi/rilis/akuisisi, dokumen/RAW, keterbatasan, riwayat revisi unavailable, dan tabel pilihan observasi yang bukan jurnal revisi.
- Shell, komponen field/tautan, formatter, guard, resolver, adapter dan gaya fondasi F6 digunakan ulang. Tidak menambah dependency/framework atau mengubah transport dashboard.
- Loader F6 diekstrak ke `useDetailData.ts`; kedua screen memakai jalur request/cancellation/keyed result yang sama. Tetap tiga GET publik dari adapter F6; belum optimasi endpoint khusus F7. Bukan tiga request ke sumber eksternal/ingestion.
- Detail → Source Trace → kembali mengikat tanggal, jenis data, frekuensi, sumber dan guard nilai/metadata yang sama. Konteks historis dipilih hanya dari kandidat source trace yang tersedia dan unik, bukan dari angka grafik.
- Perubahan nilai/unit/institusi/rilis/RAW, kandidat hilang/ambigu atau indikator salah ditolak, bukan fallback latest. Tautan kembali ke detail nonaktif bila konteks tidak dapat dipastikan; pilihan konteks lain tetap tautan eksplisit, bukan redirect otomatis.
- Rute tanpa selector secara eksplisit berarti konteks terbaru pada respons, bukan snapshot historis. Guard frontend bukan ID observasi/revisi/snapshot backend atau bukti kebenaran.
- RAW yang null pada observasi lama tidak diisi dari latest. Unduhan hanya path `/api/indicators/<kode-yang-sama>/raw-file/<id-positif>/` yang diikat ke origin API existing; origin lain, query, traversal dan newline ditolak. Frontend tidak server-fetch URL arbitrer.
- Tanggal rilis date-only tetap tanggal, tidak dibuat timestamp. Status `published` bukan klaim "tervalidasi resmi". DataType bukan otomatis klasifikasi resmi/derived.
- Backend belum menyediakan formula ID/versi/ekspresi, input deterministik, hasil presisi dan aturan pembulatan, jurnal revisi observasi yang sama, referensi publikasi terstruktur dan immutable identity. Bagian ini disiapkan dalam UI tetapi belum berisi data; tidak ada formula atau perhitungan ekonomi frontend pengganti.

## File delta F7 terhadap checkpoint F6

Semua path relatif root worktree. Tidak menyertakan kembali seluruh patch F6.

1. `frontend/src/features/indicators/SourceTracePage.tsx` — halaman dan screen F7.
2. `frontend/src/features/indicators/source-trace.css` — style khusus Source Trace, termasuk caption kontras, tanpa mengubah tema global.
3. `frontend/src/features/indicators/source.ts` — binding link konteks dan pembatas path RAW.
4. `frontend/src/features/indicators/useDetailData.ts` — ekstraksi loader F6 existing untuk reuse.
5. `frontend/src/features/indicators/DetailPage.tsx` — aktivasi link F7 dan penggunaan hook bersama; halaman F6 tidak mengimpor halaman F7.
6. `frontend/src/App.tsx` — mount route F7; dashboard tetap terisolasi dari public feature loader.
7. `frontend/tests/source-trace.test.mjs` — suite SSR/helper/context F7.
8. `frontend/tests/indicator-browser.test.mjs` — reuse harness disposable melalui `--source-trace`; regresi F6 dan alur F7 dipisahkan dalam receipt. Fixture histori RAW dibuat null untuk menguji larangan borrow dari latest.
9. `frontend/tests/indicator-pages.test.mjs` — assertion F6 berubah dari disabled placeholder menjadi active exact-context link.
10. `frontend/package.json` — dua script tes F7 eksplisit; manifest dependency/lock tidak di-upgrade.
11. `frontend/docs/F7_FRONTEND_PLAN.md` — izin, dependency dan batch 5–6.
12. `frontend/docs/F6_F7_AUDIT_PLAN.md` — catatan progres terbaru, tanpa mengubah bukti audit/API historis menjadi bukti baru.
13. `frontend/docs/F7_FRONTEND_VERIFICATION.json` — hasil dan hash aktual.
14. `frontend/docs/F7_FRONTEND_HANDOFF.md` — dokumen ini.

## Item 6 — bukti eksekusi aktual

Seluruh perintah dari `frontend/`, memakai dependency existing. Receipt [F7_FRONTEND_VERIFICATION.json](F7_FRONTEND_VERIFICATION.json) mengikat **22 source/test/config files**, dengan digest:

`2e423a77eb15016def8ac615b9ea4bec6433b9ccad48373d6288adfd4fd39ca2`

| Pemeriksaan | Hasil aktual | Batas bukti |
|---|---|---|
| `npm run test:source-trace` | **12/12 PASS**, exit 0, 0 skip | SSR/helper/adapter dengan DTO sintetis |
| `npm run test:indicators` | **26/26 PASS**, exit 0, 0 skip | Regresi F6 aktual pada branch F7, bukan mengutip tes historis |
| `npm test` | **7/7 PASS**, exit 0, 0 skip | Suite editorial default saja |
| `HERMES_TEST_SCRATCH=... npm run test:source-trace:browser` | **8 kelompok F7 + 8 kelompok F6/shared PASS**, exit 0; 0 runtime exception | Browser Chrome nyata, respons API diintersep sintetis, bukan integrasi Django |
| `HERMES_TEST_SCRATCH=... npm run test:browser` | **5 kelompok editorial PASS**, exit 0; 0 runtime exception | Dieksekusi pada batch ini setelah implementasi runtime; perubahan sesudahnya hanya CSS caption scoped F7 dan assertion tes F7, tidak mengubah dashboard |
| `npm run build` | PASS, exit 0 | TypeScript + Vite; warning chunk >500 kB tetap ada, bukan klaim performa produksi |
| `npm run lint` | Exit 0, **3 warning existing**, 0 warning fitur baru | EconomicSummary fast refresh, shared API set-state-in-effect, TrendChart exhaustive-deps; tidak diperbaiki di luar scope |
| API live | Tiga GET publik **ConnectTimeout**, tidak ada payload tervalidasi | Tidak menyalakan/edit backend, migrasi atau database |
| Preview | Route dan tiga modul/aset diperiksa HTTP 200 | Delivery frontend saja |
| Review visual F7 | **PENDING pengguna** | Screenshot dan pemeriksaan layout fungsional bukan persetujuan estetika |
| Canonical Hermes | Tidak menjalankan bootstrap/backend/full canonical verifier pada batch ini | Hasil perintah scoped di atas dipisahkan dari pengenalan canonical |

Browser F7 mencakup keyboard pergi-kembali, historical selection dan reload, tidak menyalin RAW latest, matrix perubahan metadata dan identitas, partial/empty/error/held retry, malformed/duplicate/incomplete/revision URL tanpa request API, rapid navigation/cancellation, serta 390/768/1440px tanpa overflow halaman dengan scroll tabel lokal. Caption yang sebelumnya kalah specificity terhadap style F6 diperbaiki dan warna computed diuji pada browser akhir. Profil tes disposable dibersihkan oleh teardown; browser pengguna tidak ditutup. Script receipt sementara dialokasikan di scratch yang diizinkan dan dihapus.

Log akhir ada di `.artifacts/{f7-unit-final,f6-unit-final,editorial-unit-final,f7-build-final,f7-lint-final,f7-browser-final}.log`. Receipt browser ada di `.artifacts/feature7-browser/verification.json` dan `.artifacts/browser/verification.json`. Output build dan screenshot memiliki SHA-256 terpisah pada receipt.

Pemeriksaan Git membuktikan perubahan hanya di frontend; `backend/`, README root, shared API, komponen/dashboard/assets/font/global CSS, package-lock, checkpoint F6 dan checkpoint gabungan lama tidak berubah. Git diff whitespace check lulus. Tidak ada file staged atau commit F7.

## Gate tersisa dan koordinasi

1. Pengguna menilai preview/layout **halaman F7 ini**, bukan meminta ulang persetujuan fondasi/F6 yang sudah diberikan.
2. Tim backend menyepakati dan mengekspos kontrak field formula/input/hasil/revisi/immutable identity jika acceptance memerlukan keterlacakan versi. Setelah API nyata tersedia, jalankan integrasi terhadap payload sebenarnya; formula/status resmi tetap tidak boleh diasumsikan dari nama institusi.

Tidak mengerjakan backend atau memulai integrasi di luar izin frontend. Tidak commit F7, push, PR atau merge sampai izin terpisah diperoleh. Acceptance end-to-end dan pinned revision belum selesai meskipun tes frontend lulus.
