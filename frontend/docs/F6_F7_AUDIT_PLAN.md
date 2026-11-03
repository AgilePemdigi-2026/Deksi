# Jalur B — audit dan rencana port frontend F6 → F7

Tanggal inspeksi: 2 November 2026, UTC+07. Status: **Batch 1 selesai; Batch 2 F6 diimplementasikan dan diuji; review visual dan izin checkpoint pending**.

Persetujuan sesi: pengguna menyatakan "oke kita buat front endnya dulu gapapa untuk backend nanti saja kita fokus fe nya dulu" setelah audit dan pembandingan gambar Source Trace. Scope tetap frontend dengan missing states jujur; bukan izin backend, fixture runtime, commit/push, atau otomatis menyetujui visual halaman baru. Gambar Source Trace dipakai sebagai referensi kelompok informasi, bukan mengganti fondasi editorial monokrom dengan tema biru. Dependency lokal boleh dipakai ulang melalui salinan paket existing yang lockfile-nya sudah dibandingkan identik; tidak ada install atau dependency baru.

## Tujuan dan batas kewenangan

Port perilaku Detail Indikator dan Source Trace dari checkpoint React lama ke fondasi editorial yang disetujui. Frontend publik, tanpa login. Tidak mengubah backend, Login, dashboard secara visual, identitas Git, checkpoint lama, dependency, database, atau pekerjaan sesi lain. Tidak commit/push/PR/merge. Tidak mengimpor hasil eksperimen akuisisi atau fixture sebagai fallback aplikasi.

## Baseline yang diperiksa

| Peran | Ref / HEAD | Hasil |
|---|---|---|
| Checkout utama | `E:/Deksi-Team`, `feat/7-source-trace`, `e11f4af099691f0efe9f7538020978ecde9c89de` | Checkout Laravel historis; bukan dasar React. Ada `.hermes/` untracked, dipertahankan. |
| Fondasi editorial | `feat/fe/editorial-baseline`, `505e97116f132c8630ec08d07525b8aec9e00536` | Worktree bersih; remote head cocok pada inspeksi; React/TS/Vite dan aset editorial. |
| Main remote | `0e92899ce54f85440fe920ca457dfd91f747e1aa` | Ancestor fondasi, belum memuat port editorial. Backend identik dengan fondasi menurut diff Git. |
| Backend integration ref | `be`, `c5c11553ffa2453a03f1a8a5b03ee42b214a6d58` | Berbeda dari main; fetch melaporkan ref berpindah dari sejarah lama. Tidak dipakai sebagai base atau digabungkan. |
| Checkpoint lama | `feat/6-7-react-detail-source-trace`, `cc738a8bdd7a9af44870c5480e61991050577094` | Worktree bersih, hanya referensi perilaku dan tes fixture. Tidak diubah. |
| F6 baru | `E:/Deksi-Team/.hermes/worktrees/feature-6-detail-fe`, `feat/6-detail-indikator-fe` | Dibuat dari fondasi tepat `505e97116f132c8630ec08d07525b8aec9e00536`; bukan dari Login. |
| F7 rencana | `feat/7-source-trace-fe` | Belum dibuat; menunggu checkpoint F6 yang dapat dijadikan dependency dengan izin terpisah. |

Origin diperiksa: `https://github.com/AgilePemdigi-2026/Deksi.git`. Tidak ditemukan AGENTS/CLAUDE/.cursorrules di tree fondasi atau parent worktree yang diperiksa; README dan `frontend/docs/EDITORIAL_PORT.md` dibaca. SOUL profil aktif dibaca tanpa perubahan. Fetch hanya memperbarui refs lokal, tanpa push atau perubahan branch kerja sesi lain.

## Item 1 — audit reuse dan API

### Perilaku lama yang dapat digunakan ulang

- `src/features/indicators/data.ts`: format desimal string tanpa kehilangan presisi, URL aman, validasi route, kecocokan konteks, geometri chart dengan gap/null, nol dan single-point. Adaptasi ke DTO aktual diperlukan.
- `DetailPage.tsx`: struktur nilai/periode/satuan, histori+tabel, pembanding yang disuplai backend, konteks sumber, disabled trace bila tidak cocok, akses publik.
- `SourceTracePage.tsx`: pemisahan metadata observasi/rilis/akuisisi, sumber, formula/input/hasil, revisi, dan return link yang menolak mismatch.
- `Shared.tsx`: metadata, tautan sumber, tampilan rilis date-only, serta loading/error/empty/not-found.
- `tests/data.test.mjs` dan `tests/pages.test.mjs`: skenario exact decimals, zero/null, missing history, gap/unit mismatch, URL tidak aman, escaping, no-latest-fallback, snapshot mismatch dan empty/error. Ganti input dengan DTO sintetis API sekarang; jangan memakai ID fixture sebagai ID backend.
- `tests/browser.test.mjs` lama: pola browser disposable dan alur pergi-kembali dapat diadaptasi. Endpoint intersep fixture dan assertion revisi demo harus diganti, bukan diperlakukan sebagai tes API nyata.

### Yang tidak boleh dipindahkan langsung

`loadDemoDataset`, `DEMO_URL`, `DemoDataset`, `public/fixtures/indicators-demo.json`, snapshot/trace/revision ID demo, banner contoh di runtime, global `base.css`, desain lama, App/index contoh, dan script package lama secara utuh. Old route `/indikator/:code/sumber/:traceId` mengandalkan trace ID fixture yang tidak ada pada API saat ini. App lama tidak memiliki kontrol pemilih periode; yang ada adalah pemilihan exact snapshot melalui URL. Kontrol periode menjadi adaptasi baru yang perlu dites.

Fondasi yang dipertahankan: `src/index.css` (Inter Tight/Archivo, paper/ink), aset `src/assets/editorial/`, dashboard JSX/layout, komponen editorial, disclosure, dan transport dashboard. `src/App.tsx` saat ini selalu memasang dashboard hook; routing fitur perlu mengisolasi mount dashboard tanpa mengubah tampilannya. `IndicatorCard` saat ini sengaja menonaktifkan Detail; aktivasi tautan merupakan wiring F6, bukan redesign.

### API yang benar-benar terdaftar pada kode backend baseline

Prefix `/api/` dari `backend/backend/urls.py`; views di `backend/indicators/views.py`.

| Endpoint GET | Tersedia menurut kode | Kekurangan untuk F6/F7 |
|---|---|---|
| `/api/indicators/?code=<code>` | Daftar/summary; `id` adalah kode indikator, nilai decimal string, periode, tanggal observasi, unit, category/name, source/sourceId, publicationDate, retrievedAt, delta backend | Latest saja; tidak menerima selector observasi/revisi; field tersedia berbeda pada empty; tidak memuat observation ID, revision ID, snapshot, definisi lengkap. |
| `/api/indicators/<code>/trend/` | Histori published; frekuensi native atau granularity didukung; native points memuat observationDate/frequency/dataType, value numerik; backend mengerjakan agregasi | Tidak memuat ID/source/revision setiap titik; angka grafik berupa float bukan exact decimal-string; titik agregat tahunan/bulanan kehilangan identitas native. Jangan dipakai membentuk snapshot atau menghitung delta frontend. |
| `/api/indicators/<code>/source-trace/` | Latest published: code/name, nilai decimal string, unit, period, observationDate/frequency/dataType, publicationDate, validationStatus/reviewedAt, source, rawFile opsional, history | Selalu latest, tidak memproses selector observasi/revisi dari query. `history` maksimum 12 baris observasi, bukan jurnal revisi; RAW yang checksum-nya berulang dapat menjadi null. |
| `/api/indicators/<code>/raw-file/<int:id>/` | Unduhan RAW terkait indikator published; kode memeriksa checksum file | ID RAW bukan observation ID/revision ID; checksum RAW bukan digest snapshot atau bukti angka benar. Tidak mengunduh file pada audit ini. |
| `/api/indicators/latest-periods/` | Metadata periode latest | Bukan resolver detail atau snapshot. |

Sumber kode penting: views summary 100–188, native points 265–277, trend 328–400, serialize trace 403–456, source-trace 459–476, RAW 479–504; models Observation 59–102. Model memiliki PK observasi tetapi tidak diserialisasi; tidak ada model/endpoint snapshot atau jurnal revisi pada fondasi ini. Jangan menganggap fondasi F6/F7 Django historis pada worktree/PR lama sebagai API React yang sekarang.

`dataType` (`level`, `yoy`, `cumulative_ytd`, `derived_sum`, `event`) adalah jenis data backend, **bukan field klasifikasi resmi/derived atau status verifikasi**. `validationStatus=published` ditampilkan sebagai status backend, bukan klaim independen verified. `publicationDate` date-only tidak dikonversi menjadi timestamp; waktu pembaruan pipeline bukan rilis observasi. Formula ID/versi/ekspresi/input/hasil, referensi terstruktur dan revisi tidak disediakan serializer ini. Histori tren tidak menjadi jurnal revisi. Field tidak tersedia tetap eksplisit kosong.

## Item 2 — kontrak navigasi yang diusulkan (frontend, bukan kontrak API baru)

### Konteks yang harus dipertahankan

`indicatorCode`, `observationDate`, `period`, `frequency`, `dataType`, `value` (decimal string sumber trace), `unit`, `source.sourceId`, seluruh metadata source yang tersedia, `publicationDate`, `rawFile` bila ada (documentName/sourceUrl/checksum/retrievedAt/downloadUrl), serta status/review timestamp bila ditampilkan. `observationId`, `revisionId`, `snapshotId`, dan `formula` tetap null/tidak tersedia: **tidak dibuat dari tanggal atau checksum RAW**.

Proposal route publik:

- Awal Detail: `/indikator/:code` = permintaan konteks terkini, bukan pinned snapshot.
- Setelah memilih konteks yang dapat dicocokkan: `/indikator/:code?tanggal=<ISO-date>&tipe=<dataType>&frekuensi=<frequency>&sumber=<sourceId>&konteks=<guard>`.
- Source Trace: `/indikator/:code/sumber` dengan query konteks yang sama; return link mempertahankannya persis, bukan kembali ke URL latest.
- `konteks` adalah digest frontend atas representasi deterministik konteks di atas, semata-mata **guard perubahan respons saat navigasi**, bukan ID backend, snapshot immutable, bukti kebenaran atau revisi resmi. Tidak menghitung metrik ekonomi. Implementasi menunggu persetujuan rencana ini.
- ID/code, tanggal, enum, digest, parameter duplikat, parameter konteks yang separuh, route lama/pinned revisi yang tidak didukung, dan origin/path unduhan harus divalidasi. Jangan memperbaiki token invalid atau mengabaikan `observasi`/`revisi` lalu menampilkan latest.

### Aturan resolver dan batas jaminan

1. Default Detail boleh membaca summary latest dan trend native. Jika source-trace tersedia, cocokkan konteks latest dengan summary sebelum menggabungkan metadata. Respons datang dari beberapa GET yang tidak atomik; mismatch menjadi state eksplisit, bukan dipilih salah satu diam-diam.
2. Pilihan periode detail berasal dari latest + baris `source-trace.history` yang memiliki konteks cukup dan tidak ambigu. Histori chart boleh lebih panjang, tetapi bukan janji setiap titik memiliki detail/sumber. Bila source-trace gagal, summary/trend yang sah tetap dapat ditampilkan; pemilih/pertautan yang membutuhkan konteks sumber dinonaktifkan.
3. Native trend point tidak mempunyai source/ID/revision: tidak dipromosikan sendiri menjadi identitas observasi. Agregat tren tidak diberi tautan ke sumber single-observation. Nilai detail exact berasal dari serializer summary/trace, bukan konversi float grafik.
4. Requested context hanya boleh di-resolve ke tepat satu kandidat current/history yang cocok; guard harus tetap sama. Nol kandidat, dua kandidat, perubahan nilai/unit/sumber/rilis/RAW, identitas salah, konteks di luar 12 histori, atau revision yang tidak didukung menghasilkan not-found/context-unavailable/context-changed. Tidak fallback latest. Server query yang diabaikan bukan keberhasilan pinning.
5. Metadata RAW null tidak diisi dari baris latest/observasi lain. Sumber boleh tetap tampil secara parsial; tombol RAW/sumber yang tidak aman atau tidak tersedia nonaktif. URL institusi dipisahkan dari URL publikasi/RAW.
6. F6 belum mengaktifkan tombol ke F7 yang belum terpasang. Helper kontrak dan pengujian boleh disiapkan pada F6; aktivasi endpoint frontend Source Trace dilakukan pada F7. Halaman F6 tidak mengimpor SourceTracePage agar dependency tetap satu arah.
7. Label kedua halaman: konteks cocok dengan respons yang tersedia, **tanpa jaminan revisi immutable**. Bila dataset berubah atau kandidat hilang, tampilkan batasnya dan jangan mengklaim observasi lama tetap dapat diambil.

### Koordinasi backend (proposal; bukan pekerjaan sesi ini)

Untuk jaminan pinned-version yang sesungguhnya, tim backend perlu mendefinisikan dan mengekspose identitas observasi, identitas snapshot/revisi immutable dan resolver exact selector, dengan pengikatan nilai/unit/periode/metode/sumber/review. Detail terpilih dan trace harus menggunakan identitas yang sama. Jangan menyebut endpoint/field tersebut sudah ada. Frontend dapat diselesaikan secara independen dengan guard konservatif dan state unavailable, tetapi acceptance pinned immutable tetap tertahan.

## Roadmap dua-item per batch

### Batch 1 — audit dan kontrak (sekarang)

1. Bandingkan source checkpoint, fondasi, endpoint serializer/models dan tes; simpan matriks reuse/gap serta pin Git. Selesai secara source inspection.
2. Tetapkan kontrak route/context/guard dan pemisahan branch; lakukan hanya GET lokal publik yang sudah diperiksa bebas ingestion, bila service tersedia. Simpan hasil observasi tersebut dan **berhenti untuk persetujuan rencana**.

Acceptance Batch 1: baseline/reference dipin; satu worktree F6 terisolasi; tidak membawa Login; kontrak aktual vs proposal vs fixture dibedakan; coverage/risiko/dependency tercatat. Tidak menjalankan test/build/install atau memodifikasi aplikasi pada batch ini.

### Batch 2 — F6, setelah persetujuan

3. Port komponen Detail + helper relevan ke style editorial; adapter API terpisah yang memvalidasi unknown DTO dan state partial; kontrol indikator/periode sebatas kandidat yang tersedia; histori native; field sumber dan pembanding hanya dari konteks yang benar. Route dispatcher memisahkan mounting dashboard; wiring tombol Detail tidak mengubah desain dashboard. Tidak ada fixture runtime.
4. RED→GREEN untuk kontrak/helper/pages, lalu uji alur F6 dengan synthetic response yang jelas hanya dalam tests, loading/empty/error/retry, zero/null, payload berubah, partial, rapid selection dan stale-response cancellation, URL invalid, konteks tidak cocok, histori single-point/gap/unit, keyboard dan breakpoint. Siapkan preview halaman Detail untuk persetujuan estetika. F6 tetap standalone sampai checkpoint diizinkan.

Acceptance F6: perubahan frontend terarah; dashboard/assets/fonts/transport behavior tetap; identitas dan missing states benar; tidak mengaktifkan route F7 mati; laporan fungsional/browser/build/lint/API/visual terpisah. Jangan menyebut integrasi penuh bila API belum dapat membuktikannya.

### Batch 3 — F7, setelah dependency F6 siap

5. Setelah artefak F6 dapat direview, **minta izin terpisah untuk commit lokal checkpoint F6 yang persis itu** (tidak sekaligus push). Buat worktree/branch `feat/7-source-trace-fe` dari checkpoint yang disetujui. Port SourceTracePage dan style scoped, gunakan DTO/guard F6, tampilkan formula/revisi tidak tersedia dan source metadata parsial secara jujur. Aktifkan navigasi F6 → F7 hanya setelah route F7 ada.
6. Uji pergi-kembali dan reload/deep-link dengan exact context guard, berubah nilai/unit/sumber/rilis/RAW, candidate ambigu/hilang, selection historical di luar coverage, serta route revision unsupported. Diff F7 dihitung **terhadap commit dependency F6**, sehingga tidak mengulang seluruh patch F6. Preview F7 perlu review visual tersendiri.

Acceptance F7: payload dan nilai konteks konsisten atau explicit refusal; formula tidak direka; history observasi bukan revisions; no latest fallback; diff F7 hanya tambahan Source Trace/wiring/tests/docs. Penerbitan branch/PR tetap izin terpisah; target PR tidak ditetapkan otomatis sebagai fe/be yang tertinggal.

## Kepemilikan file (target setelah persetujuan; bukan file yang sudah diimplementasikan)

| Kelompok | File kandidat | Pemilik/batas |
|---|---|---|
| Kontrak/helper/adapter F6 | `frontend/src/features/indicators/{types.ts,data.ts,api.ts,Shared.tsx}` | F6: nama diadaptasi dari checkpoint; jangan memindahkan loader demo. |
| Detail dan styling | `frontend/src/features/indicators/DetailPage.tsx`, scoped `features.css` | F6; gunakan tokens fondasi, jangan menyalin base.css/global theme lama. |
| Routing dan pintu dashboard | `frontend/src/App.tsx`, `frontend/src/components/{EconomicSummary,IndicatorCard}.tsx` | F6: hanya dispatch/mount dan href/context; markup/desain dashboard dipertahankan. |
| API base bersama | `frontend/src/api.ts` | Usulan **export konstanta API_BASE saja** agar adapter F6 memakai origin yang sama; tidak mengubah hook/transport dashboard. Kebutuhan ini termasuk gate rencana. |
| Source Trace | `frontend/src/features/indicators/SourceTracePage.tsx`, CSS scoped | F7; perubahan route registry di App dan aktivasi link terarah. Tidak mengubah bisnis F6. |
| Tests/docs | `frontend/tests/{data,pages}.test.mjs` yang diadaptasi atau suite fitur terpisah, browser suite terarah, `frontend/package.json` scripts bila perlu, `frontend/docs/` | F6/F7 masing-masing memiliki evidence; tidak menimpa test browser editorial dengan suite lama. Tidak upgrade lock/dependency. |
| Terlindungi | `backend/`, Login branch/worktree, checkpoint gabungan lama, `src/index.css`/aset editorial/layout dashboard | Tidak diubah; backend hanya dibaca. |

## Rencana verifikasi (belum dijalankan)

Manifest fondasi sudah diperiksa:
- `npm test` sekarang hanya menjalankan `node --test tests/editorial.test.mjs`; **tidak otomatis mencakup suite port F6/F7**.
- Sesudah file tes fitur ditambahkan/adaptasi: jalankan eksplisit `node --test tests/data.test.mjs tests/pages.test.mjs` dari frontend, atau script fitur yang disetujui, di samping `npm test` editorial. Nama final disesuaikan artefak; jangan mengklaim suite ini sudah ada di worktree F6 baru.
- `npm run build` = `tsc -b && vite build`; `npm run lint` = `oxlint`; warning historis tidak dihapus untuk memperoleh hasil tampak bersih.
- `npm run test:browser` sekarang khusus editorial; pertahankan dan tambah suite browser fitur terpisah. Browser executable harus ditemukan, profile disposable milik tes, scratch eksplisit `C:/Users/Pongo/AppData/Local/hermes/cache/scratch`; jangan bergantung TMPDIR atau menutup browser pengguna.
- Functional browser checks mencakup actual navigation/back/deep-link, interaksi keyboard, chart synthetic bila ada, loading/error/empty/partial/mismatch, serta responsive overflow. Synthetic interceptions bukan bukti Django/API live.
- Screenshot preview disediakan untuk review halaman baru. Visual optional/expanded QA setelah arah disetujui; mandatory functional checks tetap terpisah. Persetujuan dashboard/Login tidak otomatis menyetujui Detail/Source Trace.
- Tidak memasang dependency pada audit. Periksa runtime/dependency lokal sebelum menjalankan tahap berikut; jika instalasi diperlukan, koordinasikan izin, jangan menjalankan npm ci implisit dari README.

## Bukti Batch 1 dan gate

**Sudah dilakukan:** membaca source/manifests/test setup; verifikasi Git lokal/remote; fetch refs tanpa merge; membuat worktree F6 dari base tepat. Tidak ada PASS aplikasi yang diklaim dari dokumen atau hasil historis.

**Probe API lokal aktual:** tiga GET ke `http://localhost:8000/api` untuk `/indicators/?code=inflasi`, `/indicators/inflasi/trend/`, dan `/indicators/inflasi/source-trace/` sudah dicoba pada 2 November 2026 sekitar 21:50 UTC+07, tanpa credential/proxy dan dengan timeout/body cap. Ketiganya mengalami `ConnectTimeout`; tidak ada respons payload live untuk divalidasi. Ini bukan bukti endpoint tidak diimplementasikan atau seluruh deployment tidak tersedia. Kontrak tabel di atas dibuktikan dari source yang dipin, bukan hasil respons live. Tidak memanggil status/BPS health/ingestion/RAW/AI, karena beberapa status endpoints menjalankan koneksi provider. Tidak menyalakan Django, membuka database atau membaca .env. Rincian dan hash sumber disimpan di [receipt Batch 1](F6_F7_BATCH1_EVIDENCE.json).

**Hasil Batch 2:** implementasi dan pengujian F6 tercatat di [handoff F6](F6_FRONTEND_HANDOFF.md) dan [receipt F6](F6_FRONTEND_VERIFICATION.json). Tidak mengubah receipt Batch 1 menjadi bukti implementasi atau API live baru.

**Gate berikut:** review visual F6 dan izin terpisah commit lokal checkpoint F6 yang diidentifikasi di handoff sebelum membuat dependency branch F7. Publikasi, acceptance F7 dan end-to-end tetap gate terpisah. Tidak ada commit/push/PR saat penulisan handoff ini.
