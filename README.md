# DEKSI — BDD Sprint 1, area pengujian terpisah

## Pembaruan branch BDD-DEKSI

Paket ini memperbarui versi pilot di branch `BDD-DEKSI` dengan kandidat as-built v2.1 yang telah diuji: **73 skenario dan 219 langkah PASS**, termasuk dua perbaikan produk di salinan `frontend-checkpoint/`. Buka [RESULTS.md](RESULTS.md) atau [laporan per skenario](qa/artifacts/20261107-183251-product-fixes-full/summary.md). Catatan "belum commit/push" pada laporan historis merujuk keadaan saat run lokal, bukan alasan menganggap perbaikannya tidak ada dalam paket ini.

Hasil tersebut berasal dari run lokal `20261107-183251-product-fixes-full`, **bukan GitHub Actions** atau run baru di worktree publikasi. Source pengujian dan 18 source pin aplikasi dicocokkan dengan receipt sebelum publikasi; kedua perbaikan benar-benar disertakan, bukan hanya file laporan. Baseline v1 dan bukti kegagalan lama tetap disimpan.

Setup ini masih khusus lingkungan Windows/dependency existing yang disebut di bawah. `.gitattributes` menjaga byte QA dan dua file perbaikan agar hash receipt tidak berubah akibat konversi newline; ini bukan klaim instalasi atau eksekusi otomatis di semua mesin. Paket publikasi tidak menyertakan node_modules, virtualenv, cookie/profil browser, screenshot/log mentah atau database pengujian. Salinan checkpoint dan backup database yang telah ada pada komit pendahulu tidak ditambah atau diubah oleh pembaruan ini.

Scope: delapan fitur Sprint 1, **72 skenario as-built v2** yang mengikuti aplikasi aktual + regresi `REG-EMPTY-YEAR-DETAIL`. Baseline acceptance v1 tetap tersedia terpisah. Semua tindakan hanya pada area BDD ini dan scratch disposable; lane integrasi FE/BE lain tidak ditulis.

## Checkpoint

- Backend: `integration/sprint-1-unified-be`, `d9c673fac84992b91c160bfaa4f0de33a8ce548b`.
- Frontend: `integration/sprint1-docker-fe`, `e35d97899d345f18a3341bc19beba431f94179d9`.
- Backend tetap detached di `backend-checkpoint/`. Frontend di `frontend-checkpoint/` kini memakai branch lokal `fix/sprint1-bdd-layout-empty-year`, berbasis SHA FE di atas ditambah dua file perbaikan belum di-commit. SHA base bukan SHA yang sudah memuat perbaikan. Manifest v2.1 mengunci hash overlay; manifest v2 asli disimpan di `qa/as-built-manifest.v2-original.json`. Pemeriksaan ref lokal bukan klaim refresh seluruh GitHub.
- Referensi baseline: `qa/spec-reference/` dan `qa/features/*.feature`; dokumen Batch 1 di folder Semester tetap tidak diedit. Suite aktif: `qa/features/as-built/`, dengan pemetaan perubahan di `AS_BUILT_ALIGNMENT.md` dan `qa/as-built-manifest.json`.

## Menjalankan ulang

Gunakan dependency existing yang sudah diperiksa, **bukan install otomatis**. Command berikut untuk Git Bash pada mesin ini:

```bash
cd E:/Deksi-BDD-Sprint1/qa
E:/Deksi-Team/.hermes/worktrees/feature-1-login-be/backend/.venv/Scripts/python.exe -I -B E:/Deksi-BDD-Sprint1/qa/run_bdd.py --suite as-built --tags '@sprint1 or @regression' --label rerun-sprint1
```

Tanpa `--tags`, runner menyeleksi `@sprint1`: 72 skenario suite yang dipilih, tidak termasuk regresi tambahan. Suite default ialah `as-built`; gunakan `--suite baseline` untuk acceptance v1. Filter path memisahkan kedua katalog agar tidak terjadi ID ganda. Label yang sama boleh dipakai pada waktu berbeda; direktori artifact selalu bertimestamp. Exit 1 berarti kegagalan tes tetap dipertahankan, bukan bahwa laporan harus dibuang.

Run lengkap dapat memerlukan lebih dari enam menit tergantung beban mesin. Jika dijalankan melalui agent dengan batas command pendek, gunakan proses terpantau/notification; jangan memotong runner lalu menganggap JSON parsial sebagai hasil suite lengkap. CLI lokal biasa tidak bergantung pada batas tool chat. Command CDP memiliki deadline keseluruhan 30 detik agar event browser yang terus datang tidak memperpanjang satu command tanpa batas; ini tidak mengubah timeout HTTP produk.

Setelah run, buat ringkasan berdasarkan lokasi `ARTIFACTS` yang dicetak:

```bash
E:/Deksi-Team/.hermes/worktrees/feature-1-login-be/backend/.venv/Scripts/python.exe -I -B E:/Deksi-BDD-Sprint1/qa/report_results.py 'E:/Deksi-BDD-Sprint1/qa/artifacts/<timestamp>-rerun-sprint1'
```

Reporter membaca hasil aktual dan memeriksa 72 ID sesuai manifest versi suite, hash source QA/feature dan cleanup; tidak menjalankan ulang aplikasi atau mengubah FAIL menjadi PASS. Reporter menolak DTO sukses mock dalam suite as-built dan menolak menimpa ringkasan sebelumnya. Hasil terbaru dicatat di `RESULTS.md`; hasil baseline sebelumnya dipertahankan di `RESULTS_BASELINE_V1.md` serta artifact historis.

## Lapisan bukti dan batas

- Behave-Django menjalankan Gherkin Given–When–Then. API menggunakan view/model/database asli pada SQLite disposable.
- Browser nyata menggunakan Chrome/CDP dengan `websocket-client` existing, **NON-Selenium**. Tidak ada instalasi atau pengunduhan driver.
- React/Vite → proxy same-origin → Django LiveServer. CSRF middleware dan cookie HTTP-only tetap aktif. Test server memakai backlog 128 agar bootstrap paralel React dev mode tidak tersendat; timeout HTTP aplikasi tidak diubah.
- Tiap skenario browser memiliki port dan profil sendiri. RAW dan database hanya dalam scratch milik run, email hanya locmem.
- Skenario lambat/gagal jaringan memakai interception yang dicatat; `BDD-F02-08` memakai respons error 503 sintetis, bukan bukti layanan nyata menghasilkan 503.
- `BDD-F08-07` menginjeksi `DatabaseError` pada penyimpanan fixture, dengan HTTP dan UI nyata. Patch dibersihkan setelah skenario.
- **Suite as-built tidak memakai DTO sukses mock.** `ASBUILT-F07-03` memeriksa respons backend asli `unclassified`, formula/input belum tersedia, revisi null dan snapshot tidak immutable. `BDD-F07-03` yang mengubah valueKind menjadi official lewat DTO mock hanya berada pada suite baseline; bukan acceptance E2E dukungan official. Tidak ada data resmi atau provider resmi yang dipakai.
- `ASBUILT-F06-02` dan `ASBUILT-F07-08` menguji safe empty state serta rincian HTTP/transport yang dibuka melalui kontrol aktual. Banner not-found khusus dan pemisahan state utama tetap gap acceptance v1, bukan dinyatakan sudah diperbaiki. Tiga perubahan memakai ID baru; baseline lama tidak ditulis ulang menjadi PASS.
- Q02/Q03/Q04 dijalankan sebagai kontrak kandidat; hasil teknis bukan persetujuan manusia atas kontrak. Review Q01–Q09 dan rekonsiliasi SRS lengkap masih terbuka.
- Tag `@not_run` dan komentar SPECIFICATION ONLY hanya pada salinan baseline Batch 1. Suite as-built memakai tag `@as_built`; status run aktual tetap berasal dari `behave.json`, bukan tag tersebut.
- Skipped scenario karena seleksi tag berbeda dari skipped step setelah sebuah langkah gagal. Gunakan run semua tag untuk laporan cakupan; jangan menyebut subset PASS sebagai seluruh suite PASS.
- Setelah pengguna meminta memperbaiki FAIL, dua perbaikan produk lokal diizinkan: batas lebar artboard dan guard Detail untuk tahun tanpa data (termasuk tombol hero yang sebelumnya bisa melewati kartu). Tidak ada skenario dihapus. Database demo/container aktif, provider AI/resmi, email nyata, install, commit/push/PR dan lane sesi lain tetap tidak disentuh.
- Audit hook Python bukan sandbox OS. Pemeriksaan fungsi/keyboard/overflow tidak memberikan sertifikasi aksesibilitas, persetujuan visual, kesiapan SMTP atau produksi.

## Berkas utama

- `PLAN.md`: izin, batas dan urutan pilot → ekspansi.
- `qa/run_bdd.py`, `bdd_settings.py`: runner dan lingkungan disposable.
- `qa/browser.py`, `journal.py`, `features/environment.py`: Chrome, journal HTTP, bukti dan cleanup.
- `qa/features/steps/`: bindings API/browser/ekspansi.
- `qa/features/as-built/`, `qa/as-built-manifest.json`, `AS_BUILT_ALIGNMENT.md`: katalog aktual, fingerprint source dan delta terhadap baseline.
- `qa/report_results.py`: ringkasan mekanis hasil aktual, ID, hash dan cleanup.
- `qa/artifacts/<run>/`: `behave.json`, `run.json`, `cleanup.json`, bukti DOM/HTTP/screenshot per skenario.
- `FE_HANDOFF.md`: temuan dan reproduksi untuk pemilik frontend; dokumen lokal, bukan bukti pesan telah dikirim.
