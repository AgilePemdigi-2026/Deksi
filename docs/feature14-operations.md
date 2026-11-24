# Fitur 14 — panduan operasional kandidat BPS

Status: kandidat lokal, belum dipublikasikan, belum dideploy dan belum diuji dengan BPS nyata. Perubahan bergantung pada fitur 12/13; jangan menganggap PR #31 telah merge tanpa pemeriksaan terpisah.

## Sebelum migrasi atau deployment

- Koordinasikan rilis dengan pemilik database dan tim; periksa riwayat migrasi aktual serta konflik migrasi pada versi hasil integrasi. Migrasi fitur 14 adalah `0015_resyncjob` dan `0016_resync_reconciliation`; fitur 12/13 juga membawa migrasi pendahulu. Nomor ini bisa berubah saat integrasi, sehingga periksa ulang sebelum rilis.
- Buat backup PostgreSQL yang konsisten menggunakan prosedur tim, simpan secara aman, dan uji restore pada database **terpisah** sebelum migrasi. Konfirmasi siapa yang berwenang mengembalikan backup, target restore dan dampak data setelah titik backup. Belum ada bukti backup atau restore produksi dalam pekerjaan ini.
- Compose produksi saat ini menjalankan migrasi otomatis saat backend mulai. Jangan menjalankannya terhadap database pengguna sebelum backup diverifikasi dan rilis disetujui. Pengujian migrasi di database disposable bukan bukti keamanan migrasi produksi.
- Pasang `BPS_API_KEY` hanya melalui pengelola rahasia deployment, tanpa menuliskannya di repositori atau memasukkannya ke URL aplikasi/browser. Worker memakai origin WebAPI BPS tetap dan tidak mengikuti redirect. Protokol BPS yang digunakan menempatkan kunci di path request keluar: redaksi logger HTTPX aplikasi **tidak** membuktikan bahwa proxy, APM, tracing, jaringan, atau penyedia tidak merekamnya. Tinjau konfigurasi masing-masing dan kebijakan retensinya sebelum memakai kunci nyata; jangan mengandalkan redaksi aplikasi saja.
- Siapkan proses `resync-worker` terpisah dari Gunicorn. Kandidat `docker-compose.prod.yml` mendefinisikannya dan menunggu backend sehat, sehingga migrasi backend harus selesai terlebih dahulu. Konfigurasi baru belum dideploy; keberhasilan `docker compose config` bukan bukti proses berjalan.

## Saat operasi

1. Admin meninjau riwayat dan status antrean sumber BPS, lalu mengirim satu permintaan. `queued` berarti diterima tapi belum dimulai. Jika worker belum berjalan, permintaan bisa tetap antre; ini bukan keberhasilan sinkronisasi.
2. `running` berarti proses telah dimulai dan belum ada hasil final; **tidak** membuktikan worker masih hidup. Jangan otomatis mengulang pekerjaan tertinggal atau memakai usia job sebagai bukti kematian proses.
3. Bila hasil tidak pasti, periksa riwayat, kandidat yang sudah terbentuk, log aman, dan keadaan worker sebelum mencatat pemeriksaan manual. Rekonsiliasi mencatat Admin, waktu dan alasan sebagai `unknown`, bukan keberhasilan atau kegagalan; waktu selesai aktual tetap tidak diketahui. Hasil parsial yang sudah ada tidak otomatis dibatalkan atau dipublikasikan.
4. Pagar database memeriksa status job dalam transaksi setiap kali worker BPS membuat metadata atau kandidat. Setelah rekonsiliasi, worker lama tidak boleh menulis kandidat melalui jalur ini. Request HTTP yang sudah terlanjur dikirim tidak otomatis dibatalkan: periksa/hentikan proses lama sesuai prosedur operasional sebelum mengirim ulang. Pagar ini tidak mengklaim melindungi handler sumber lain atau penulis di luar jalur BPS yang diaudit.
5. Tinjau kandidat sebelum publikasi. Nilai publik lama tetap digunakan sampai ada review/publikasi yang sah. Jangan memperlakukan berhasilnya pengambilan sebagai verifikasi angka atau publikasi.

## Bukti yang masih diperlukan sebelum aktivasi

- Review tim atas rancangan recovery, hak Admin, log dan konfigurasi worker.
- Verifikasi backup dan restore terisolasi pada lingkungan rilis, serta hasil migrasi terhadap salinan disposable yang sesuai.
- Tes stack production-like dan proses worker pada konfigurasi kandidat; review visual dan penerimaan pengguna terpisah.
- Persetujuan terpisah untuk penggunaan BPS nyata, publikasi, migrasi database pengguna dan deploy. Sumber selain BPS belum diaktifkan.
