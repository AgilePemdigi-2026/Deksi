# DEKSI Frontend — Detail Indikator (fitur 6)

Laravel 12 + PHP ^8.2 + Blade + Tailwind/Vite, mengikuti composer.json dan style frontend tim. Halaman ini masih memakai **dataset demo lokal**, bukan angka resmi yang telah diverifikasi. Fitur 7, backend dan Docker tidak diimplementasikan pada perubahan ini.

## Menjalankan lokal
Gunakan PHP/Composer yang tersedia di Laragon atau runtime sesuai composer.json. Pada mesin pengembangan saat implementasi, PHP ada di `C:/laragon/bin/php/php-8.3.26-Win32-vs16-x64/php.exe` dan Composer di `C:/laragon/bin/composer/composer.phar`. Tidak ada perubahan PATH global.

Jalankan dari folder Frontend. Contoh berikut mengasumsikan php, composer, node dan npm tersedia pada terminal lokal:

```bash
# Siapkan direktori runtime yang tidak masuk Git.
php -r "foreach (['bootstrap/cache','storage/framework/views','storage/framework/cache/data','storage/framework/sessions','storage/logs'] as \$p) { if (!is_dir(\$p)) mkdir(\$p,0777,true); }"
composer install --no-scripts --no-plugins --prefer-dist --no-interaction
npm ci --ignore-scripts
npm run build
```

Buat `.env.local` dari `.env.example` **hanya bila belum ada**, lalu:

```bash
php artisan key:generate --env=local
php artisan serve --env=local --host=127.0.0.1 --port=8010
```

Jangan menimpa environment milik tim atau commit app key. `.env` sudah terlacak pada baseline repository; ignore baru tidak otomatis menghapus file yang sudah terlacak. Perubahan fitur ini tidak memodifikasi atau menghapus `.env` tersebut. `.env.local`, vendor, node_modules, runtime storage dan public/build diabaikan Git.

Halaman: `/dashboard` lalu Lihat Detail, atau `/indikator/pdb`. Route memakai kode existing: pdb, inflasi, fiskal, investasi, bi_rate dan tpt. Semua tetap dataset demo. Tidak ada endpoint ekonomi baru yang dibuat di backend.

## Perilaku fitur
- Akses publik tanpa login; nilai/satuan/periode/institusi/tanggal berasal dari dataset yang sama.
- Grafik SVG server-rendered dan tabel historis native HTML, tanpa library chart tambahan.
- Gap/null bukan nol; seri tidak konsisten tidak digambar diam-diam.
- Metadata hilang ditandai; contoh badge perubahan dan klaim kausal tidak dipromosikan menjadi hasil analisis.
- Indikator tidak dikenal: HTTP 404 dengan navigasi kembali. Dataset rusak/hilang: HTTP 503 dengan retry.
- Link Source Trace dan AI tidak dibuat palsu; ketersediaannya dijelaskan sebagai fitur/dependensi belum tersedia.

## Pengujian
```bash
php tests/indicator-detail.php
php tests/indicator-detail-regression.php
```

Untuk menjaga lokasi fixture sementara eksplisit, set DEKSI_TEST_SCRATCH ke direktori scratch yang diizinkan sebelum menjalankan regresi. Default runner memakai storage/framework/testing lokal. Runner menjalankan HTTP kernel Laravel nyata dan helper grafik, bukan mock API. Tidak memakai PHPUnit/Behat atau menguji database/backend produksi.

Hasil aktual dan batas kualitas/ISO: [FEATURE_6_VERIFICATION](docs/FEATURE_6_VERIFICATION.md).

## Batas integrasi dan desain
Docker di branch main pada audit membangun deksi/, bukan Frontend/. Tidak ada perubahan Docker dalam pekerjaan ini. Cara menjalankan di atas independen dari Docker tim.

Figma belum dapat diakses. Ekspor SRS final menempatkan gambar dashboard yang sama pada C.1 dan C.2 (keduanya merujuk relationship gambar yang sama). Karena itu style existing dipakai sementara, tetapi kesesuaian halaman dengan High-Fi detail belum dapat disahkan. Kirim frame Detail Indikator yang benar untuk review visual.

Perubahan penunjang minimum: base Controller yang hilang, package/entrypoint Vite dan lockfile, ignore runtime, perbaikan serialisasi Blade dashboard yang menyebabkan HTTP 500, pengurutan import CSS, serta navigasi kartu. Komponen dashboard lainnya bukan cakupan implementasi fitur 6; renderer canvas interaktif dashboard sebelumnya belum tersedia dan tidak ditambahkan pada entrypoint bersama.

## Kolaborasi
Branch kerja feat/detail-indikator dari fe. Tidak direct push ke fe/be/main. Commit, push, PR ke fe dan merge belum dilakukan; memerlukan instruksi dan review sesuai workflow tim.
