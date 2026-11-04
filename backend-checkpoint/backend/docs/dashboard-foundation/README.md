# Kontrak kandidat API dashboard — Batch 1

## Status dan batas kandidat

Implementasi lokal pada `integration/sprint-1-dashboard-be`, dasar BE7 `5c9e20de5d71d74d2c9aabcf00dbf85d04ee8fe3` yang mewarisi BE6 `14a4017ea9ee7499df64ea7dca111a6c0438359e`. Backend filter/feedback diadaptasi dari pekerjaan tim `f638bf8d5c40f91076caa893dac44d62a2049b88`. Perubahan belum commit/push/PR dan bukan pengganti branch fitur asli.

Kandidat hanya menyatukan API publik dashboard, filter, feedback dan dependensi fitur 6/7. Tidak menyalin frontend atau fitur sumber data Sprint 2 dari PR #23/#24; tidak memasukkan branch autentikasi Login/Reset. Integrasi seluruh backend/auth dan publikasi tim tetap gate terpisah. Rencana: [PLAN.md](PLAN.md). Hasil audit serta batas bukti: [AUDIT.md](AUDIT.md). Receipt: [VERIFICATION.json](VERIFICATION.json).

Dokumen ini menjelaskan kontrak implementasi kandidat, bukan respons hasil request ke data resmi, OpenAPI, bukti produksi, atau persetujuan desain. Seluruh pengujian memakai data sintetis dan settings terisolasi tanpa `.env`, provider atau database kerja.

## Endpoint yang dipakai dashboard

Semua path di bawah dipasang di prefix `/api/` oleh `backend/urls.py`. JSON sukses tidak dibungkus dalam properti `data`/`success`. Error view berupa `{ "error": "..." }`; penolakan CSRF/method dari Django dapat berupa HTML/plain text, sehingga frontend harus menangani status HTTP sebelum mengharuskan JSON sukses.

| Metode/path | Kontrak utama |
|---|---|
| GET `indicators/` | Ringkasan enam kode default; `code` boleh berulang untuk pilihan eksplisit. |
| GET `indicators/dashboard/` | Ringkasan dengan kategori/tahun; tambahan `activeFilters`. |
| GET `indicators/categories/` | `{ categories: [{ category, codes }] }`, katalog kategori kanonik tim. |
| GET `indicators/latest-periods/` | Ketersediaan periode terbaru per indikator; bukan kalender rilis. |
| GET `indicators/{code}/trend/` | Histori native atau agregasi backend melalui `granularity` yang terdaftar pada `granularities`. |
| GET `indicators/{code}/source-trace/` | Provenance nilai terbaru, atau konteks observasi tertentu dengan selector lengkap di bawah. |
| GET `indicators/{code}/raw-file/{raw_file_id}/` | Download RAW publik yang memenuhi ownership, batas ukuran dan integritas. Endpoint ini bukan proxy URL pengguna. |
| GET `system/update-status/` | `lastSuccessful`/`lastAttempt` dari log tersimpan. Timestamp sukses bukan bukti semua indikator berisi data atau mempunyai periode sama. |
| GET `feedback/categories/` | Kategori feedback, `csrfToken` dan cookie CSRF; tanpa login. |
| POST `feedback/` | Feedback anonim dengan CSRF yang valid; sukses 201 dengan `id`, `status=pending`, `message`. |

Jangan gunakan `status/` atau `system/bps-status/` sebagai polling dashboard: jalur tersebut dapat menjalankan probe provider BPS. Membuka dashboard tidak boleh memulai ingestion, sinkronisasi atau pemanggilan provider/AI.

## Identitas indikator

Kode API: `pdb`, `inflasi`, `fiskal`, `investasi`, `birate`, `tpt`.

Prototype menggunakan alias `apbn` dan `bi-rate`; adapter tampilan memetakannya ke `fiskal` dan `birate`. Alias bukan persamaan makna pengukuran. Nama, satuan, frekuensi dan `dataType` mengikuti API; jangan mempertahankan label rasio APBN `%` apabila respons backend adalah pengukuran/satuan lain. Backend tidak menambahkan endpoint alias diam-diam.

## Ringkasan dan filter tahun

Parameter filter: `category`, `year`, dan `code` berulang. Parameter tidak dikenal atau `category`/`year` berulang menghasilkan 400. `category` dicocokkan case-insensitive terhadap kategori tim; kategori tidak dikenal menghasilkan 400. Untuk kompatibilitas pekerjaan tim, kategori yang diberikan menentukan daftar kode, mengalahkan `code`. `year` opsional/kosong berarti terbaru; jika terisi harus digit ASCII tahun 1–9999. Frontend normal menggunakan label/kode dari endpoint kategori.

- Tanpa filter, payload sama dengan `indicators/`, selain `activeFilters: {}`.
- Dengan tahun, ambil observasi terakhir pada tahun itu yang `published` dan memiliki `reviewed_by` serta `reviewed_at`. Nilai terakhir di tahun lain tidak menjadi fallback.
- Nilai, satuan, sumber, tanggal, metadata publikasi/akuisisi, perubahan dan sparkline dibentuk bersama oleh `serialize_summary_card(indicator, year=...)`.
- Pembanding memakai sumber, satuan, frekuensi dan jenis data yang sama. Sparkline maksimal tujuh nilai sebanding, dibatasi sampai tanggal observasi terpilih; boleh mencakup tahun sebelumnya, tidak mengambil tahun setelah pilihan.
- Data belum tersedia memakai `available=false`, `value=null`, periode null dan catatan yang jelas. Sejumlah metadata hanya hadir pada kartu tersedia: frontend tidak boleh mewajibkan seluruh field saat kosong. Kode belum terdefinisi tetap kartu unavailable, bukan angka nol.
- `value` dan `changeValue` adalah string desimal. `changeUnit=percentage_point` berbeda dari `percent`; `changePercentage` null untuk perubahan poin persentase. Nol adalah nilai sah. Tidak ada interpretasi otomatis naik=baik/turun=buruk.
- `latestPeriod`/`latestYear`/`latestObservationDate` pada hasil filter mengacu ke observasi terpilih, bukan nilai terbaru global. Tahun aktif tercantum pada `activeFilters`.
- `hasCurrentYearData` dan `dataAvailabilityNote` berasal dari observasi terpilih; timestamp pembaruan global tidak menggantikan periode/rilis tiap indikator.

`sparkline` tetap array angka aproksimasi yang kompatibel, tanpa tanggal per elemen. Untuk grafik kalender dan deteksi gap gunakan histori bertanggal, bukan mengarang tanggal dari posisi array.

## Histori, detail, dan Source Trace

Tidak ada endpoint `/detail/` baru: frontend fitur 6 menggunakan data ringkasan, histori dan Source Trace yang tersedia. Histori mempertahankan `exactValue`, `sourceId`, `observationDate`, `frequency`, `dataType` dan satuan setiap titik. `value` numerik hanya aproksimasi koordinat; tabel/tooltip/ekspor mempertahankan desimal asli.

- Pilihan granularitas mengikuti respons backend. Tidak semua indikator mendukung bulanan/kuartalan. Backend menghitung agregasi dan menolak seri/metode yang tidak sebanding; frontend tidak menghitung ulang metrik ekonomi inti.
- Endpoint histori belum menerima filter tahun/rentang dashboard. Frontend menyaring baris native yang ditampilkan secara konsisten terhadap pilihan dashboard; `historicalAverage`/`historicalAverageExact` bukan otomatis rata-rata rentang yang dipotong frontend dan bukan target kebijakan resmi.
- Histori native dapat memuat sumber/semantik berbeda. Frontend harus memisahkan/menolak garis gabungan yang tidak sebanding, mempertahankan tabel dan memutus gap kalender yang teridentifikasi tanpa memasukkan nol palsu.
- Selector Source Trace harus memuat **keempatnya**: `observationDate`, `frequency`, `dataType`, `sourceId`. Semua diambil dari titik yang dipilih, bukan disubstitusi dari ringkasan terbaru.
- Selector parsial/tidak valid/berulang ditolak 400; konteks tidak ditemukan 404, ambigu 409. Tidak dialihkan diam-diam ke terbaru. Tanpa selector barulah API memilih terbaru.
- Histori trace memakai `limit` 1–100 (default 100) dan `offset` nonnegatif sesuai validator; total dan `hasMore` mengikuti observasi publik yang direview.
- `observationId` bukan versi immutable. `revisionId=null`, `immutableSnapshot=false`, `officialVerification=unassessed`; formula/input yang tidak tersimpan tetap unavailable. Checksum hanya bukti integritas berkas, bukan kebenaran angka resmi.

## Feedback: tanpa akun, bukan tanpa CSRF

Urutan browser yang diharapkan: GET `/api/feedback/categories/` → simpan token hanya di memori → POST JSON `/api/feedback/` dengan cookie yang sama dan header `X-CSRFToken`. Tidak perlu login/registrasi publik. Token tidak disimpan ke localStorage atau ditulis ke log.

Untuk Batch 2, gunakan jalur API same-origin/proxy yang dikonfigurasi secara eksplisit. Pengujian HTTP batch ini same-origin; keberhasilan lintas origin/browser belum dibuktikan. Jangan memperbaikinya dengan wildcard CORS atau mematikan CSRF. Bila origin berbeda diperlukan, tetap butuh allowlist/credentials/hostname cookie yang sesuai dan pengujian browser tersendiri.

| Field | Batas |
|---|---|
| `category` | Wajib; salah satu enum dari endpoint kategori. |
| `description` | Wajib; 10–2000 karakter setelah trim. |
| `sender_name` | Opsional; maksimum 150 karakter. |
| `sender_email` | Opsional; maksimum 254 karakter dan validasi email Django. |
| `related_indicator_code` | Opsional; maksimum 32 karakter, konteks advisory, bukan bukti indikator/versi terverifikasi. |
| `related_period` | Opsional; maksimum 50 karakter, tidak dikonversi menjadi tanggal/rilis. |

Body maksimum 32 KiB UTF-8; oversize menghasilkan 413. JSON non-object, duplikasi key, konstanta nonfinite, Unicode tidak valid pada field yang akan disimpan, tipe field bukan teks serta batas field yang dilanggar menghasilkan 400 tanpa penyimpanan. Field opsional yang tidak diberikan/null menjadi kosong; nilai terlalu panjang tidak dipotong diam-diam. Field `status`/`admin_notes` dari publik tidak mengendalikan model: tersimpan pending dan catatan Admin kosong. GET pada endpoint kirim ditolak 405; tidak ada daftar feedback publik.

IP diambil dari peer langsung yang valid, tidak mempercayai `X-Forwarded-For` tanpa kebijakan proxy. Log penerimaan hanya ID dan enum kategori, bukan teks/konteks/email/IP pengguna. Response sukses minimal dan `no-store`. Aksi perubahan status di Django Admin memerlukan izin `change_feedback`, bukan sekadar akun staff dengan hak lihat.

## Gate setelah Batch 1

- Port full dashboard React/Prototype 2, integrasi browser dan visual acceptance adalah Batch 2, belum selesai di sini.
- Data resmi/current database, PostgreSQL, deployment, anti-spam/rate-limit produksi, dan konsolidasi autentikasi belum diverifikasi oleh suite ini.
- Merge migration menutup percabangan feedback/provenance tanpa mengubah migrasi historis. Uji upgrade kedua jalur memakai database sintetis; migrasi tidak memperbaiki digit yang sudah hilang sebelum penyimpanan exact decimal.

## Recipe verifikasi lokal yang disetujui

Root worktree kandidat memiliki `.hermes/environment.json`. Jalankan `hermes verify --json` dari root worktree, bukan folder `backend/`. Recipe ini khusus backend Batch 1 pada mesin ini; interpreter existing ditulis eksplisit, tanpa instalasi atau perubahan profil/global.

Bootstrap memeriksa dependency/interpreter/port, build melakukan lint/check/drift migrasi, test menjalankan suite publik, lalu startup aplikasi WSGI Django dengan DB dalam memori di `127.0.0.1:55945`. Readiness memakai endpoint asli `/api/indicators/`. Server uji berhenti otomatis 20 detik setelah listening; ini bukan server development permanen atau konfigurasi deployment. Jika port sedang dipakai, preflight menolak; jangan menghentikan layanan lain untuk menjalankan recipe.

Run kanonik sudah berhasil dengan `ok=true`, exit 0 dan HTTP 200. Lihat bagian penyelesaian verifier di [AUDIT.md](AUDIT.md) dan bukti mentah pada `.artifacts/dashboard-foundation/canonical-full-raw.json` relatif folder backend. Batas data sintetis, satu tes symlink yang dilewati, serta gate frontend/produksi tetap berlaku.
