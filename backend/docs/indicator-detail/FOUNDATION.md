# Fondasi bersama fitur 6 dan fitur 7

**Status: PROPOSAL / keputusan skema PENDING_D1; belum ada model atau migrasi baru.** 27 Oktober 2026. Baseline main `21a065d3f145364a758aeec07571768a0ed29768`. [Kontrak F6](README.md), [mapping](contract.json), [acceptance](ACCEPTANCE.md).

## 1. Bukti skema dan dampak

| Source existing | Fakta | Implikasi |
|---|---|---|
| [models.py](../../apps/indicators/models.py), EconomicIndicator | Unit, type, name, description, methodology dan formula dapat berubah | Pinned detail tidak boleh join master terbaru untuk memberi makna angka lama |
| IndicatorDataPoint | Value Decimal(20,4), nullable; struktur period/layer; mutable; UUID | UUID point bukan immutable revision; value null bukan otomatis error/zero |
| IndicatorDataPoint publication_status | Status hanya pada working point | Tidak membuktikan manusia mereview konten revisi tertentu |
| SourceTrace data_point | OneToOne; point bisa belum memiliki trace | F6 harus bisa menyajikan snapshot angka yang sah dengan metadata sumber belum lengkap |
| SourceTrace version | String blank, tanpa sequence/histori | Label revisi institusi tidak boleh disintesis dari waktu/UUID |
| DataPoint/source/trace timestamps | Release_date, fetched_at dan internal created/updated/published berbeda | Jangan mengambil satu timestamp sebagai pengganti konsep lain |
| DataPoint unique_together | Quarter/month nullable dan tanpa revision | Bukan versioning; risiko ambiguity periode harus diperiksa pada PostgreSQL test sebelum mengklaim constraint aman |
| [initial migration](../../apps/indicators/migrations/0001_initial.py) dan [Admin](../../apps/indicators/admin.py) | Cascade parent dan fields ekonomi/provenance editable | Retention/edit policy baru berdampak jalur Admin tim; save override saja bukan DB immutability |
| trend fields | Value/percent/direction tanpa comparator/unit-kind/formula/input revision | Jangan langsung serialisasi sebagai perubahan terverifikasi |
| Data origin/frequency master/price concept | Tidak ada field origin, frekuensi master atau konsep harga/base year terstruktur | Capture harus eksplisit/unknown; jangan menganggap fixture atau label cukup |

Ini penilaian statik, bukan hasil DB atau bukti bahwa data duplikat/korup benar-benar ada. Model/migrasi belum diimpor/dijalankan. SourceTrace model belum menyimpan revision-bound reviewer atau evidence verifikasi angka.

## 2. Alternatif

**A. Live read API tanpa migrasi.** Boleh menjadi prototipe terbatas bila disetujui terpisah, tetapi harus menghapus janji konten pinned immutable, review per revisi, dan source binding historis. Tidak memenuhi keseluruhan invariant F6-07 ketika working record/master berubah. Jangan implementasikan A lalu menyebutnya B.

**B. Rekomendasi: satu shared revision snapshot.** Rancangan F7 lokal sudah mengusulkan `SourceTraceRevision`. F6 memakai **model kandidat yang sama**, bukan membuat `IndicatorRevision`/tabel snapshot kedua. Nama model tetap working name sampai review. Publication lifecycle terpisah dari frozen content; satu tabel bukan jurnal lengkap seluruh keputusan manusia.

Rancangan F7 berada lokal/untracked di worktree `source-trace-api`, belum masuk baseline ini dan belum disetujui. Paket F6 tidak mengubahnya; perselarasan di bawah adalah **delta yang perlu review bersama**, bukan klaim kontrak F7 telah diamendemen. Setelah disetujui, update satu spesifikasi canonical dan implementasi bersama sekali; jangan membiarkan dua proposal berbeda menjadi sumber runtime.

## 3. Delta minimum terhadap kandidat F7

| ID | Usulan selaras | Alasan / dampak |
|---|---|---|
| J1 | Shared `SourceTraceRevision` memiliki FK `data_point` PROTECT wajib, dan `source_trace` PROTECT nullable | Angka tanpa metadata trace tetap bisa punya revisi F6. Tidak membuat trace/institusi palsu untuk lolos FK |
| J2 | Sequence unik per data_point, previous_revision dari point yang sama; bukan per trace | Trace dapat baru tersedia belakangan. Old no-trace A dan trace-bearing B tetap satu lineage observasi; lock/alokasi sequence harus point-anchored |
| J3 | Snapshot menyimpan metadata F6 tambahan: short_name, category, definition dari description, methodology, point fetched_at | Pinned detail tidak mengubah definisi/type/unit/tanggal setelah master diedit. Semua berasal dari actual input, optional blank→null setelah review |
| J4 | Tambahkan slot nullable change pada schema snapshot yang sama, bukan tabel kalkulasi baru | Baseline slot null dengan warning. Kolom trend lama tidak cukup untuk mengisi evidence perubahan |
| J5 | F7 hanya menyajikan revision yang trace-nya ada dan cocok dengan point/indicator; F6 trace nullable | F7 UUID trace nonnull tetap berlaku pada respons F7. Revisi tanpa trace memberi source link null; ketika metadata datang, buat revisi baru, jangan edit A |
| J6 | Publikasi/review terikat shared revision; capture satu transaksi; data_origin direkam pada snapshot | F6 dan F7 tidak mengadopsi approval/status working row secara otomatis atau punya dua keputusan publikasi yang bertentangan |

J1/J2 mengubah proposal awal F7 (FK trace wajib, sequence per trace); **harus diterima dan direkonsiliasi sebelum kode shared model**, walaupun paket F7 belum diimplementasikan. Tidak menambahkan endpoint Source Trace atau membangun ulang halaman F7 dalam scope F6. FK point/trace dan identity snapshot divalidasi konsisten; PROTECT impact pada delete parent diuji sebelum dipakai tim.

## 4. Kandidat konten dan lifecycle

Usulan fields model: UUID id; FK data_point; optional FK source_trace; sequence; previous_revision; schema_version; snapshot JSON strict; created_at; publication_status default draft; reviewed_by/reviewed_at dan published_at sesuai policy tim. **Semua model/fields baru tetap PROPOSED.** Jangan menambahkan FK reviewer atau trigger tanpa persetujuan policy/retention.

Snapshot memuat:
- identity indicator/point/trace nullable/revision/sequence/schema/source_version nullable;
- indicator code/name/short_name/category/unit/data_type/definition/metodologi;
- observation period, value decimal string/null, layer dan actual point fetched_at;
- source metadata/date-only release/actual trace acquisition bila ada;
- data_origin explicit atau unknown;
- slot change null pada baseline F6; konten formula/input F7 tetap proyeksi allowlist yang sudah dirancang, bukan dump JSON legacy.

Snapshot JSON bukan framework versioning baru. Strict schema/version validator dan decimal validation wajib. Core identity/period/layer invalid gagal capture sebelum review. API read tidak menciptakan snapshot, review evidence atau row metadata. String/type yang tidak valid tidak diam-diam dicast menjadi nilai ekonomi.

### Perubahan dan pembanding

Untuk memenuhi F6-03 secara penuh kelak, minimal evidence change harus merekam: value decimal, kind (growth_percent/percentage_points/basis_points/absolute), unit yang sesuai, comparison period, comparator data_point/revision, formula ID/version dan calculation reference/input revision yang relevan. Satuan persen tidak otomatis berarti change adalah persen; pertumbuhan PDB yang sudah berupa rate berbeda dari nilai PDB sebagai input.

Kolom trend_value/trend_percent lama **tidak dipetakan** menjadi evidence tersebut. Saat ini `change=null`, `change_evidence_unavailable`. Jangan memanggil AI/engine, mengambil angka fixture frontend, menebak comparator dari previous array item, atau menghitung dari formatted string. Mendefinisikan/menjalankan metode kalkulasi dan menyimpan evidence memerlukan keputusan kontrak bersama PIC ekonomi, di luar read API Batch 2. Karena itu F6-03 end-to-end tetap dependency pending, bukan disebut PASS karena null aman.

Jika evidence baru disetujui kemudian, simpan dalam revisi baru dan review ulang. Comparator nonpublic tidak boleh bocor sebagai ID/nilai; aturan proyeksi/dependency lifecycle harus disepakati sebelum change diaktifkan. Jangan menambah field ke snapshot lama yang sudah disahkan lalu mewariskan review-nya.

## 5. Capture, review, retention dan fallback

1. Tidak membackfill otomatis data legacy menjadi published. Kandidat adopsi mengambil konten nyata/unknown origin, status draft dan review kosong. created_at adopsi bukan tanggal rilis atau revisi historis institusi.
2. Capture membaca point/master/trace dan evidence input dalam transaksi konsisten dengan urutan lock yang disepakati jalur penulis tim. Ini memerlukan review jalur Admin/pipeline: row lock service tidak melindungi edit langsung di luar protokol. Hindari signal otomatis setiap save dan seluruh engine baru.
3. Validasi point/trace/indicator ownership, period structure, layer↔type, decimal, URL dan enum; detail tanpa trace boleh partial jika publikasinya sah. F7 hanya aktif setelah trace-bearing revision dan endpointnya tersedia. Identitas point dipakai, bukan lookup periode nullable dengan `.first()`.
4. Perubahan content, schema, parent, sequence dan FK setelah capture dilarang melalui jalur aplikasi yang dijanjikan. `save()` override/readonly Admin tidak mencakup QuerySet.update, bulk operations atau direct SQL. **D2:** pilih batas perlindungan service/Admin saja atau juga database/SQL; jangan mengklaim DB-enforced bila tidak diuji.
5. Review/publish minimal lewat jalur terautentikasi, berwenang, atomik, mengikat exact revision dan actual reviewer/time. Tidak membangun UC-08 penuh, tetapi tanpa write/policy minimal API tidak boleh menganggap snapshot published sah. Desain journal/audit lifecycle lengkap belum termasuk.
6. Working/master edit, source is_active operasional, draft baru dan fetch failure tidak menghapus/menimpa revisi published A. New B default draft. Current memilih published sequence terakhir per point, lalu period terbaru dalam seri. Null pada periode baru tidak mundur ke A nonnull diam-diam.
7. Pencabutan publikasi/akses historis harus eksplisit. Jika A ditarik, pinned A generic 404 dan tidak dialihkan ke B. Content beku berbeda dari lifecycle akses; no-store awal, tidak menjanjikan public immutable cache.
8. Data RAW, raw_value, notes dan JSON internal tidak disalin ke proyeksi publik. Origin demo tidak masuk jalur produksi default. Bukti resmi/verified terpisah dari data_type=official dan status published.
9. Tes PostgreSQL harus membuktikan unique sequence, same-point parent, concurrency, rollback dan efek PROTECT cascade. SQLite atau static AST tidak membuktikan semantik locking/NULL PostgreSQL. Jangan menjalankan migrasi pada DB pengguna untuk memverifikasi desain.
10. Pengambilan data resmi dan pengisian approved revision milik pipeline/reviewer yang disepakati. Sampai ada data sah, empty/not-found jujur lebih baik daripada seed demo produksi atau fabricated timestamps.

## 6. Gate keputusan sebelum Batch 2

| ID | Keputusan yang dibutuhkan | Rekomendasi / belum otomatis diizinkan |
|---|---|---|
| D1 | Setujui shared snapshot B dan J1..J6; reconcile contract F7 canonical | Satu revisi point-anchored untuk F6/F7; migrasi additive setelah review, bukan tabel paralel |
| D2 | PIC/policy review minimal, siapa boleh publish, audit/retention dan batas immutability | Proteksi aplikasi/Admin minimal diuji, batas direct SQL dilaporkan; DB trigger/privilege bukan asumsi |
| D3 | DB PostgreSQL test terisolasi, interpreter/dependency dan izin setup | Bukan DB produksi, bukan env secret; perintah diverifikasi dari environment setelah izin |
| D4 | Mapping kode/seri/metrik ke FE dan target branch backend | API mempertahankan kode persis; tidak menebak pdb/rate/frequency dari fixture; tidak otomatis mengubah FE atau PR |

D1/D2 adalah keputusan arsitektur bersama, D3 prerequisite eksekusi, D4 koordinasi integrasi/publikasi. User "go batch 1" mengizinkan penyusunan rekomendasi ini, bukan menyatakan semua gate sudah accepted. Perintah migrate/install/test runtime belum diberikan karena environment test belum dipilih; Batch 2 tidak dimulai.
