# Fitur 6 backend — bukti verifikasi Batch 2

Status: **pengujian backend terisolasi lulus; Draft PR untuk review, bukan penerimaan produksi.** Base `be` `03052e3911966895456fd338300621c159ae30e4`; branch `feat/6-indicator-detail-backend`. Tanggal eksekusi 28 Oktober 2026 (UTC+07). Scope/kebijakan di [IMPLEMENTATION.md](IMPLEMENTATION.md). Kontrak Batch 1 tetap baseline historis, bukan klaim API/runtime saat itu.

## Runtime dan isolasi

- Python virtualenv 3.13.7, Django 6.1.2, DRF 3.18.3, psycopg2-binary 2.9.13. Dependency mengikuti requirements backend existing; tidak mengubah environment global.
- `backend.test_settings` berdiri sendiri, tidak mengimpor dotenv/settings produksi. SQLite in-memory; PostgreSQL test portable EDB **18.6**, loopback `127.0.0.1:55436`, database test `test_deksi_f6_test` dan maintenance `deksi_f6_test`, user test lokal tanpa password pada cluster disposable yang hanya mendengarkan loopback.
- Binaries diperoleh dari archive EDB yang dirujuk halaman resmi PostgreSQL Windows, melalui HTTPS. ZIP: `postgresql-18.6-5-windows-x64-binaries.zip`; SHA-256 lokal `e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2`. Hash adalah identitas unduhan lokal, **bukan klaim validasi signature/checksum vendor**.
- Database test dibuat/dihapus oleh Django test runner; server PG dihentikan di finally dan tidak ada postmaster.pid setelah run berhasil. Tidak menjalankan database produksi, Docker, AI, source fetching atau migrasi pengguna.

## Hasil aktual final

| Pemeriksaan | Hasil |
|---|---|
| Django feature-6 suite, PostgreSQL 18.6 | **43 tests, OK, exit 0; tidak ada skip**; run final 17.333 s menurut runner |
| Django feature-6 suite, SQLite memory | **43 tests, OK, skipped=1, exit 0**; skip adalah PostgreSQL row-lock concurrency yang tidak didukung SQLite |
| Migration consistency `makemigrations --check --dry-run` | No changes detected, exit 0 |
| Django system check | No issues, exit 0 |
| Real HTTP melalui LiveServerTestCase + urllib | Anonymous/malformed-token detail, history, pinned revision dan private accounts benar; termasuk dalam suite, bukan pengujian frontend/browser |
| PostgreSQL concurrency | Dua capture bersamaan pada point yang sama menghasilkan sequence 2/3 unik; benar-benar dieksekusi, bukan SQLite/mock |
| Migration roundtrip test | Reverse 0002→0001 dan forward lagi pada DB test; working observations bertahan, tidak auto-publish. **Rollback menghapus tabel revision/snapshot** sehingga bukan rollback data-preserving untuk produksi |
| Independent review | Review read-only core capture→publication→public read melaporkan tidak ada must-fix dalam scope yang diperiksa; bukan security audit penuh/runtime verification |

Perintah nyata dari root dengan interpreter virtualenv:

```sh
# SQLite, default standalone test settings
backend/.venv/Scripts/python.exe -B backend/manage.py test apps.indicators.tests --settings=backend.test_settings --noinput --verbosity=1
backend/.venv/Scripts/python.exe -B backend/manage.py makemigrations --check --dry-run --settings=backend.test_settings
backend/.venv/Scripts/python.exe -B backend/manage.py check --settings=backend.test_settings

# PostgreSQL: server test milik run ini sudah disiapkan/dihentikan terpisah
DEKSI_TEST_DB=postgres DEKSI_TEST_PG_PORT=55436 backend/.venv/Scripts/python.exe -B backend/manage.py test apps.indicators.tests --settings=backend.test_settings --noinput --verbosity=1
```

Jangan menyalin konfigurasi trust/role test ini untuk deployment. Jangan menjalankan mode PostgreSQL sebelum memiliki cluster test terisolasi yang disetujui. Uji real HTTP dilakukan terhadap aplikasi+DB test milik run, bukan server demo frontend pengguna.

## Cakupan dan bukti RED

Model revision belum terdaftar → assertion gagal; model+migrasi membuatnya lulus. Capture service belum ada → assertion gagal; capture draft/no-fake-trace lulus setelah implementasi. Endpoint publik awal 404 vs expected 200 → lulus setelah route/view/projection. Bulk Admin pilihan status campuran awal melempar ValidationError → diperbaiki menjadi atomic rollback dan pesan error; regresi lulus.

Suite mencakup decimal zero/null/presisi, RAW/layer invalid, periode malformed, identitas/parent/review, frozen content dan checksum, role inactive/ordinary admin, duplicate sequence DB constraint, published-review DB constraint, current vs pinned, chronological history/pagination/ambiguity, mixed frequency/unit, unsafe URL dan private-field projection, sanitized storage failure, throttle/405/HEAD/OPTIONS/no-write serta account auth boundary. Tidak menganggap fixture sebagai data resmi.

## Kegagalan harness dan batas evidence

Pencarian literal ZIP pada HTML EDB awal hanya menemukan archive lama; tidak memakai PG9. Download modern sempat timeout dan dilanjutkan dengan validated HTTP Range. Launcher PG awal tertahan oleh inherited capture pipes pada Windows; owned server dihentikan, lalu launcher diarahkan ke log file dan run berhasil. Kegagalan setup itu **bukan test aplikasi PASS**; hasil final di atas berasal dari run nyata setelah repair.

Receipt/log/hash lengkap disimpan lokal pada `.hermes/receipts/feature6-postgresql.json`, `feature6-postgresql-suite.log`, `feature6-sqlite-final.json` (tidak dimasukkan PR). File `verification.json` pendamping menyimpan ringkasan eksekusi dan fingerprint source yang dapat direview. Pengingat canonical detector yang tidak mengenali runner tidak diatasi dengan mengubah ledger/manifest atau menjalankan Compose yang di luar scope. Bukti eksekusi dan pengenalan canonical adalah dua status berbeda.

## Batas yang belum diterima

- Tidak ada integrasi Laravel/visual acceptance, deploy, Docker acceptance, official-data validation atau backend Source Trace endpoint.
- `change=null` sampai comparator/formula evidence disepakati; belum menyelesaikan full F6-03. Source link null sampai endpoint F7 benar-benar ada; bukan dead link.
- Immutable content ditegakkan/dideteksi pada jalur ORM/Admin/service yang diuji, bukan pencegahan operator direct SQL yang dapat mengubah row dan hash.
- Review/publish policy minimum, retention/PROTECT impact, shared contract F7 J1..J6, audit lifecycle lengkap dan pemetaan seri/kode masih memerlukan review tim. Tes tidak memberi approval manusia.
- PR F7 #20 muncul paralel pada commit 23aa325 dan juga menambahkan shared revision model. Empat dokumen F7 berbeda dari baseline Batch 1; 12 file frontend yang diproteksi tetap cocok. Hasil gabungan F6 + PR #20 **belum diuji** dan fondasi model/migrasi harus diselaraskan sebelum merge kedua PR. Jangan menafsirkan 43 tes branch F6 sebagai acceptance gabungan.
- Tidak ada klaim GitHub CI lulus dari run lokal. PR dibuat Draft, tidak auto-close issue atau auto-merge.
