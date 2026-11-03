# Status aktif F6 backend — Batch 1 dan penyesuaian Batch 2

Tanggal: 2026-11-03. Status ini melengkapi, bukan mengganti, receipt historis.

## Implementasi saat ini

- Fondasi API baca dan empat koreksi audit tetap dipertahankan. Branch F6 `feat/6-detail-indikator-be`, HEAD dasar `032b9aec4de0a5d9d96fe94b638329ab5207b586`; source lifecycle diuji terhadap baseline tersebut; identitas checkpoint baru dicatat terpisah setelah otorisasi.
- BI, BKPM, fiskal dan BPS menulis `ObservationCandidate`, bukan menimpa observasi publik. Impor identik tidak membuat kandidat berulang; kandidat baru tidak mewarisi persetujuan reviewer lama.
- Source/Indicator existing yang berbeda dari metadata importer ditolak eksplisit, bukan diam-diam diubah. Publikasi membutuhkan Admin aktif berizin, validasi, pemeriksaan snapshot basis yang belum berubah, dan transaksi atomik atas data, status kandidat dan log sukses.
- Pending, penolakan, kandidat kedaluwarsa dan kegagalan publikasi tidak mengganti data publik lama. `publish_observations` kini wajib memilih ID kandidat eksplisit dan menggunakan Admin existing; tidak membuat reviewer otomatis atau memublikasikan seluruh tabel.
- Migration `0005_observation_candidate` diuji pada DB sintetis dan tidak memindahkan/mengubah observasi aktif. Tidak ada migrasi database pengguna. Petunjuk operator: [LIFECYCLE.md](LIFECYCLE.md).

## Bukti aktual

- F6 canonical baru: 52 test PASS; Django check, migration drift dan lint 19 file terpilih PASS. Tiga writer yang gagal pada canonical sebelumnya telah direproduksi dengan fixture terisolasi, kemudian lulus setelah repair.
- F7 telah menerima 19 file shared yang cocok byte/text setelah normalisasi line ending. Canonical F7: 73 test ditemukan/dieksekusi oleh runner, 1 SKIP symlink Windows; check/drift/lint dan Node syntax PASS.
- Integrasi F7 actual FE → Django: 13 pemeriksaan PASS tanpa intersepsi API. Alur baru menahan nilai lama saat staging, reject dan kegagalan transaksi; review CLI eksplisit menerbitkan kandidat, byte RAW tetap cocok dan URL konteks lama ditolak.
- Kedua canonical dicatat `passed`, exit 0, pada ledger session/root tepat dan dibaca balik read-only. Build/unit/browser FE terpisah tidak diulang pada batch ini karena source FE tidak diubah; bukti lama tidak disebut fresh.
- Review independen menemukan bypass aksi publikasi observasi legacy. Aksi itu dihapus; crafted Admin POST direproduksi RED lalu tidak dapat memublikasikan tanpa kandidat. Audit lanjutan juga memperbaiki no-op fakta legacy belum direview dan overwrite RAW pada F6; hardening writer F7 yang sudah ada dipakai ulang di fondasi shared, bukan membuat storage baru. Seluruh regresi baru lulus pada canonical akhir. Ini bukan persetujuan publikasi.

## Batas dan gate tersisa

- Kandidat adalah staging/review, bukan jurnal revisi immutable. Source/Indicator/observasi legacy tetap mutable bagi jalur berwenang lain; formula versi dan official verification belum tersedia.
- SQLite menyimpan decimal exact sebagai TEXT; SQL numeric ordering/aggregation generik tidak didukung. Tes concurrency SQLite membatasi maksimal satu publikasi dari basis sama, tetapi dapat menolak kedua penulis; PostgreSQL dan jaminan progress/retry belum diuji.
- Provider resmi, migrasi DB pengguna, deployment, standalone startup/readiness dan persetujuan estetika belum dilakukan. Integrasi adalah data sintetis, bukan verifikasi ekonomi/sumber resmi.
- Warning dashboard Recharts pada fixture angka ekstrem sudah tercatat pada Batch 2 sebelumnya; bukan chart histori F6 dan bukan regresi lifecycle. Dashboard milik rekan tidak diubah. Tidak ada klaim konsol seluruh aplikasi bersih.
- Pengguna telah mengizinkan checkpoint dan dependency lokal untuk kandidat yang diuji. SHA final serta ancestry harus dicatat pada handoff setelah eksekusi; izin ini tidak mencakup push, PR atau merge shared. Jangan mengubah/menghapus checkpoint lama atau menganggap penyalinan working tree sudah merupakan merge Git.
- Jangan stage `.hermes/`, `.artifacts/`, interpreter lokal, secret, environment atau RAW. Belum ada push, PR atau merge ke branch shared. FE companion masih memerlukan keputusan publikasi terpisah.
