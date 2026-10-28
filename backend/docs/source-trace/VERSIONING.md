# Penilaian versioning — backend fitur 7

**Status awal Batch 1: PROPOSAL**, berdasarkan inspeksi statik 27 Oktober 2026 atas `be` commit `03052e3911966895456fd338300621c159ae30e4`; model/migrasi saat itu belum dijalankan. [Kontrak](README.md), [mapping field](contract.json), [acceptance](ACCEPTANCE.md).

**Pembaruan Batch 2–3:** pilihan B diimplementasikan lokal setelah izin pengerjaan berikutnya, dengan FK point/indicator PROTECT tambahan, digest konten dan satu keputusan terminal per revisi. Model/migrasi telah diuji hanya pada PostgreSQL test. Detail hasil dan batas direct SQL/team approval ada di [IMPLEMENTATION.md](IMPLEMENTATION.md). Pernyataan model belum ada dan gate di bawah adalah assessment historis Batch 1, bukan status implementasi terkini.

## 1. Bukti dan dampak

| Temuan aktual | Lokasi kode baseline | Dampak / batas bukti |
|---|---|---|
| `SourceTrace.data_point` OneToOne | models.py:239–244; 0001_initial.py:135 | Satu row provenance sekarang per point; bukan satu row per revisi |
| `version` CharField blank | models.py:278 | Label saja, tidak ada unique/order/parent/review binding; dua label sama atau kosong bukan histori |
| value/period/layer ada di IndicatorDataPoint; type/unit/formula ada di master | models.py:90–113, 155–191 | Membekukan trace saja tidak membekukan angka dan maknanya |
| SourceTrace dan DataPoint punya updated_at | models.py:218–219, 280–281 | Waktu edit tidak memulihkan isi sebelum edit; bukan changelog |
| Admin metadata dan angka editable | admin.py:22–35 | readonly ID/timestamp tidak melindungi versi lama; bukan bukti sudah ada write yang salah |
| FK cascade dari indikator ke point, point ke trace | models.py:148–151, 239–242 | Penghapusan parent berpotensi menghapus provenance; perlu retention policy sebelum snapshot publik |
| published hanya status pada point | models.py:187–192, 216 | Tidak membuktikan review manusia, tidak membedakan review A dari revisi B |
| unique_together period menyertakan quarter/month nullable | models.py:226; 0001_initial.py:94 | Bukan model versioning. Pada default uniqueness PostgreSQL, NULL dapat membuat lebih dari satu kombinasi tampak sama lolos; ini risiko statik, belum direproduksi pada DB proyek |
| DataSource.is_active / indicator.is_active | models.py:53, 115 | Flag operasional, bukan mekanisme pencabutan publikasi historis |
| Tidak ada kolom asal demo, formula ID/versi, immutable snapshot atau evidence verifikasi | kelas terkait pada models.py | Jangan mengarang field/asal dari nama institusi; null/unassessed sampai tersedia |

README model menyebut Detail UC-03, sedangkan baseline produk pengguna memetakan fitur 6 pada UC-02. Paket ini mengikuti baseline produk; komentar kode tidak diubah dalam Batch 1.

Referensi nullable uniqueness: dokumentasi PostgreSQL bagian Unique Constraints (dirujuk pada README paket). Jangan mengubah unique_together existing hanya untuk menyimpan revisi; snapshot dipisahkan dari periode. Pengetatan nullable period constraint merupakan keputusan kompatibilitas/data-cleanup terpisah bila diperlukan. Selalu lookup memakai UUID point dan validasi ownership, tidak `.first()` menurut periode.

## 2. Alternatif dan rekomendasi

**A — Tanpa migrasi:** read API terhadap model sekarang dapat dibuat untuk live metadata. Harus menyatakan histori tidak tersedia dan tidak mengklaim snapshot immutable. `version`, UUID point dan URL saja tidak menjamin nilai/metadata lama tetap. API ini tidak memenuhi keseluruhan F7-04/F6-07 bila master/point diedit. Tidak direkomendasikan sebagai kontrak versioned final.

**B — Rekomendasi: satu model baru `SourceTraceRevision` untuk konten snapshot dan lifecycle publikasi.** Biarkan tabel/master existing serta OneToOne tetap sebagai working/current record. Jangan mengganti seluruh pipeline atau memasukkan frontend ke branch ini. Buat satu row snapshot untuk satu kandidat revisi; setelah dibuat, konten tidak dapat diubah. Metadata review/publikasi terpisah dari konten beku dan hanya berubah melalui proses terkontrol yang disetujui.

Pilihan B adalah **usulan**, bukan persetujuan migrasi. API pada README mengasumsikan B disetujui dan pembatas publikasinya tersedia. Jangan diam-diam mengimplementasikan A lalu menyebutnya B.

## 3. Sketsa model minimum untuk direview (belum kode)

| Field kandidat | Tujuan |
|---|---|
| id (UUID) | Revision ID internal; bukan release ID institusi |
| source_trace (FK PROTECT) | Hubungan revision ke trace dan point existing; beberapa revisi per trace |
| sequence (positive integer) | Urutan per trace, unique `(source_trace, sequence)`; tidak berasal dari label versi sumber |
| previous_revision (self FK PROTECT, nullable) | Lineage internal; parent harus trace sama dan sequence lebih kecil; bukan histori rilis resmi yang ditebak |
| schema_version (positive integer) | Versi struktur snapshot internal |
| snapshot (JSON, strict schema) | Frozen indicator ID/code/name/type/unit; point ID, value/layer/period; trace ID; source/publication/release/fetch; official value/unit/period; formula/input refs; source_version; data_origin |
| created_at | Timestamp pencatatan internal, bukan acquisition/release time |
| publication_status | Default draft, never auto-published; status per revisi, tidak mengambil status point terbaru sebagai otorisasi publikasi |
| reviewed_by (FK AdminUser, nullable, PROTECT) dan reviewed_at | Binding review ke revisi ini; tidak dikirim ke publik. Tambahkan hanya sesuai aturan akses/tim dan kebijakan retensi yang disetujui |
| published_at | Waktu publikasi DEKSI yang benar-benar terjadi, nullable sebelum publikasi |

`SourceTraceRevision` tidak ada pada baseline. Nama/tipe final model dan field diputuskan sebelum migrasi. Snapshot JSON dipilih agar kolom ekonomi existing tidak diduplikasi besar-besaran; konsekuensinya validasi schema, decimal strings, URL dan referensi input wajib. JSON bukan izin menyimpan raw secrets/HTML atau output AI tak tervalidasi.

Publication metadata **bukan append-only** pada sketsa ini; kontennya yang immutable. Jika tim membutuhkan audit penuh setiap keputusan review/penarikan, riwayat keputusan harus tersedia dari workflow review tim atau desain jurnal terpisah yang disetujui. Jangan menyebut satu tabel ini sudah menyediakan jurnal review lengkap. GET tidak mengubah status dan tidak menciptakan evidence review. Tidak ada endpoint publik untuk menulis review.

## 4. Invariant penyimpanan dan penerimaan yang diperlukan

1. Capture angka, period, type, unit, sumber dan formula/input dalam transaksi konsisten; gunakan pembacaan terkunci atau strategi konsistensi yang sesuai setelah code path penulisan tim diketahui. Jangan join master yang berubah saat melayani snapshot.
2. ID indicator/point/trace pada JSON harus cocok dengan hubungan FK. UUID revision dan sequence internal bukan sumber kebenaran nilai; source_version yang tidak ada tetap null.
3. Larang perubahan snapshot, schema_version, parent, sequence dan FK setelah pembuatan di service serta Admin. ORM update/bulk update dan akses SQL perlu strategi eksplisit; `save()` override saja **tidak** membuktikan immutability database. Tentukan apakah trigger/DB privilege diperlukan sebelum mengklaim perlindungan terhadap direct SQL; jangan menambahkan trigger diam-diam.
4. Isi/referensi snapshot harus lolos validasi sebelum dapat direview. Metadata opsional kosong boleh ditandai partial. Content changed berarti revisi baru dan review baru; approval A tidak boleh dibawa ke B.
5. Publikasi hanya melalui aksi terautentikasi/berwenang yang mengikat reviewer, waktu dan revision tertentu. Memiliki `publication_status=published` saja belum membuktikan proses review benar. Mekanisme write/policy review minimal adalah gate dengan tim, bukan pembangunan UC-08 lengkap di endpoint baca.
6. Current memilih sequence terbesar **di antara published revisions**, bukan row draft paling baru. Current lookup dan response menggunakan revision yang sama, tidak membaca ulang latest setelah serialisasi dimulai.
7. Metadata/angka master terbaru, draft baru atau akuisisi gagal tidak menimpa A. Pinned A mengembalikan konten A; history hanya menampilkan revisi yang diizinkan publik. Parent internal nonpublik tidak diungkap sebagai UUID/URL publik; parent publik terdekat boleh ditunjukkan tanpa mengklaim sebagai parent rilis institusi.
8. PROTECT revision→trace plus perlindungan Admin/service perlu diuji terhadap penghapusan trace, point dan indikator berantai. Soft-disable akuisisi bukan delete. Penghapusan/pencabutan untuk kebutuhan legal bukan bagian batch ini; memerlukan kebijakan tersendiri.
9. Alokasi sequence dan validasi parent diuji pada transaksi bersamaan: unique constraint wajib, retry konflik terbatas. Foreign key self tidak sendiri menegakkan same-trace/acyclic; validasi domain dan tes wajib. Jangan mengandalkan test SQLite untuk menyatakan locking/NULL PostgreSQL benar.
10. GET read-only, input tidak dievaluasi sebagai kode, tidak server-side fetch URL. Public output hanya allowlist dan tetap membedakan metadata completeness, review publikasi dan verifikasi angka.

## 5. Adopsi data existing dan kompatibilitas

Tidak melakukan backfill otomatis ke published snapshot. Proses adopsi yang kelak disetujui membuat kandidat dari row yang ada dengan source_version asli/null, origin unknown bila tidak ada evidence, review binding kosong dan status draft. created_at baru berarti waktu adopsi, **bukan** timestamp revisi historis sumber. Angka/metadata lama yang sudah tertimpa tidak dapat direkonstruksi dari updated_at atau label version.

Nilai null tetap null; precision maksimum existing empat decimal tidak dinaikkan dengan mengarang digit. Jangan mengubah fixture frontend menjadi data resmi, jangan menamai snapshot baru sebagai `v1` sumber jika label tidak ada. Migrasi awal baru seharusnya additive; rollback dan data retention perlu diuji pada database test sebelum dipakai tim. Jangan menjalankan migrate pada database pengguna untuk sekadar membuktikan rancangan.

Workflow Admin/pipeline existing harus tetap kompatibel. Snapshot baru tidak terbentuk diam-diam dari signal setiap save, dan tidak otomatis mengubah status atau menghapus working data. Form publikasi/aksi review paling kecil perlu direncanakan bersama PIC Admin; jika tidak tersedia, API versioned tetap tidak boleh dinyatakan siap publikasi. Perlindungan penghapusan baru merupakan perubahan perilaku yang perlu disetujui tim.

## 6. Keputusan yang belum diberikan

**D1 — Setujui/revisi pilihan B, endpoint pinned/history dan aturan review per revisi.** Konsekuensi: satu tabel snapshot tambahan, migrasi additive, validasi dan pembatas edit/delete; integrasi aksi publikasi minimal harus terkoordinasi. Persetujuan untuk membuat dokumen Batch 1 tidak otomatis menyetujui D1.

Sebelum kode, identifikasi PIC/policy review dan database test yang dapat dipakai, lalu pilih batas immutability (Admin/service saja atau juga DB/direct SQL) dan audit perubahan lifecycle. Jangan mengisi keputusan itu dengan asumsi atau membuat framework audit baru. Implementasi API baca tidak membutuhkan akses ke database produksi atau pemasangan dependency baru tanpa izin.
