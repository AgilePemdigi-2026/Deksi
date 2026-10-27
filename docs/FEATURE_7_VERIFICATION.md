# Verification receipt — Fitur 7: Source Trace Data

Verifikasi lokal: 27 Oktober 2026, UTC+07. Branch `feat/7-source-trace`, base `origin/fe` pada `7b4e36f58fde3f8477f5b5b91ae1006be175f743`. Issue terkait: #12. Status: **frontend demo diimplementasikan dan diuji; integrasi API/data resmi, review visual pengguna, review tim dan integrasi main belum selesai**. Tidak ada commit, push, PR baru, merge atau perubahan issue dalam pekerjaan ini.

## Lingkup
- Route GET/HEAD publik: `/indikator/{kode}/sumber/{trace}`, nama `indikator.source-trace`.
- Lima ringkasan, enam tahap penjelasan alur, formula/input, metadata, transparansi dan riwayat revisi sesuai struktur CSS/screenshot High-Fi yang diberikan pengguna.
- Navigasi fitur 6 menuju Source Trace hanya untuk snapshot demo yang cocok. Kembali ke detail hanya aktif jika konteks masih cocok.
- CSS dibatasi `.source-trace-page`; dashboard/detail tetap memakai gaya tim. Footer khusus Source Trace, tidak mengganti footer halaman lain.
- Tidak mengubah `backend/`, `deksi/`, Docker, dependency manifests/lockfiles, credential, identitas Git, atau `resources/data/indicators.json`.

## Kontrak demo dan batas data
`resources/data/source-traces.json` adalah fixture demonstrasi terpisah. Dataset berisi enam snapshot yang mengulang nilai/periode/satuan pada dataset contoh indikator existing, bukan angka resmi baru.

Identitas: `id`, `indicator_code`, `version`, dan `snapshot`. Detail dicocokkan pada kode, periode, nilai, satuan, institusi dan label rilis; versi ambigu tidak dipilih otomatis. Trace lama dapat dibaca berdasarkan ID-nya, tetapi link kembali ke detail dinonaktifkan jika detail berubah. Pencocokan ini adalah batas frontend demo, bukan pengganti data-point ID dan revision identity dari backend.

Metadata: `data_type`, `publication_name`, `publication_url`, `fetched_at`, `formula_id`, `formula_version`, `formula_expression`, `formula_is_example`, `inputs`, `references`, dan `revisions`.

- Jenis nilai pada fixture belum diklasifikasikan, status verifikasi tetap belum terverifikasi.
- Formula PDB adalah ilustrasi metode YoY ADHK triwulanan, bukan bukti bahwa angka demo dihitung dari input resmi. Input numerik dan hasil kalkulasi backend tetap belum tersedia; frontend tidak menghitung angka inti.
- Publikasi spesifik, URL publikasi, waktu akuisisi dan riwayat revisi tidak direka. Tanggal rilis contoh tidak diubah menjadi timestamp pasti.
- Diagram alur menerangkan tanggung jawab tahapan, bukan bukti pipeline/review sudah dijalankan.
- Nilai resmi dan turunan memiliki rendering berbeda pada pengujian sintetis; tidak ada klaim verifikasi resmi atau tanda tangan kriptografis.
- Repository saat ini sengaja membaca fixture berstatus demo. Integrasi backend memerlukan kontrak dan pengambil data API yang benar, bukan mengganti label demo menjadi resmi.

## Runtime dan perintah
PHP Laragon 8.3.26 pada path interpreter yang telah diperiksa; Node 24.13.1, Vite 8.3.4. Dependency existing digunakan tanpa instalasi tambahan. Tes HTTP memakai kernel Laravel aktual, bukan PHPUnit/Behat. Set `DEKSI_TEST_SCRATCH` ke direktori scratch milik penguji sebelum suite fixture; temp fixture dihapus melalui finally.

```text
php tests/source-trace.php
php tests/indicator-detail.php
php tests/indicator-detail-regression.php
npm run build
php -l <controller, repository, routes, dan test terkait>
git diff --check
```

Perintah PHP dijalankan dengan executable Laragon terverifikasi, bukan asumsi PATH. Build menghasilkan CSS/manifest pada public/build yang di-ignore. Build memberi warning nonfatal konfigurasi existing `__dirname` pada Vite; konfigurasi tidak diubah atau warning disembunyikan.

## Hasil aktual
| Pemeriksaan | Hasil dan batas |
|---|---|
| Fitur 7, kernel HTTP | **37 skenario PASS, 0 FAIL**, exit 0 |
| Smoke fitur 6 | PASS, exit 0 |
| Regresi fitur 6 | **26 skenario PASS, 0 FAIL**, exit 0 |
| Vite build | PASS, exit 0, setelah CSS/view/navigasi selesai. Perbaikan PHP snapshot-binding sesudahnya tidak mengubah aset frontend |
| Syntax PHP | PASS untuk controller detail/source, repository Source Trace, routes, dan test; repository diuji lint ulang setelah perbaikan binding |
| git diff --check | PASS, exit 0 |
| Integrity boundary | Diff tracked pada dataset indikator existing, backend, deksi, Docker yang diperiksa serta manifest/lockfile dependency kosong |
| Browser Chrome terisolasi | **9 pemeriksaan PASS**, exit 0, setelah perbaikan terakhir |

37 skenario meliputi akses enam indikator, navigasi, 404/503, JSON/list rusak, identitas duplikat/salah, metadata parsial/tipe salah, null vs nol, escaping teks, lima URL berbahaya, tautan HTTP/HTTPS beratribut aman, klasifikasi official/derived/unknown, formula ilustratif, snapshot lama/ambigu, rilis berubah dengan angka tetap, kegagalan sumber yang tidak merusak detail, tanggal vs akuisisi, markup tabel/navigasi dan integritas/pembersihan fixture.

Ini suite regresi frontend tambahan, bukan pelaksanaan BDD akademik lengkap dan bukan pengujian ketepatan angka ekonomi.

### Bukti tests-first dan diagnosis
- Route publik: RED `expected HTTP 200, got 404`, lalu GREEN setelah implementasi.
- Link detail: RED `detail must link to its matching trace`, lalu GREEN setelah navigasi dihubungkan.
- Self-review menemukan angka tetap bisa memiliki metadata rilis berubah: reproduksi RED **36 pass/1 fail**, lalu perbaikan matcher memberi **37 pass/0 fail**.
- Skenario kontrol keamanan/parsial ditambahkan untuk memeriksa jalur implementation; tidak diklaim seluruhnya pernah RED.
- HTTP cold-start pertama melewati timeout klien 10 detik, lalu log server mencatat 200. Bukan hasil tes browser yang dianggap lulus.
- Percobaan browser pertama lulus empat viewport lalu gagal akibat quoting selector di harness (`ReferenceError: sumber is not defined`). Script verifikasi diperbaiki tanpa mengubah aplikasi untuk menutupi error; run berikutnya dan run setelah perbaikan binding lulus sembilan checks.

## Bukti browser aktual
Chrome dipanggil dengan profile scratch kosong terpisah, tanpa menyalin profile/kredensial pengguna, tanpa mematikan sandbox/web security. Tidak ada dependency browser baru.

1. Viewport 1280 CSS px: lima ringkasan, enam tahap, CSS aktif, radius 2px, demo jelas, tanpa overflow horizontal halaman.
2. Viewport 768 CSS px: checks struktur/overflow yang sama lulus.
3. Viewport 390 CSS px: satu kolom konten utama, checks struktur/overflow lulus.
4. Viewport 320 CSS px: checks struktur/overflow lulus; tabel memiliki wadah scroll sendiri.
5. Klik link aktual dari detail PDB menuju Source Trace dengan ID demo yang cocok.
6. Klik kembali dari Source Trace ke detail PDB.
7. Halaman inflasi menampilkan metadata/jenis nilai yang belum lengkap tanpa menebak formula.
8. Route trace tidak dikenal menampilkan 404; link pemulihan mencapai dashboard.
9. Event keyboard Tab pada browser memberi fokus ke link dengan outline solid 2px.

Screenshot hasil: `deksi-source-trace-1280.png` dan `deksi-source-trace-390.png` pada scratch sesi, disediakan sebagai preview pengguna. Font eksternal Google diblokir hanya pada browser QA terisolasi untuk menghindari dependensi jaringan; screenshot tersebut dapat menggunakan font fallback. Tidak mengklaim pixel-perfect typography, semua interaksi keyboard, uji screen reader, atau persetujuan visual pengguna.

Profile Chrome verifikasi telah dihapus (`profileRemoved: true`). Server PHP sementara pada port 8027 dihentikan setelah verifikasi. Aplikasi tidak dibiarkan sebagai layanan persisten.

## Pemetaan kualitas berbasis baseline ISO
Rujukan engineering baseline, bukan sertifikasi/kepatuhan formal atau asesmen klausul normatif.

| Karakteristik kualitas | Bukti / keterbatasan |
|---|---|
| Functional suitability | Alur detail/source, metadata dan state HTTP diuji; API resmi belum terhubung |
| Performance efficiency | Build berhasil; bukan benchmark beban atau jaminan latensi |
| Compatibility | Laravel/Blade existing, tanpa dependency baru; Django API/Docker belum diuji |
| Interaction capability | DOM responsif, Tab/focus dan tabel diuji; visual pengguna dan aksesibilitas menyeluruh pending |
| Reliability | 404/503/parsial, snapshot lama dan degradasi detail diuji; fallback backend belum dibangun |
| Security | Escape teks, validasi URL, tanpa server fetch URL sumber; bukan penetration test/audit backend |
| Maintainability | Repository/controller/view terpisah secukupnya, suite regresi dan receipt tersedia |
| Flexibility | Variasi official/derived/unknown diuji pada fixture, bukan janji seluruh kontrak masa depan |
| Safety | Demo eksplisit, input/hasil tidak direka, provenance salah tidak dipilih diam-diam |

Keterlacakan requirement dan bukti mengikuti baseline PRD F7-01–F7-06, issue #12 dan acceptance lintas halaman. Requirement publikasi/data resmi tidak dianggap lolos hanya karena frontend passing.

## Gate tersisa
- Review tampilan oleh pengguna terhadap High-Fi yang dikirim.
- API backend: kontrak data-point/revisi, payload metadata/formula/input, dan pembatasan data publik perlu disepakati dan diuji nyata.
- Data resmi dan sejarah revisi yang diverifikasi; tidak mengganti field kosong dengan contoh Figma.
- Review tim, BDD akademik bila diwajibkan, integrasi main/penyelesaian PR #9 dan Docker.
- Commit/push/PR fitur 7 hanya setelah izin terpisah; branch lokal belum dipublikasikan.

## Hash sumber saat verifikasi (SHA-256)
| File | SHA-256 |
|---|---|
| app/Http/Controllers/IndicatorController.php | d4df25fe0f4cabf81b09d5144292c5e93dab2d2106814e73ec069c119392d9bc |
| app/Http/Controllers/SourceTraceController.php | e34d66772fbf4c7bb11f4addc910f837451ae86ef77c126c393439d79b65b959 |
| app/Support/SourceTraceRepository.php | 41a8e2a3ddb7b81a8359cd319ec890bc8898ddec3c9e2b5cdd64800c67fa253f |
| resources/css/app.css | ce1ae1ef946c6b05a08d48213cb3c857689fb52b7c562007ad19d5abe13ec213 |
| resources/css/source-trace.css | 7c1b5828c57e6fe9ac28a6cfb569fce490c7e7132f813216319b70ef87ca9567 |
| resources/data/source-traces.json | 4aa10ca357956a297b4989078b5f5c1322fbf56b8408f1909d9f89f8aaf8d825 |
| resources/views/indicators/show.blade.php | 0943d404090017a67448199f822c3d3ccda6b550bc3c537734121fd1903f8a8f |
| resources/views/layouts/app.blade.php | 47a18f966e740900869b0c92a5033b0e7030b91e794370d423fc5690839c7a49 |
| resources/views/source-trace/show.blade.php | 871d0602a2a4039a9ce96fee892acc02f3bb04949e7cff1c5017dddc0f8d1071 |
| resources/views/source-trace/state.blade.php | 0c69e52dc94f23e125391813230aecd381cba30285d9dc224af38e5478e47d32 |
| routes/web.php | 708e0d618db233a90a4eddfdc3f4a64bb6173f976be5e4f3c41fb1a375a98af7 |
| tests/source-trace.php | 157d3d260c7bef8420664f7635375ca98e48afc2339b958b53eded95e7ec448a |

Receipt ini dibuat setelah run yang tercatat. Penulisan dokumentasi bukan run aplikasi tambahan dan tidak mengubah hasil historis menjadi klaim integrasi resmi.
