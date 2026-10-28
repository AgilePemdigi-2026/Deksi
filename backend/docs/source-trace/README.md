# Backend fitur 7 — kontrak Source Trace

**Status awal Batch 1: PROPOSAL**, 27 Oktober 2026; saat itu belum ada izin implementasi. Sumber kode: branch `be`, commit `03052e3911966895456fd338300621c159ae30e4`. Branch kerja lokal: `feat/7-source-trace-api`.

**Pembaruan Batch 2–3:** implementasi lokal kemudian diizinkan dan sudah dibuat/diuji pada PostgreSQL test. Lihat [IMPLEMENTATION.md](IMPLEMENTATION.md) untuk perilaku aktual, 43 tes yang dieksekusi dan batas penerimaan. Uraian proposal/gate Batch 1 di bawah dipertahankan sebagai konteks desain awal, bukan klaim bahwa endpoint masih kosong saat ini. Team review, data resmi, integrasi frontend dan izin publikasi GitHub tetap terpisah.

## 1. Tujuan dan batas

Fitur 7 / UC-04 menelusuri **angka, indikator, periode, jenis nilai dan revisi yang sama**, dapat dibaca publik tanpa login. Fitur 6 tidak diubah. Tetap Django/DRF existing; tidak membangun Economic Engine, scraper/scheduler, AI, provider baru, workflow Admin lengkap atau database dari nol.

Dokumen paket ini:
- [contract.json](contract.json): rancangan terstruktur endpoint, mapping field dan requirement. Bukan OpenAPI/JSON Schema, konfigurasi aplikasi atau respons API aktual.
- [VERSIONING.md](VERSIONING.md): bukti keterbatasan skema dan usulan snapshot minimum; butuh persetujuan sebelum perubahan model/migrasi.
- [ACCEPTANCE.md](ACCEPTANCE.md): skenario pengujian yang belum dijalankan. Validasi dokumen tidak sama dengan tes API/database.

Otoritas produk: keputusan pengguna terbaru dan baseline lokal PRD F7-01 sampai F7-06, F6-07, Q-04 serta DECISIONS D-01/D-05/D-06. Paket baseline 20 Oktober masih menyebut scope frontend saja dan stack belum final; izin backend Batch 1 tanggal 27 Oktober dan inspeksi Django aktual mengatasi keterbatasan scope lama itu, **bukan** izin memindahkan seluruh dokumen baseline ke repo tim. Nomor `F7-BE-*` di sini adalah turunan acceptance teknis, bukan pengganti requirement produk.

## 2. Fakta kode, bukan hasil runtime

| Sumber relatif dari dokumen ini | Temuan yang diperiksa |
|---|---|
| [models.py](../../apps/indicators/models.py) | UUID indikator/data point/trace; decimal `(20,4)` dan nilai nullable; status draft/pending_review/published/rejected |
| [models.py](../../apps/indicators/models.py) | Satu `SourceTrace` untuk satu data point; metadata rilis, formula, input JSON dan label `version` |
| [0001_initial.py](../../apps/indicators/migrations/0001_initial.py) | Skema awal merefleksikan hubungan OneToOne, cascade dan unique_together periode; bukan bukti migrasi sudah diterapkan |
| [root urls.py](../../backend/urls.py) | Prefix `/api/v1/indicators/` sudah ada |
| [indicator urls.py](../../apps/indicators/urls.py) | `urlpatterns = []`; semua endpoint pada bagian berikut masih proposal |
| [settings.py](../../backend/settings.py) | Default permission `IsAuthenticated`, renderer JSON, paginasi 20; anonymous throttle 20/minute |
| [accounts/views.py](../../apps/accounts/views.py) | Pola respons `success`, `message`, `data`; fitur ini mengikuti pola sukses tersebut tanpa membawa token/profil Admin |
| [admin.py](../../apps/indicators/admin.py) | Hanya ID/timestamp yang readonly; provenance dan nilai belum dibekukan |

Tidak membaca credential/env. Versi dependency runtime, koneksi PostgreSQL, data produksi, implementasi review manusia, aplikasi berjalan dan CI backend **belum diverifikasi**.

## 3. Endpoint baca yang diusulkan

Semua kode indikator bersifat identitas persis; jangan case-fold/menebak kode dari label frontend. UUID harus valid dan hubungan parent diperiksa. `revision_id` adalah UUID snapshot DEKSI yang diusulkan, **bukan** label revisi resmi dari institusi.

| ID | GET path | Makna |
|---|---|---|
| current | `/api/v1/indicators/{code}/data-points/{data_point_id}/source-trace/` | Revisi **terpublikasi terakhir** pada data point yang diminta, bukan periode terbaru seluruh indikator; respons mengembalikan `revision_id` dan URL pinned |
| revision | `/api/v1/indicators/{code}/data-points/{data_point_id}/source-trace/revisions/{revision_id}/` | Membaca revisi tertentu; tidak fallback ke revisi lain |
| history | `/api/v1/indicators/{code}/data-points/{data_point_id}/source-trace/revisions/?page={page}` | Riwayat revisi publik data point yang sama; paginasi 20, descending sequence, UUID tie-breaker |

History adalah bagian keterlacakan F7-04, bukan daftar seluruh indikator atau endpoint perhitungan. Current merupakan convenience lookup; **jangan** memakainya untuk menautkan angka frontend yang sudah cached. Detail fitur 6 kelak harus mendapat `data_point_id`, `revision_id`, nilai dan URL pinned dari snapshot yang sama. Jika binding belum ada/tidak cocok, nonaktifkan tautan dengan keterangan; jangan menebak dari `pdb`, tahun atau nilai yang kebetulan sama. Route frontend lama dan fixture demo tidak otomatis menjadi ID backend.

`GET`, `HEAD` dan `OPTIONS` adalah metode baca yang direncanakan. `POST/PUT/PATCH/DELETE` ditolak 405 di endpoint ini; mutasi Admin tidak ditambahkan di sini. HEAD tanpa body; OPTIONS tidak boleh mengungkap serializer/internal Admin. Paginasi history memakai page positif; malformed page 400, out-of-range 404; tanpa page berarti page 1. Detail bukan respons paginasi.

## 4. Bentuk respons dan field

Envelope sukses: `success: true`, `message` teks umum, `data` objek detail atau objek history. Detail `data` memiliki `snapshot`, `publication`, `metadata`, `links`. Isi snapshot merupakan konten beku; publication merupakan keadaan lifecycle terkontrol, bukan bagian konten immutable. History memuat `count`, `next`, `previous`, `results`; item hanya `revision_id`, `revision_sequence`, `source_version`, `published_at`, `url`. Tidak memuat draft atau komentar reviewer internal.

Field di bawah berada relatif terhadap `data` pada respons detail. Semua field yang didefinisikan tetap hadir; nilai tak tersedia `null`, daftar kosong tetap `[]`. `contract.json` mencatat mapping per field, field hasil turunan serializer dan field yang membutuhkan skema baru.

| Kelompok | Isi dan aturan |
|---|---|
| `snapshot.identity` | UUID indikator/data point/trace/revisi; urutan revisi internal; schema version internal; label versi sumber nullable. Label versi sumber tidak dianggap unik atau dibangkitkan dari timestamp |
| `snapshot.indicator` | code, name, unit, data_type `official` atau `derived`, dibekukan saat snapshot; bukan join ke nama/unit/formula master terbaru pada saat GET |
| `snapshot.observation` | value sebagai decimal string atau null; data_layer; period `{type, year, quarter, month, label}`; tidak menghitung tren atau mengonversi unit |
| `snapshot.source` | institution_name/code, publication_name/url, release_date (date-only), fetched_at (timestamp aware); tidak menyalin `DataSource.last_fetched_at` sebagai waktu akuisisi observasi |
| `snapshot.official_value` | value/unit/period resmi dari trace, dipisahkan dari output observasi; tidak dijadikan nilai fallback untuk observasi atau input turunan |
| `snapshot.calculation` | null untuk official. Derived: formula ID/versi nullable, ekspresi dari trace, inputs tervalidasi; tidak fallback ke formula master terbaru dan tidak mengevaluasi ekspresi |
| `snapshot.data_origin` | `unknown` sampai asal data direkam eksplisit; `demo` untuk fixture; `official_source` hanya dengan asal tercatat, bukan karena domain URL. Label asal bukan klaim angka telah diverifikasi |
| `publication` | status `published` pada respons publik; published_at aktual nullable. Publication bukan status verifikasi matematika/resmi; reviewer, email, alasan internal tidak dikirim |
| `metadata` | status complete/partial dihitung dari field wajib pada proyeksi yang sah, missing_fields, warnings berkode. completeness flag tersimpan tidak dipercaya sendirian; verification_status tetap `unassessed` tanpa evidence verifikasi yang disetujui |
| `links` | relative path current, revision, history dan previous_revision nullable dibangun server berdasarkan identitas/akses publik tervalidasi; parent internal nonpublik tidak diungkap. Links adalah envelope dinamis, bukan konten snapshot beku. Jangan menggunakan Host/X-Forwarded-Host tak tepercaya untuk membangun URL sumber |

### Presisi dan nilai hilang

- `IndicatorDataPoint.value` dan `SourceTrace.official_value` tidak melewati float JSON atau rounding tambahan; gunakan string decimal sesuai skala penyimpanan empat digit. Nol menjadi `"0.0000"`; null tetap null. Jangan mengklaim presisi sumber di luar empat digit yang disimpan.
- Data periodik memakai fields period aktual. Annual: quarter/month null; quarterly: quarter 1–4 dan month null; monthly: month 1–12 dan quarter null. Payload legacy yang ambigu tidak ditebak; ditolak sebelum snapshot atau sebagai 503 bila invariant snapshot rusak.
- release_date `YYYY-MM-DD` atau null, tanpa jam fiktif. fetched_at hanya dari trace, timezone-aware ISO 8601 atau null; nilai timestamp naive/ambigu tidak diberi offset tebakan. published_at berarti publikasi DEKSI, bukan rilis institusi.
- Optional string kosong/whitespace dinormalisasi null tanpa menormalkan identifier. Period, angka, satuan dan metadata yang bertentangan tidak disatukan hanya karena nama mirip.

### Formula/input

`formula_inputs_detail` existing merupakan dict tanpa kontrak item; `EconomicIndicator.formula_inputs` hanya daftar kode. Keduanya **belum** membuktikan nilai, periode dan revisi input spesifik. Adapter penulisan snapshot kelak harus memvalidasi struktur input, bukan menyalurkan JSON mentah ke publik. Input minimal memuat key, label, value decimal string/null, unit, period, source_data_point_id dan source_revision_id; price_concept/base_year nullable jika relevan. ID sumber yang tidak layak publikasi tidak diungkap; field menjadi null dan warning tersedia. Semua input dihitung dari evidence tersimpan, bukan diperkirakan dari formula.

Jika input tidak dapat dipetakan, `inputs: []` dengan warning `formula_inputs_unavailable`; ini berarti **belum tersedia**, bukan bukti formula tidak memakai input. ID/versi formula belum punya kolom existing: null dan warning, jangan membuat ID dari nama indikator. Formula official tidak ditampilkan sekalipun kolom master kebetulan terisi. GET tidak melakukan perhitungan ekonomi atau memanggil AI.

### Partial vs invalid

Metadata parsial boleh 200 pada revisi yang memang sudah disetujui publikasi; missing ditandai. Publication review terpisah dari kelengkapan. Minimum identitas, ownership, jenis nilai/layer, struktur period, decimal yang valid, dan snapshot revision yang sah wajib; kerusakannya bukan metadata opsional. Published value boleh null jika observasi memang hilang; tidak boleh diisi nol. `metadata.status=complete` tidak sama dengan sumber dapat dijangkau atau angka resmi terverifikasi.

Missing fields dihitung deterministik, setidaknya untuk nilai/unit/period sumber yang tidak tersedia, institusi, publikasi/URL, tanggal rilis, akuisisi dan source_version; untuk derived ditambah formula ID/versi/ekspresi dan input yang belum tersedia. Tiap input yang belum lengkap dilaporkan dengan path indeks. Informasi tak relevan untuk official tidak ditandai hilang. Daftar rinci final dan struktur input harus dikunci pada implementasi serializer bersama skema yang disetujui; flag `is_metadata_complete=True` tidak cukup untuk melewati validasi ini.

## 5. Publikasi, keamanan dan kegagalan

- DRF view harus explicit `AllowAny`; rekomendasi authentication_classes kosong khusus endpoint baca supaya cookie/token Admin tidak diperlukan dan token malformed tidak mengubah endpoint publik menjadi 401. Jangan mengubah default global `IsAuthenticated`.
- Hanya snapshot dengan publikasi yang disetujui boleh dibaca dan masuk history. Draft/pending/rejected tidak boleh bocor meski peminta sedang login sebagai Admin di route publik. Identitas point, indikator dan revisi harus satu hubungan yang sama; jangan memakai `.first()` untuk mengatasi ambiguity.
- Layer RAW tetap internal dan bukan kandidat snapshot publik, meskipun status row legacy salah diset published. Snapshot publik hanya clean/derived yang sesuai jenis nilainya; mismatch tidak ditebak atau dipindahkan layer otomatis. Nilai resmi pada proyeksi publik bukan dump record RAW.
- **Gate skema:** backend sekarang hanya memiliki publication_status pada data point. Kontrak revisi ini membutuhkan status publikasi per snapshot dan proses review yang terikat snapshot. Jangan menganggap status point, default field atau isi fixture sebagai evidence persetujuan revisi.
- Draft baru, fetch gagal, sumber dinonaktifkan untuk akuisisi atau edit master tidak menghapus revisi publik terakhir. `is_active` sumber/indikator tidak disamakan diam-diam dengan pencabutan revisi; mekanisme penarikan harus eksplisit, ditinjau tim dan tidak diimplementasikan pada Batch 1.
- URL publikasi hanya absolute HTTP/HTTPS dengan host, tanpa userinfo/credential, control character atau backslash. URL tidak aman menjadi null dan warning; teks sumber tetap data, bukan HTML/instruksi. Tidak ada server-side fetch ke URL metadata, health-check sumber, redirect otomatis, atau klaim domain resmi hanya dari skema URL.
- Serialize allowlist; jangan kirim raw_value, notes/internal JSON mentah, last_fetch_message, identity reviewer, token, exception, connection string atau dokumen RAW. Frontend tetap escape teks dan rel aman untuk tautan eksternal.
- Detail/history awalnya `Cache-Control: no-store`; ini bukan janji immutable lifecycle HTTP. Konten snapshot tetap beku, tetapi status publikasi dapat berubah lewat proses review/penarikan. Jangan mengiklankan ETag atau cache immutable sebelum kebijakan lifecycle disepakati.
- Pertahankan throttle existing. Pemakaian Laravel server-side dapat berbagi IP pada limit anonymous 20/minute; koordinasikan caching/rate policy saat integrasi, jangan mematikan guard global atau mempercayai X-Forwarded-For dari pengguna.

| HTTP | Situasi | Body |
|---|---|---|
| 200 | Revisi publik lengkap/parsial; history untuk parent yang memiliki revisi publik, termasuk current | Envelope sukses |
| 400 | page query tidak valid | `success:false`, `message`, `error.code=invalid_request`, `data:null` |
| 404 | UUID/code tidak valid, parent tidak cocok, trace/revisi tak ada atau belum publik; page melewati akhir | Pesan generik yang sama, `error.code=not_found`; jangan membedakan keberadaan draft |
| 405 | Metode mutasi | `error.code=method_not_allowed`, tanpa mutasi |
| 429 | Throttle existing | `error.code=throttled`, Retry-After bila tersedia |
| 503 | Storage error, snapshot rusak/ambigu yang tidak dapat disajikan dengan aman | `error.code=source_trace_unavailable`; log internal tersanitasi, tanpa fallback demo |

Error envelope di atas adalah usulan fitur 7, bukan default DRF yang sudah dikustomisasi. Implementasi perlu adapter exception scoped pada fitur ini, termasuk resolver 404/405, dengan tes respons; jangan mengubah error global accounts. HTTP 500 lain yang tak terantisipasi tetap error server dan tidak boleh menjadi respons sukses. Empty/partial bukan alasan mengganti angka atau memilih periode/revisi lain.

## 6. Gate dan langkah setelah Batch 1

**D1 — Butuh keputusan pengguna/tim sebelum kode model:** setujui atau revisi opsi snapshot append-only pada [VERSIONING.md](VERSIONING.md), status publikasi per revisi, serta endpoint pinned/history. Tanpa itu jangan mengklaim versioned API selesai atau menjalankan migrasi. Jika hanya read API existing yang dipilih, kontrak harus diturunkan eksplisit menjadi live metadata tanpa jaminan histori, bukan tetap menjanjikan kontrak ini.

Batch berikut setelah izin: (1) model/migrasi minimum dan test penyimpanan pada database test yang disetujui; (2) serializer/view/URL/test API sesuai kontrak. Data resmi dan integrasi Laravel tetap gate terpisah. Tidak ada commit/push/PR pada Batch 1 ini.

## Referensi primer teknis

- DRF Permissions, bagian setting policy / AllowAny: https://www.django-rest-framework.org/api-guide/permissions/ (dibaca 27 Oktober 2026). Digunakan untuk pengecualian permission view, bukan izin membuka endpoint lain.
- PostgreSQL unique constraints: https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS (dibaca 27 Oktober 2026). Dipakai terbatas untuk penilaian nullable uniqueness dalam VERSIONING; versi server proyek belum diperiksa.
