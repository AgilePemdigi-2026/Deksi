# Fitur 6 backend — implementasi Batch 2

**Status: implementasi lokal untuk Draft PR ke `be`; bukan production-ready atau sprint acceptance.** Scope: Detail Indikator publik, histori antarperiode dan pinned revision. Bukan dashboard fitur 3/4, backend Source Trace, engine perhitungan, AI atau integrasi Laravel. Branch fitur: `feat/6-indicator-detail-backend`, base `be` commit `03052e3911966895456fd338300621c159ae30e4`.

Kontrak [README](README.md), [contract.json](contract.json), [FOUNDATION](FOUNDATION.md) dan [ACCEPTANCE](ACCEPTANCE.md) adalah **baseline rancangan Batch 1** bertanggal 27 Oktober 2026. Status PROPOSAL/NOT RUN di dokumen historis itu bukan hasil eksekusi Batch 2. Dokumen ini dan VERIFICATION menjadi otoritas status implementasi aktual; tidak mengubah sejarah atau menganggap review tim sudah diterima.

## Yang diimplementasikan

- `SourceTraceRevision`: satu shared snapshot point-anchored, trace opsional, urutan/parent per point, schema version, checksum konten, lifecycle draft/pending_review/published/rejected, reviewer/time/published time. Migrasi `0002_sourcetracerevision` additive; tidak mengubah data legacy atau mempublikasikannya otomatis.
- Public projection memuat identitas/nilai/unit/period/frequency, definisi/metodologi yang disediakan, metadata sumber/rilis/akuisisi dan keterbatasan. Decimal `(20,4)` dikirim sebagai string; null bukan zero; string kode dipertahankan persis.
- Frozen content tidak berubah melalui `save`, normal QuerySet update/delete/bulk atau editor Admin. Review/publish memvalidasi ulang schema dan checksum. **Ini perlindungan aplikasi/ORM, bukan privilege/trigger database yang mencegah direct SQL atau private ORM internals.** Checksum mendeteksi perubahan konten tanpa perubahan hash; bukan kriptografi autentikasi terhadap operator SQL yang dapat mengubah keduanya.
- Current memilih published revision terakhir per point, lalu periode terbesar dalam satu frekuensi. Draft baru atau working/master edit tidak mengganti published A. Nilai null periode baru tetap null, bukan fallback diam-diam ke periode lama nonnull.
- Histori satu revision per point, ascending, fixed 20/page. Duplikasi periode atau unit/type/identity seri bertentangan gagal 503; tidak `.first()` menurut periode. Row null dipertahankan; `gap_policy=break_on_null_or_missing_period`. Tidak mengisi periode hilang sebagai nol.
- Public GET mengabaikan kebutuhan token/session hanya di view fitur ini; accounts tetap private. RAW, private notes, raw JSON formula, reviewer/email dan exception tidak diproyeksikan. Metadata URL tidak di-fetch. No-store, throttle existing dan query strict tetap berlaku.

## Endpoint aktual

Semua memakai prefix `/api/v1/indicators/` yang sudah terdaftar:

| GET path | Query |
|---|---|
| `{code}/detail/` | `period_type` optional bila satu frekuensi publik |
| `{code}/history/` | `period_type`, `page` positif ASCII canonical tanpa leading zero, maksimum sembilan digit |
| `{code}/data-points/{data_point_id}/revisions/{revision_id}/` | Tidak menerima query |

GET/HEAD/OPTIONS; mutasi 405. Code/UUID/parent/nonpublic unknown mengembalikan generic 404 sama. Invalid/unknown/duplicate query 400; ambigu frequency 400 series_selection_required; throttle 429; storage/invariant failure 503 tersanitasi. Error tidak berubah menjadi empty/demo. Empty history page1 hanya untuk indikator yang punya publikasi sah tetapi frekuensi valid pilihan belum punya baris; current pilihan tanpa observasi 404.

Histori merupakan konteks published saat request, bukan as-of historis, frozen keseluruhan seri atau pagination snapshot lintas request. Di PostgreSQL, selection/count/page menggunakan read-only REPEATABLE READ transaction; bila dipanggil dari transaksi luar yang bukan repeatable read/serializable, gagal aman 503 daripada menjanjikan konsistensi palsu. Default deployment tidak boleh membungkus view ini dengan transaksi luar READ COMMITTED/ATOMIC_REQUESTS tanpa menyelaraskan kebijakan tersebut. SQLite dipakai sebagai test cepat, bukan bukti PostgreSQL isolation/locking.

## Capture dan publikasi terkontrol

Model source lama tetap working record tim. Jalur capture eksplisit berada pada `apps.indicators.revisions.capture_revision(point_id, data_origin='unknown')`: mengunci master, point dan trace opsional secara konsisten. Tidak ada signal, network fetch, adopsi approved otomatis, endpoint tulis publik, atau pengubahan fixture frontend menjadi data resmi.

Lifecycle services: `submit_revision`, `publish_revision`, `withdraw_revision` menerima revision ID dan actor. Actor dibaca ulang dari AdminUser; harus aktif, staff, dan reviewer/superadmin atau superuser. Ordinary role admin tidak otomatis boleh mempublikasikan. Publish hanya dari pending_review, mengikat reviewer/time ke konten tepat itu. Origin demo ditolak jalur publikasi produksi; origin unknown tidak disamakan verified/official_source.

Readonly Django Admin untuk revision menyediakan submit/publish/withdraw actions kepada reviewer yang juga memiliki izin view model Django. Operasi multi-selection atomik: satu status/konten invalid membuat seluruh pilihan rollback dan pesan error terlihat. Konten/FK/status tidak diedit melalui form, tidak add/delete di editor ini. Pembuatan kandidat memakai capture service dari jalur operator/pipeline yang berwenang; tidak menambah public write endpoint atau membangun UC-08 penuh.

Service actor policy di atas adalah implementasi engineering minimum untuk direview tim, **bukan klaim persetujuan akhir PIC/policy tim**. Actor yang sama dapat submit dan publish; aturan dual-review tidak dimodelkan. Withdraw mempertahankan fakta review awal dan mengubah lifecycle menjadi rejected; paket ini belum menyediakan jurnal append-only seluruh keputusan review/penarikan. Admin Django mencatat tindakan UI sesuai mekanismenya; pemanggilan service langsung bukan audit journal lengkap.

## Keselarasan shared revision F7

J1..J6 dari FOUNDATION diadopsi di shared model yang sama: mandatory point, optional trace, sequence per point, frozen metadata F6, change nullable dan revision-bound publication. Tidak membuat tabel revision F6 paralel. Source Trace yang datang setelah A membentuk B, tidak mengubah A.

**Perubahan paralel ditemukan setelah pengujian fitur 6:** backend F7 sudah dipublikasikan sebagai PR #20 (`feat/7-source-trace-api`, commit `23aa325`) ke `be`. Working tree F7 dan dokumen historisnya berubah dari baseline pemeriksaan Batch 1; ini bukan file yang ditulis pekerjaan F6. F7 juga menambahkan `SourceTraceRevision`. Branch F6 ini tetap berbasis `be` 03052e3 dan belum menggabungkan PR #20.

**Integration blocker:** model, migrasi dan lifecycle shared revision kedua branch harus direkonsiliasi sebelum kedua PR digabung; jangan menerapkan dua implementasi atau menyebut hasil gabungannya sudah diuji. Draft PR F6 menyatakan dependensi PR #20 secara eksplisit. Tidak mengubah, menimpa, merge atau mempublikasikan ulang pekerjaan F7 dari sesi ini. Pilihan fondasi bersama membutuhkan review lintas PR, bukan pembuatan model/tabel kedua.

`links.source_trace` saat ini **null**, disertai `source_trace_endpoint_unavailable`: backend fitur 7 belum dibuat di branch ini. Fixture route Laravel bukan alasan mengiklankan URL API yang belum ada. Detail/pinned identity sudah tersedia agar integrasi nanti mempertahankan revision yang sama.

## Batas yang sengaja dipertahankan

- `snapshot.change=null`, warning change_evidence_unavailable. Trend legacy tidak memiliki binding comparator/unit-kind/formula yang cukup. Full F6-03/data resmi masih dependency engine/reviewer; tidak mengklaim null aman sebagai perhitungan selesai.
- Asal unknown dan verification_status unassessed tetap eksplisit. Institution/publication URL, metadata lengkap atau status published bukan verifikasi faktual/matematis.
- Model lama belum memisahkan konsep harga/base year atau frekuensi semester. API tidak menebak atau mengagregasi antarseri; pakai kode indikator yang benar dan metadata yang direview.
- Bukan jaminan semua jalur SQL/pipeline mematuhi protokol lock. Jalur penulisan lain harus berkoordinasi untuk menghindari edit/reparent yang tidak sesuai kontrak. Revision FK PROTECT berdampak delete parent; kebijakan retention harus direview tim.
- Integrasi frontend belum dilakukan: pembaca Laravel masih fixture dan helper grafik belum menerima decimal string. Adapter harus mempertahankan string untuk display, konversi hanya untuk geometri, memutus missing calendar periods, dan tidak fallback demo tersembunyi saat API error.
- Tidak mengubah Docker, .env, settings produksi, dashboard, backend accounts atau data resmi. Tidak menjalankan migrasi produksi dan tidak merge ke be.

## Menjalankan tes terisolasi

Runtime dependency mengikuti `backend/requirements.txt`. Instalasi lokal yang dipakai pada implementasi ini: uv venv di `backend/.venv`, Python 3.13.7, Django 6.1.2, DRF 3.18.3, psycopg2-binary 2.9.13. Tidak mengubah runtime global atau memasang paket di profil Hermes.

Dari root repository, gunakan interpreter virtualenv yang tersedia pada platform Anda:

```sh
backend/.venv/Scripts/python.exe -B backend/manage.py test apps.indicators.tests --settings=backend.test_settings --noinput --verbosity=1
backend/.venv/Scripts/python.exe -B backend/manage.py makemigrations --check --dry-run --settings=backend.test_settings
backend/.venv/Scripts/python.exe -B backend/manage.py check --settings=backend.test_settings
```

`backend.test_settings` standalone: tidak mengimpor settings produksi atau dotenv. Default SQLite memory. Mode PostgreSQL hanya dengan `DEKSI_TEST_DB=postgres`: loopback 127.0.0.1, port `DEKSI_TEST_PG_PORT` (default 55436), maintenance database `deksi_f6_test`, test database `test_deksi_f6_test`, user `deksi_f6_test`, tanpa password. Konfigurasi ini **khusus server test lokal terisolasi**, bukan deployment/trust untuk jaringan atau DB pengguna. Server PostgreSQL test harus disiapkan secara terpisah dan dihentikan setelah run; jangan mengarahkan env test ke produksi.

Bukti aktual, jumlah test/skip, migration dan real HTTP dicatat pada VERIFICATION setelah run final. Jangan menjalankan Compose hanya untuk membuat detector canonical menandai workspace verified. Tidak ada klaim CI/produksi/validitas angka resmi dari test sintetis.
