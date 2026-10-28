# Acceptance backend fitur 6

**Semua skenario API/database: NOT RUN.** Batch 1, 27 Oktober 2026; rancangan berbasis main `21a065d3f145364a758aeec07571768a0ed29768`. [Kontrak](README.md), [field/requirement terstruktur](contract.json), [fondasi/gate](FOUNDATION.md). Validasi dokumen tidak mengubah status tes berikut menjadi PASS.

## 1. Matriks requirement dan skenario

| ID | Requirement baseline | Skenario dan expected behavior | Bukti implementasi kelak |
|---|---|---|---|
| F6-BE-01 | F6-01, Q-04 | Anonymous GET bekerja untuk revisi publik tanpa token/session; malformed token tidak mengubah view publik menjadi login; HEAD body kosong; OPTIONS aman; mutasi 405 tanpa write | API/permission/DB before-after, NOT RUN |
| F6-BE-02 | F6-01, F6-07, Q-04 | Code persis, invalid UUID, cross-indicator/point/revision, unknown/draft/rejected/nonpublic selalu generic 404 tanpa bocor nama/keberadaan internal; tidak fallback ke indikator/version lain | API/security, NOT RUN |
| F6-BE-03 | F6-02 | Decimal ekstrem/negatif/zero/missing, four-place scale, field optional kosong; zero string bukan null, null bukan zero; tidak float atau parsing Rp/%; definisi hanya dari konten reviewed | Serializer/API, NOT RUN |
| F6-BE-04 | F6-02, F6-04 | Annual/quarterly/monthly tervalidasi; frekuensi campuran perlu pilihan, query invalid/duplikat/unknown 400; period_type optional hanya bila satu public frequency; duplicate period dan unit/type mismatch gagal aman, RAW excluded | Query/DB/API, NOT RUN |
| F6-BE-05 | F6-03 | Isi trend_value/percent lama tidak membuat change semu; change=null + warning bila comparator/formula evidence absent. Bila kontrak change kelak diaktifkan: masing-masing kind/unit/comparison/input revision diuji, comparator private tidak bocor | Contract/API baseline; metrik lengkap dependency pending, NOT RUN |
| F6-BE-06 | F6-04 | Satu published revision per point; histori ascending, pagination fixed 20, count/links akurat dan scope seri sama; supplied null dipertahankan; bulan/kuartal/tahun yang hilang memutus grafik tanpa zero fill; empty page1 vs out-of-range benar; jangan klaim as-of/cross-page snapshot | Query/API dan adapter grafik terpisah, NOT RUN |
| F6-BE-07 | F6-05 | Tanpa fakta kausal tidak ada penjelasan penyebab/kontribusi; teks berbahaya tetap data; tidak ada AI call, private diagnostic evidence atau raw formula inputs dalam respons | API/allowlist/no-outbound, NOT RUN |
| F6-BE-08 | F6-06 | Observasi, rilis date-only, point/trace fetched_at dan internal publication tidak tertukar; updated_at/request time tidak dipakai sebagai rilis/freshness; ambiguous timestamp tidak diberi offset tebakan; origin unknown tidak dipromosikan verified | Serializer/API, NOT RUN |
| F6-BE-09 | F6-07 | Detail–trace menggunakan point/revision sama; data tanpa trace tetap dapat tampil sebagai published partial snapshot; source link null bila trace/endpoint tak tersedia; trace datang kemudian menjadi revisi baru, bukan mengubah A; no fake metadata | Storage/API/integrasi F7, NOT RUN |
| F6-BE-10 | F6-07, Q-03 | Edit master/working value/trace atau tambah draft B tidak mengubah pinned A/current public A; latest observation ditentukan period bukan updated_at; published latest null tidak mundur ke angka nonnull. Pinned history berbeda konteks diberi null link+warning; revision revoked generic 404 | Storage/publication/API, NOT RUN |
| F6-BE-11 | Q-03 | Optional source/definition/change missing boleh 200 partial; valid selected frequency tanpa rows pada indikator publik boleh 200 history page1 kosong; no public identity 404; storage/invariant failure 503 bukan empty/demo; unanticipated 500 bukan sukses | API/fault injection, NOT RUN |
| F6-BE-12 | Q-04 | raw_value, notes, fetch errors, reviewer, credentials dan input JSON internal tidak keluar; unsafe URL (javascript/data/userinfo/control/backslash) null + warning; URL HTTP(S) valid tidak di-fetch; text tetap escaped oleh FE | Serializer/API/FE security, NOT RUN |
| F6-BE-13 | Q-04, Q-05 | AllowAny hanya view baca; account/Admin tidak ikut terbuka; throttle existing dan 429/Retry-After; no-store; GET tidak memutasi point/snapshot/review; invalid queries tidak menulis atau menembus private data | API/regression/DB, NOT RUN |
| F6-BE-14 | F6-07, Q-05 | Shared model tunggal; J1..J6 disetujui; unique sequence per point, valid same-point parent, point/trace FK binding dan PROTECT; concurrency/capture konsisten; content frozen dan review baru saat perubahan. Batas direct SQL sesuai D2 diuji/dilaporkan | PostgreSQL/storage/Admin/migration, NOT RUN |
| F6-BE-15 | F6-02, F6-04, F6-07, Q-05 | Laravel detail nyata membaca API; exact code mapping, decimal display presisi dan geometry conversion finite terpisah; missing period memutus garis; last response/context berbeda tidak menukar indikator; pinned source tepat; outage bukan silent fixture fallback; dashboard anggota lain tetap | Integrasi FE–BE/browser, batch berikut, NOT RUN |

`contract.json` menyimpan ID dan baseline mapping yang sama. Keseluruhan F6-03 belum terpenuhi hanya karena fallback null benar; validitas metrik, sumber resmi dan review data adalah gate terpisah.

## 2. Batas akses publik dan data test

- Gunakan fixture sintetis berlabel pada database test terisolasi; tidak mengimpor JSON demo FE menjadi data resmi, tidak auto-publish data legacy/produksi.
- Tes draft/pending/rejected, published tetapi RAW, point berbeda pada period sama, mixed type/unit, missing trace dan metadata malformed. Status pada working row tidak meloloskan snapshot tanpa review binding.
- Gunakan real ORM/query dan Django/DRF test request; mock hanya outbound/failure yang perlu diisolasi. Pelanggaran period/decimal/ownership yang core bukan normalisasi optional metadata.
- Sumber resmi tidak diakses saat GET atau test; kegagalan situs eksternal tidak menghapus konten snapshot yang sudah valid. Tidak menjalankan string formula atau provider AI.
- Database error tidak dianggap cache fallback; read API tidak menciptakan histori/snapshot/review pada request. Tabel counter row/hash/publication diperiksa sebelum/sesudah GET.

## 3. Kualitas dan bukti proporsional

Kerangka mengacu ISO_QUALITY lokal (draft), bukan sertifikasi atau klaim normative compliance. Teks penuh standar tidak ditinjau pada batch ini; tidak membuat threshold kinerja/klausul baru.

| Karakteristik kerangka kualitas | Risiko/evidence pada lingkup ini |
|---|---|
| Functional suitability | F6-BE-01..10: nilai/semantik/seleksi/pinned tepat |
| Performance efficiency | Histori bounded, no AI/source fetch, ukur query count/payload/latency aktual setelah implementasi; budget belum ditetapkan |
| Compatibility | Kontrak decimal/period/identity/links dan J1..J6 bersama F7; F6-BE-15 |
| Interaction capability | Field/warnings memungkinkan label parsial dan tabel; browser/keyboard/readability tetap tugas FE yang harus diuji terpisah |
| Reliability | F6-BE-10/11: published terakhir tetap, null/partial/error tidak tertukar |
| Security | F6-BE-01/02/12/13: public projection, no RAW/private/SSRF/mutasi |
| Maintainability | Satu model shared, explicit source mapping, scoped errors dan test command/receipt aktual |
| Flexibility | F6-BE-03/04/08: optional metadata, frekuensi valid dan unsupported semester tidak ditebak |
| Safety | F6-BE-05/07/09/14: data demo, review, angka/metode dan sumber tidak diklaim verified tanpa evidence |

## 4. Urutan implementasi setelah gate

1. D1 shared snapshot J1..J6 dan D2 policy/owner protection harus diterima; D3 interpreter dan DB test diizinkan. Tidak meminta secret dalam chat; konfigurasi dilakukan melalui cara aman yang disepakati.
2. Periksa manifest/runtime/test settings aktual dan pilih perintah runner resmi. Kandidat framework adalah Django test runner, **belum dieksekusi dan belum dikunci command/interpreter/DB**. Jangan menyebut test php lama sebagai bukti backend atau menjalankan migrate terhadap DB pengguna.
3. RED untuk satu jalur versioned detail/public boundary; implementasi storage/service minimal; GREEN. Lanjut serializer/query/detail/history/pinned secara vertical slices, lalu relevant regression accounts dan storage. Tidak menulis semua endpoint sebelum tes pertama.
4. Pada PostgreSQL test: migration forward/rollback yang relevan, transaction/concurrency, nullable duplicate period dan PROTECT. SQLite atau AST tidak cukup untuk menyatakan semantik DB lulus.
5. Jalur HTTP nyata Django + database test: public detail/histori/pinned, unknown/nonpublic/storage error. Simpan command, exit, actual counts dan payload yang tidak sensitif.
6. Integrasi Laravel dan browser F6-BE-15 setelah API tersedia; jangan mengubah dashboard atau fitur 7 tanpa scope tambahan. Rate/cache server-side dan code/series mapping dibahas sebelum wire-up.

## 5. Verifikasi Batch 1 dan stop

Batch 1 hanya memvalidasi JSON, ID, mapping terhadap AST, prefix dan policy source, tautan lokal, keselarasan desain F7, scope file dan hash source yang diproteksi. Ini **document/static validation**, bukan API/security/migration/runtime PASS dan bukan kesepakatan semantic contract.

Receipt lokal: `.hermes/receipts/feature6-backend-batch1.json` pada worktree ini. Stop setelah struktur paket valid dan perubahan hanya dokumen. Jangan membuat endpoint/model/migrasi, install dependency, menjalankan DB/server, commit/push/PR/merge. Keputusan berikut tetap D1..D4 pada FOUNDATION; human design review dan sprint acceptance tidak diambil alih validator.
