# BDD Sprint 1 — hasil eksekusi 7 November 2026

**72 skenario baseline: 68 PASS, 4 FAIL, 0 SKIPPED, 0 undefined.**

Ditambah regresi tahun kosong: **73 skenario = 68 PASS, 5 FAIL, 0 SKIPPED**. Seluruh **219 langkah** mendapat hasil: **214 PASS, 5 FAIL, 0 SKIPPED**. Exit runner **1**, karena kegagalan produk/kontrak dipertahankan, bukan disembunyikan.

Run final: `qa/artifacts/20261107-003936-sprint1-verified/`. Command dan hash source tersimpan di `run.json`; hasil per skenario di `behave.json`; ringkasan lengkap di `summary.md` dan `summary.json`.

| Cakupan baseline | PASS | FAIL | Catatan |
|---|---:|---:|---|
| API | 27 | 0 | View/model/database disposable asli, CSRF aktif |
| Browser tanpa DTO success mock | 41 | 3 | Termasuk fault injection jaringan/storage yang diberi label |
| Browser kontrak DTO success mock | 0 | 1 | BDD-F07-03, bukan acceptance E2E backend |
| Total baseline | 68 | 4 | 72 skenario |
| Regresi tambahan | 0 | 1 | Filter tahun kosong → Detail terbaru |

## Kegagalan yang tersisa

1. `BDD-F06-02`: Detail kode asing belum menampilkan not-found yang jelas; **tidak ditemukan substitusi angka PDB**.
2. `BDD-F07-03`: klasifikasi `official` belum dirender. **Skenario DTO mock**, backend saat ini belum menghasilkan klasifikasi itu.
3. `BDD-F07-08`: Source Trace belum membedakan not-found dan gangguan transport dengan jelas.
4. `BDD-X-06`: dashboard desktop memiliki overflow horizontal 15 px (`clientWidth=1265`, `scrollWidth=1280` pada viewport emulasi 1280).
5. `REG-EMPTY-YEAR-DETAIL`: pilih tahun 2024 tanpa data, Detail PDB diam-diam menampilkan Q1 2025 terbaru.

Reproduksi dan batas bukti: [FE_HANDOFF.md](FE_HANDOFF.md). Handoff masih lokal, **belum dikirim ke pemilik frontend**.

## Yang berubah pada harness

- Bindings diekspansi ke seluruh 72 skenario dan regresi tambahan, tanpa mengubah teks baseline `.feature`.
- Default runner kini menyeleksi seluruh `@sprint1`; tidak hanya dua pilot.
- Perbaikan wait dokumen baru, asumsi query Source Trace yang keliru, pembandingan instant timestamp lintas zona, backlog test server dan race baca `DevToolsActivePort` Windows.
- Oracle fokus menerima outline, focus stroke SVG atau perubahan box-shadow/border yang benar-benar terlihat pada computed style; tidak memaksa satu implementasi CSS.
- Kegagalan startup dan run lama tetap disimpan di artifact historis. Dua unit test harness untuk locked/partial DevToolsActivePort dan timeout permanen **PASS**, terpisah dari 72 BDD.
- Reporter memeriksa ID, hasil, source hashes dan cleanup, tanpa memberi persetujuan semantik/visual.

## Checkpoint dan keselamatan terverifikasi

- BE: `d9c673fac84992b91c160bfaa4f0de33a8ce548b`.
- FE: `e35d97899d345f18a3341bc19beba431f94179d9`.
- Ref integration lokal diperiksa ulang; tidak ditemukan FE integration lokal lebih baru. Bukan klaim refresh seluruh GitHub.
- Kedua worktree produk tetap **clean**. Tidak ada source produk, database demo/container aktif, dependency atau konfigurasi provider diubah; tidak ada commit/push/PR.
- Kesembilan file baseline `.feature` **byte-identical** terhadap sumber Batch 1.
- DB disposable dihapus; seluruh cleanup browser/Vite tercatat berhasil. **165 port milik run diperiksa dan tidak lagi listening**. Bukti: `boundary-check.json`.
- Email locmem, CSRF middleware asli dan cookie HTTP-only tetap aktif. Tidak ada provider resmi/AI atau email nyata; Python audit hook bukan sandbox OS.

## Batas acceptance

Browser nyata **Chrome/CDP, NON-Selenium**; driver Selenium tidak dipasang. `BDD-F02-08` menginjeksi error 503 dan `BDD-F08-07` menginjeksi kegagalan storage; keduanya dibedakan dari respons sukses nyata. `BDD-F07-03` satu-satunya success DTO mock.

Q02/Q03/Q04 kini dieksekusi terhadap kontrak kandidat yang tersedia, **bukan dianggap disetujui**. Q01–Q09, rekonsiliasi SRS lengkap, review manusia/visual, SMTP dan produksi masih di luar bukti PASS ini. Tidak ada bug produk diperbaiki hanya untuk menghijaukan tes.
