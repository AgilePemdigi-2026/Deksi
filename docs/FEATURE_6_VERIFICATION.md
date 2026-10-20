# Verification receipt — Fitur 6

Tanggal: 20 Oktober 2026, waktu host UTC+07. Branch lokal feat/detail-indikator, base fe `8fbfb7cc8198354f880d857acb1b5e6aea8c18fe`. Status: **frontend demo implemented and functionally exercised; official-data integration and visual acceptance pending**. Tidak ada commit/push/PR/merge.

## Runtime dan cakupan
PHP Laragon 8.3.26; Composer 2.8.4; Laravel terpasang 12.70.0; Node 24.13.1; npm 11.13.0; Vite terpasang 8.3.4. Dependency proyek lokal dipasang setelah izin eksplisit pengguna, tanpa instalasi global. Composer dijalankan dengan no-scripts/no-plugins; npm dengan ignore-scripts. App key dibuat hanya pada .env.local yang di-ignore dan tidak ditampilkan.

Tests menggunakan kernel HTTP Laravel aktual, JSON contoh tim dan fixture sintetis yang eksplisit. Database, API sumber resmi, model AI dan Docker tidak dijalankan. Temp fixture di scratch Hermes dibersihkan oleh finally. PHP views/cache/log berada pada storage runtime lokal yang di-ignore.

## Bukti awal (20 Oktober 2026, sebelum pemindahan lokasi)
Bagian awal dan tabel hash di bawah adalah catatan historis pada lokasi Frontend/. Saat itu belum ada commit/push/PR. Bukti revalidasi struktur terbaru dicatat terpisah di bagian akhir.

| Pemeriksaan | Hasil |
|---|---|
| Smoke php tests/indicator-detail.php | PASS, exit 0; akses/detail/demo/periode/histori dan penolakan klaim fixture |
| Regresi php tests/indicator-detail-regression.php | **26 skenario PASS, 0 FAIL**, exit 0 |
| npm run build | PASS, exit 0; CSS dan manifest dihasilkan |
| PHP -l | PASS pada 7 file PHP controller/repository/helper/routes/tests yang diperiksa |
| git diff --check | Exit 0; ada warning konversi LF/CRLF, bukan whitespace error |
| Route Laravel | GET/HEAD indikator/{kode}, nama indikator.show |
| HTTP nyata /dashboard | 200 |
| HTTP nyata /indikator/pdb | 200 |
| HTTP nyata /indikator/fiskal | 200, state history kosong |
| HTTP nyata /indikator/tidak_ada | 404 |
| Browser DOM detail | Judul/indikator sesuai, demo terlihat, SVG tersedia, tanpa href # |
| Browser klik kartu PDB | Berpindah nyata dari dashboard ke /indikator/pdb |
| Browser keyboard | Enter pada summary membuka tabel 18 baris; fokus terlihat |
| Browser viewport 360/768/1280 CSS px | Tidak ditemukan horizontal overflow halaman pada pengukuran DOM |
| Screenshot | Capture browser timeout; tidak ada screenshot final yang disahkan |

Regresi meliputi null vs zero, data hilang/JSON rusak/list salah/ID duplikat, escaping label, metadata parsial, unknown ID, enam detail demo, link dashboard, gap/null history, unit hilang, angka nonfinite, geometri ekstrem/konstan, empty state, navigasi tanpa dead link, 404 recovery dan integritas fixture lokal. Ini suite regresi tambahan, bukan suite BDD/Behat akademik atau bukti validitas data ekonomi.

Urutan tests-first terdokumentasi dalam keluaran sesi: route awal 404 → route/detail 200; demo disclosure gagal → lulus; histori aksesibel gagal → lulus. Regresi awal 14 pass/10 fail menunjukkan metadata/error/navigation belum lengkap; satu kegagalan pembanding bytes berasal dari perbedaan output shell Git dan diubah menjadi hash file sebelum/sesudah, bukan dengan mengubah fixture. Setelah perbaikan, 24 pass; penambahan pengujian dead link/404 recovery gagal 2 sebelum koreksi dan akhirnya 26 pass. Tidak ada assertion dilemahkan untuk menyembunyikan defect aplikasi.

Server HTTP awal dijalankan dari cwd yang salah sehingga router framework mencari index.php di root Frontend. Server itu dihentikan; server pengganti dijalankan dari public/ dan empat endpoint diverifikasi ulang. Masalah awal adalah setup verifikasi, bukan hasil aplikasi yang diterima. Pengujian browser awal juga perlu koreksi script scroll smooth dan escaping selector; hasil klik/Enter di atas berasal dari run yang berhasil, bukan asumsi dari markup.

Satu pengukuran localhost per endpoint (bukan benchmark/P95): dashboard 587,39 ms; detail PDB 523,15 ms; fiskal 430,94 ms; not-found 373,15 ms. Payload HTML berturut-turut 42747, 17946, 10035, 3880 bytes. Tidak ada target performa disepakati atau klaim scale/production readiness. Build memberi warning nonfatal __dirname pada konfigurasi Vite existing; tidak disembunyikan.

## Quality map berbasis ISO/IEC 25010:2023
Rujukan pengembangan saja, tanpa klaim sertifikasi/kepatuhan atau pemetaan klausul normatif.

| Karakteristik | Bukti / batas |
|---|---|
| Functional suitability | Detail, metadata tersedia, states dan navigasi diuji; angka/definisi/perubahan resmi yang belum tersedia tetap keterbatasan |
| Performance efficiency | Build dan pengukuran satu request localhost; load/latency acceptance belum disepakati |
| Compatibility | Laravel/Blade existing; integrasi API dan Docker tim belum diuji |
| Interaction capability | Native details, tabel alternatif, keyboard dan 3 viewport diuji; screenshot, kontras menyeluruh, zoom dan uji pengguna belum selesai |
| Reliability | 404/503, null/gap, malformed metadata diuji; last-valid-data backend tidak diimplementasikan |
| Security | Escaping dan tidak ada dead link pada detail; tidak ada audit menyeluruh, penetration test atau pengujian otorisasi backend |
| Maintainability | Lockfile, tests, helper geometri terpisah; perbaikan bootstrap minimum; belum review anggota tim |
| Flexibility | Enam kode existing dan variasi fixture parsial; bukan dukungan semua bentuk kontrak/data masa depan |
| Safety | Demo disclosure, tidak mengarang badge/kausalitas, null bukan nol; gate publikasi resmi tetap dependency backend |

29148: requirement fitur 6 ditelusurkan ke perilaku dan keterbatasan, bukan otomatis dianggap seluruh PRD lulus. 29119-2: hasil tes dan batas bukti dipisahkan; BDD executable akademik masih pending. 12207: implementation dan verification lokal dilakukan, validation tim/PO serta release belum dilakukan. 27001/42001 tidak dinilai sebagai sistem manajemen.

## Acceptance yang belum terpenuhi
- High-Fi detail yang benar: Figma gagal diakses; pada ekspor SRS Appendix C.1/C.2 terdapat gambar dashboard yang sama (rId39), bukan frame detail yang dapat diverifikasi.
- Screenshot final dan review visual/usability oleh pengguna/tim.
- Data resmi terverifikasi, definisi lengkap, nilai perubahan tervalidasi, jenis nilai, version binding dan workflow publikasi backend.
- Source Trace fitur 7 dan Grounded AI; tidak diimplementasikan.
- Docker menjalankan Frontend/: konfigurasi main sebelumnya menjalankan deksi/; tidak diubah.
- Renderer canvas interaktif dashboard existing belum tersedia; fitur 6 menggunakan SVG sendiri tanpa ketergantungan renderer tersebut.

## Hash sumber saat verifikasi (SHA-256)
| File relatif Frontend | Hash |
|---|---|
| app/Http/Controllers/IndicatorController.php | 9780c3f35e35e54bc06a42bfb7c371507fdab91844c2566ef7580d84af01ecf7 |
| app/Support/IndicatorHistory.php | 80a4496069a5915fad1a3eb5a39d1767bfa84526ca06c5359a56557600143b88 |
| app/Support/IndicatorRepository.php | c9ef13224c2b81546d6fee34fdce2dd01a3c2cdbb61a7ad81d2de421419531e2 |
| resources/views/indicators/show.blade.php | 04b2035383f03108b4f6495831dbdf1a8988715c8c943731166057e99aa826af |
| resources/views/components/indicator-history.blade.php | 0984b75a5d3f75c8a7871f00d96711891feeb78a2250ba4a38eff020ed566714 |
| tests/indicator-detail-regression.php | 02f211158d4401e61deb471940444c8126e0427dce2e808ffcf39fae773bfadb |

Batas integritas: git diff memastikan backend/, deksi/, Docker, Frontend/.env dan resources/data/indicators.json tidak diubah sebagai tracked source. Ini bukan seal seluruh filesystem/runtime. Receipt ini dan README hanya pencatatan setelah run; tidak memicu klaim eksekusi tes tambahan.

## Revalidasi sebelum PR — 21 Oktober 2026 (UTC+07)
Pengguna mengizinkan commit, push dan PR, tanpa merge. Fetch menemukan commit tim `85d7668` (penyesuaiaan lokasi frontend) pada fe: 28 file dipindahkan dari Frontend/ ke root tanpa perubahan isi. Integrasi dilakukan pada feature branch, bukan shared branch. Konflik file-location diselesaikan dengan mengikuti pemindahan tim dan mempertahankan perubahan fitur; tidak dibuat frontend duplikat. Ignore runtime serta dependency lokal dipindahkan ke root; environment lokal tidak dipublikasikan.

Dari root baru: Composer check-platform-reqs --no-dev PASS pada PHP 8.3.26; npm run build PASS; php tests/indicator-detail.php PASS; php tests/indicator-detail-regression.php **26 PASS / 0 FAIL**, exit 0. Build menghasilkan CSS 48,49 kB (gzip 11,57 kB); scope pemindaian Tailwind sekarang root monorepo. Ini pengukuran build, bukan benchmark atau jaminan performa produksi. Warning __dirname Vite existing masih nonfatal.

Tes ulang ini dilakukan karena lokasi aplikasi dan base integrasi benar-benar berubah, bukan untuk mengulang pengingat verifikasi. Source logic dipertahankan; sebagian hash byte berubah karena checkout/merge memakai CRLF. Tabel berikut adalah hash pada lokasi baru setelah tes:

| File relatif root frontend | SHA-256 saat revalidasi |
|---|---|
| app/Http/Controllers/IndicatorController.php | 26c06d2af6e8756e8d726742c02b5264ac754f191af44fea1e41a64c33f9c603 |
| app/Support/IndicatorHistory.php | 20a430a9faf0a260a13ce4ed92a15516ca4856c62f0c2248d983086d5adc3781 |
| app/Support/IndicatorRepository.php | c9ef13224c2b81546d6fee34fdce2dd01a3c2cdbb61a7ad81d2de421419531e2 |
| resources/views/indicators/show.blade.php | ed4c50e12aaf9af9e7e9a2c1d8b144e7bf0ff5a184d3c4958fce4394a713d386 |
| resources/views/components/indicator-history.blade.php | 741f7d28e2c8aee8787e8f6ba0147c76f6d5cd331082d20bbcaba45a23c794a2 |
| tests/indicator-detail-regression.php | 6f0ede55397a644f512380dc890bab9e5e84ccca66636b917d74c6872ec05975 |

Pengguna menyatakan tampilan lokal aman untuk dilanjutkan ke PR; itu bukan pengesahan fidelity terhadap frame High-Fi yang belum dapat dibaca. Status review High-Fi, data resmi/backend, fitur 7, Docker dan BDD akademik tetap seperti batas di atas. Kesiapan akhir masih review tim, bukan auto-merge. Catatan internal .hermes, .env.local, vendor, node_modules, build, storage dan log tidak termasuk perubahan PR.
