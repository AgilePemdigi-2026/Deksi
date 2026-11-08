# F6 — persiapan publikasi branch terpisah

Pengguna mengizinkan urutan pemisahan koreksi F6, pembaruan dependency F7, commit lokal masing-masing unit, kemudian push hanya dua feature branch. Dokumen ini merekam tahap sebelum publikasi, bukan bukti push sudah terjadi. Tidak ada izin PR, merge shared branch, force-push, atau perubahan identitas.

## Scope F6

Branch `feat/6-detail-indikator-fe`, foundation `505e97116f132c8630ec08d07525b8aec9e00536`, checkpoint awal `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`.

Koreksi yang dipindahkan dari worktree F7 yang telah direview:
- Deadline per resource 10 detik termasuk body JSON; cancellation dan partial data tetap benar.
- Frequency/dataType dipertahankan; grafik campuran ditolak dan metadata asli ada di tabel.
- Skala Y numerik dengan presisi adaptif agar angka berdekatan tidak memakai label sama.
- Regresi timeout/body parsing/abort, mixed series, zero/null/negative/constant/large/small-difference values.

Ini pemindahan patch yang sudah diuji, bukan implementasi baru atau bukti RED baru. Identitas normalized-text lima file helper/API/type/test dan komponen History dibandingkan dengan worktree F7; sama. F6 sengaja tetap standalone: source-trace route placeholder dan tombol F7 disabled sampai lapisan F7 ditambahkan. Tidak memindahkan SourceTracePage, hook ekstraksi F7, atau aktivasi link F7 ke F6.

## Verifikasi aktual setelah pemisahan

Dijalankan dari frontend worktree F6:
- `npm run test:indicators`: 33/33 PASS, 0 skip.
- `npm test`: 7/7 editorial PASS, 0 skip.
- `npm run test:indicators:browser` dengan scratch eksplisit: 8 kelompok PASS, 0 runtime errors. Browser disposable dengan API sintetis, bukan Django.
- `npm run build`: exit 0, warning chunk >500 kB tetap ada.
- `npm run lint`: exit 0, tiga warning existing di luar patch.
- `git diff --check`: exit 0.

Path, hash, log dan waktu eksekusi ada pada [receipt F6](F6_PUBLICATION.json). Receipt F6 awal tetap bukti historis, bukan hash source terkini. Git core.autocrlf existing true; kesetaraan checkout Windows dan blob Git diperiksa sebagai konversi CRLF/LF saja, bukan mengubah konfigurasi global atau menormalisasi perbedaan kode.

Tidak ada install/dependency baru, backend/Login, database, global theme atau shared dashboard transport yang diubah. API nyata, human visual acceptance, dan remote CI tidak disimpulkan dari tes sintetis. Status remote/commit final akan diverifikasi terpisah setelah tindakan publikasi.
