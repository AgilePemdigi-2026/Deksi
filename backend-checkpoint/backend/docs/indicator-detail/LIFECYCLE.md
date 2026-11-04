# Impor kandidat dan review observasi — F6 shared lifecycle

## Perubahan kontrak penulisan

BI, BKPM, fiskal dan BPS kini membuat `ObservationCandidate` pending. API publik tetap membaca `Observation` published dengan reviewer/waktu review. Data baru tanpa publikasi belum tersedia di API; data valid sebelumnya tetap tersedia ketika calon penggantinya pending, ditolak, stale atau gagal dipublikasikan.

`0005_observation_candidate` menambah staging kosong, tidak mengubah observasi aktif dan tidak memigrasikan data lama secara otomatis. Pengujian memakai DB scratch. Migration database pengguna membutuhkan backup, inspeksi, dan izin terpisah; rollback yang menjatuhkan tabel kandidat dapat menghilangkan draft kandidat.

## Pemeriksaan Admin

1. Gunakan Admin existing yang aktif, staff, dengan izin `indicators.change_observationcandidate` (atau superuser aktif yang juga staff). Kandidat tidak membawa reviewer publik sebelumnya.
2. Periksa `payload`, `base_snapshot` dan RAW/sumber terkait pada detail kandidat. Ini bukan verifikasi resmi angka atau tampilan perbandingan versi immutable.
3. Pilih kandidat yang benar secara eksplisit untuk aksi publikasi atau penolakan. Publikasi memvalidasi domain observasi dan kesesuaian basis observasi/master/RAW sebelum perubahan atomik.
4. Jika basis berubah atau payload tidak cocok fingerprint, hentikan review dan periksa ulang fakta/basis. Jangan memaksa status published melalui edit data. Observasi publik dibuat read-only di Admin dan tidak dapat dihapus lewat Admin ini; ini bukan larangan ORM/DB untuk operator istimewa.

Fakta identik hanya diabaikan bila observasi sudah published dengan reviewer dan waktu review; legacy pending/validated/published tanpa review tetap membuat kandidat. Aksi publish observasi legacy tidak tersedia, termasuk bagi superuser dan crafted POST. Kandidat identik pada basis sama dipakai ulang, tidak dipublikasikan otomatis dan tidak membuka ulang kandidat ditolak. Tidak ada retry/resubmission otomatis atau klaim jaminan progress pada writer concurrent.

## Command review khusus operator

Dari folder `backend/` menggunakan environment proyek yang benar:

```text
python manage.py publish_observations --username <admin-existing> --candidate-id <id-yang-direview>
```

Ulangi `--candidate-id` untuk batch terpilih. Tanpa selection, ID duplikat, actor tidak berizin atau satu kandidat bermasalah, command menolak; kegagalan satu kandidat membatalkan seluruh batch. Tidak membuat akun/reviewer otomatis dan tidak menawarkan broad publish.

CLI adalah fasilitas operator lokal yang sudah memiliki akses environment/database, bukan endpoint autentikasi atau bukti kehadiran manusia. Username yang dicatat bukan tanda tangan/verifikasi resmi. Contoh di atas bukan izin menjalankannya pada DB pengguna.

## Integritas dan logging

- Payload memakai decimal string sesuai domain 24 digit/6 decimal dan tanggal ISO, bukan float untuk menyimpan angka ekonomi.
- Importer tidak menimpa master Source/Indicator existing yang berbeda: perubahan konfigurasi harus diperiksa secara eksplisit. Master mutable ini bukan versioning.
- Staging tidak memajukan log sukses pembaruan publik. Publikasi menyimpan nilai, review baru, status kandidat dan log sukses dalam satu transaksi; kegagalan log ikut rollback.
- Fondasi F6 kini menggunakan ulang writer RAW content-addressed F7 agar impor dengan nama dokumen sama tidak menimpa RAW aktif. F7 tetap menambahkan pemeriksaan download. Checksum adalah integritas byte, bukan bukti akurasi data/sumber resmi. Hardening route download publik F7 tetap delta F7; penataan writer shared tidak otomatis memindahkan seluruh API Source Trace ke F6.
- Snapshot basis mencegah kandidat lama diterapkan pada keadaan berbeda; bukan jurnal public immutable, bukan sandbox terhadap operator DB/filesystem dan bukan penyimpanan formula versi.

## Bukti dan batas

Lihat [CURRENT_STATUS.md](CURRENT_STATUS.md). Unit meliputi writer offline, Admin HTTP, selected-only CLI, izin, stale/reject/rollback, migrasi staging dan transaksi SQLite. Harness F7 menjalankan aplikasi sebenarnya dengan data sintetis dan CLI review nyata; ia bukan login/form Admin browser atau review manusia terhadap data resmi. PostgreSQL, provider resmi, migrasi DB pengguna, deployment dan visual approval tetap terpisah.
