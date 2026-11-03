# Status aktif F6 backend — Batch 2

Tanggal: 2026-11-03. Dokumen ini melengkapi, bukan mengganti, receipt checkpoint historis.

## Scope yang diteruskan

Pengguna memilih Batch 2 (integrasi dan persiapan branch) sebelum Batch 1 (kandidat impor/review). Karena itu evaluasi hanya berlaku untuk API baca dan koreksi yang sudah diimplementasikan. Tidak ada klaim bahwa lifecycle pembaruan otomatis sudah aman.

- Branch `feat/6-detail-indikator-be`; checkpoint dasar `652ec018ddad455358a9d552593c11b52c4be03b`.
- Koreksi Admin memakai tampilan decimal exact tanpa ordering SQL yang menyesatkan; parameter urutan buatan juga dicakup regresi.
- Receipt `AUDIT_FIXES_VERIFICATION.json` mencatat koreksi dan hash sumber setelah empat temuan audit; `VERIFICATION.json` awal tetap historis.
- Hasil canonical terakhir yang sudah dieksekusi: 21 test PASS, Django check/drift/scoped lint PASS. Manifest lokal memakai interpreter proyek, pengaturan terisolasi, tanpa bootstrap atau standalone start/readiness.
- Hasil frontend companion yang masih valid harus dibaca terpisah: F6 40 test dan editorial 7 PASS pada source yang sama; bukti ini bukan eksekusi baru hanya karena dokumen diperbarui.

## Batas yang belum ditutup

- Impor BI/BKPM/fiskal dapat menimpa row published menjadi pending. Writer BPS dapat memperbarui nilai published dengan reviewer lama. Batch 1 untuk staging kandidat/review BELUM DIIMPLEMENTASIKAN; regresi alur kandidat belum dapat dijalankan.
- Master sumber/observasi mutable; formula/jurnal revisi immutable tidak tersedia. PostgreSQL, migrasi DB pengguna, data resmi dan deployment belum diuji.
- SQLite menyimpan nilai exact sebagai TEXT; SQL numeric ordering/aggregation generik bukan kontrak yang didukung. Tidak ada float cast pengganti presisi.
- Perbaikan konsumsi histori presisi/sumber/gap di FE companion masih lokal; publikasi BE tidak otomatis menerbitkannya.

## Persiapan publikasi

Stage hanya allowlist deliverable backend dan dokumentasi terkait setelah izin checkpoint. Jangan stage `.hermes/`, path interpreter mesin, environment, RAW pengguna atau `.artifacts/`. Konfigurasi Hermes lokal adalah alat verifikasi, bukan produk yang otomatis dipublikasikan.

F7 harus mewarisi checkpoint F6 terkoreksi. Perubahan dependency, commit lokal, push, PR dan merge shared memiliki izin terpisah. Jangan menulis ulang atau menghapus checkpoint lama. Kandidat boleh direview sebagai API baca dengan batas di atas, bukan dinyatakan siap produksi/refresh otomatis.
