# Implementasi dan verifikasi backend fitur 7 — Batch 2–3

Status saat penutupan Batch 2–3, sebelum publikasi GitHub: **implementasi lokal selesai dan pengujian di bawah lulus; belum integrasi frontend atau produksi**. Status commit/push/PR setelah tahap itu mengikuti branch/PR GitHub, bukan snapshot laporan ini. Pekerjaan pada `feat/7-source-trace-api`, base `be` commit `03052e3911966895456fd338300621c159ae30e4`, worktree `E:/Deksi-Team/.hermes/worktrees/source-trace-api`. Izin melanjutkan Batch 2–3 dan penegasan branch terpisah berasal dari pengguna dalam chat. Ini izin implementasi teknis, bukan review tim atau verifikasi angka ekonomi.

## 1. Batch 2 — storage dan review minimum

- `SourceTraceRevision` serta migrasi additive `0002_source_trace_revision` menyimpan snapshot angka/period/unit/type/institusi/publikasi/rilis/akuisisi/formula/input. Working tables existing tidak ditulis ulang dan data lama tidak otomatis dipublikasikan.
- FK trace, point dan indikator memakai PROTECT untuk menjaga identitas/retensi. Dua FK point/indikator dan `content_sha256` merupakan detail penguatan proposal Batch 1; bukan model revisi kedua. Sequence unik per trace; parent harus trace sama dan mendahului revisi baru.
- Capture memakai transaksi dan row lock; mengalokasikan sequence dari satu trace secara serial. Pembacaan angka, master dan trace dikunci sebelum snapshot dibuat. Origin default unknown, bukan official_source dari nama institusi.
- Model save, default QuerySet update/delete/bulk dan Admin edit/delete dibatasi. Hash membantu mendeteksi perubahan konten; **bukan bukti autentisitas sumber atau validasi angka**, dan bukan perlindungan terhadap SQL/ORM berprivilege yang sengaja melewati guard. Tidak memasang trigger atau mengubah privilege DB.
- Review adalah satu keputusan terminal draft→published atau draft→rejected, menggunakan user staff aktif dengan permission `indicators.publish_sourcetracerevision`, exact content digest dan row lock/CAS. Approval tidak diwariskan. Tidak ada reopen/revoke/pending-review workflow lengkap pada scope ini.
- Admin SourceTrace menyediakan aksi capture draft. Admin revision read-only menyediakan aksi publish/reject eksplisit dan menggunakan LogEntry Admin existing. Ini bukan jurnal review append-only umum atau pengganti UC-08 lengkap. Tidak ada review/publish publik.

## 2. Batch 3 — API publik baca

| GET | Perilaku |
|---|---|
| `/api/v1/indicators/{code}/data-points/{data_point_id}/source-trace/` | Revisi publik terakhir untuk point tersebut |
| `/api/v1/indicators/{code}/data-points/{data_point_id}/source-trace/revisions/{revision_id}/` | Exact revision tanpa fallback latest |
| `/api/v1/indicators/{code}/data-points/{data_point_id}/source-trace/revisions/?page=1` | Riwayat publik, page size 20, descending sequence/id; count+page dihitung pada satu statement PostgreSQL |

AllowAny dan authentication kosong hanya pada view fitur ini; global accounts tetap IsAuthenticated. GET/HEAD/OPTIONS tanpa mutasi, metode tulis 405, malformed token tidak menghalangi akses publik. Semua respons view memakai no-store. Throttle existing dipertahankan, termasuk 429/Retry-After. Invalid/missing/private identity generic 404, query invalid 400, kerusakan/storage error 503 tersanitasi. Suffix tak dikenal di bawah namespace source-trace mendapat JSON 404 scoped, tidak mengubah error accounts/global.

Serializer memvalidasi struktur/digest dan hanya mengeluarkan field allowlist. Null bukan nol; decimal string empat digit, rilis date-only dan waktu akuisisi dipertahankan. RAW atau type/layer mismatch tidak dapat dicapture menjadi snapshot publik. Metadata partial tidak berarti verified; verification_status unassessed. Tidak menghitung ekonomi/mengevaluasi formula, memanggil AI atau melakukan fetch URL sumber.

Legacy formula-input JSON bukan passthrough. Adapter mengenali dict `schema_version: 1` dengan formula_id/formula_version dan inputs strict; input malformed/struktur tak didukung menjadi inputs kosong dengan warning. Formula berasal dari trace, bukan master mutable terbaru. Formula ID/version yang belum direkam tetap null. Snapshot maksimum 128 KiB, maksimum 100 input dan bounds text/decimal/schema divalidasi; ini batas implementasi, bukan bukti kinerja pada beban produksi.

Referensi input hanya ditampilkan bila revisi sumber publik, point sesuai, digest valid dan value/unit/period yang diberikan cocok dengan snapshot sumber. Input privat/invalid tidak diungkap sebagai ID atau nilai; ditandai warning. **Konten tersimpan immutable, tetapi proyeksi input yang perlu disembunyikan serta links/lifecycle bersifat access-aware**: respons keseluruhan tidak dijanjikan byte-immutable/HTTP immutable. Previous link memilih revisi publik sebelumnya, melewati parent internal nonpublik. Ambiguitas beberapa lineage trace untuk satu point gagal aman 503 pada current/history; exact pinned yang sah tetap terbaca.

## 3. Verifikasi yang benar-benar dieksekusi

Interpreter project: `backend/.venv/Scripts/python.exe`; Django 6.1.2, DRF 3.18.3, psycopg2-binary 2.9.13. PostgreSQL test 17.6, loopback 127.0.0.1:59477, owned data directory pada scratch `deksi-f7-postgres/data`, bukan database aplikasi pengguna. Requirement manifest tidak ditambah.

Perintah berikut dijalankan dari `backend/`, dengan konfigurasi test standalone yang tidak memuat .env/credential aplikasi:

- `DEKSI_TEST_PG_PORT=59477 .venv/Scripts/python.exe manage.py test --settings=backend.test_settings --noinput -v 2` → **43 tests, OK, exit 0**.
- `DEKSI_TEST_PG_PORT=59477 .venv/Scripts/python.exe manage.py makemigrations --check --dry-run --settings=backend.test_settings` → **No changes detected, exit 0**.
- `DEKSI_TEST_PG_PORT=59477 .venv/Scripts/python.exe manage.py check --settings=backend.test_settings` → **no issues, exit 0**.
- `git diff --check` → **exit 0** pada sumber tracked saat pemeriksaan.

Suite default tersebut menemukan seluruh tes Python yang tersedia pada checkout ini, yaitu tes fitur 7 yang ditambahkan. Bukan bukti seluruh fitur produk sudah diuji. Skenario termasuk:

- storage/identity/null/decimal/date/schema, immutable default write paths dan PROTECT;
- otorisasi review, digest salah, keputusan terminal tidak dapat ditimpa;
- **PostgreSQL nyata**: dua capture bersamaan, dua keputusan review bersamaan (hanya satu commit), constraint sequence, migration reverse/reapply pada test DB tanpa mengubah working rows;
- anonymous current/pinned/history, draft/new working changes tidak mengganti publikasi lama, cross-parent/private generic 404, source-input confidentiality, error/corrupt snapshot, no outbound URL/AI, mutation denial, throttle, pagination dan accounts authentication boundary;
- **LiveServerTestCase melalui HTTP/TCP loopback nyata**: current/pinned/history 200, private revision 404 dan POST 405; bukan hanya mock/DRF test client.

RED yang sempat diamati sebelum perbaikan: penerimaan published/identity salah pada model parsial; capture/review belum tersedia; route current/pinned/history 404; validasi bool/URL bertipe salah; input privat bocor; Admin actions belum ada; legacy ambiguity dipilih sebagai 200 dan suffix 404 masih HTML. Fixture label periode yang terlalu panjang diperbaiki sebagai error harness, bukan diklaim bug aplikasi. Semua tes akhirnya lulus dengan assertion keamanan dipertahankan.

Logs dan receipt source/test hashes lokal: `.hermes/receipts/batch23-*.log` dan `.hermes/receipts/feature7-backend-batch2-3.json` pada worktree. File .hermes, .venv, cluster/binary PostgreSQL dan credential tidak menjadi kandidat publikasi. Receipt ini tidak mengubah hasil historis Batch 1 menjadi tes backend saat itu.

## 4. Batas selesai dan handoff

- Migrasi hanya diuji pada database test milik batch; **belum diterapkan ke DB aplikasi/produksi**. Reverse migration menghapus tabel revisi; jangan memakainya sebagai rollback data publik produksi tanpa rencana retensi.
- Runtime test HTTP dikelola/dihentikan oleh test runner; cluster PostgreSQL test dihentikan setelah verifikasi. Tidak menjanjikan server preview backend tetap menyala.
- Frontend fitur 6/7, fixture frontend dan PR #15 tidak diubah. F7-BE-14 (binding Laravel nyata), data resmi, review manusia atas data sebenarnya, visual acceptance, deployment dan CI remote tetap pending.
- Batas SQL/privileged ORM dan workflow lifecycle yang lebih luas tetap eksplisit; bukan klaim database-enforced immutability atau keamanan produksi menyeluruh.
- Integrasi shared model dengan backend fitur 6 perlu review kontrak bersama saat dikerjakan; tidak mengubah worktree fitur 6 milik sesi lain.
- Pada penutupan Batch 2–3 belum ada commit, push, PR, merge atau perubahan pada shared branch be. Publikasi berikutnya membutuhkan izin pengguna dan mengikuti jalur feature branch → PR ke be, bukan direct push. Pembuatan PR tidak berarti izin merge atau deployment.
