# DEKSI (Deteksi Ekonomi Indonesia)

DEKSI adalah aplikasi web untuk memantau dan menganalisis indikator ekonomi Indonesia. Proyek ini dikembangkan sebagai bagian dari Praktikum Pembangunan Perangkat Lunak oleh Kelompok AgilePemdigi-2026.

## Teknologi

Backend menggunakan Python dan Django. Frontend menggunakan React dengan TypeScript yang dibangun menggunakan Vite. Pemeriksaan kode frontend menggunakan Oxlint, sedangkan backend menggunakan Ruff.

## Fitur

Fitur yang dikembangkan mencakup login admin, lupa dan reset kata sandi, dashboard ekonomi dengan filter, halaman detail indikator yang dapat diakses publik, serta penelusuran sumber data (source trace).

## Struktur Direktori

```
.
├── backend/     Proyek Django (API dan logika bisnis)
├── frontend/    Proyek React + TypeScript (antarmuka pengguna)
└── README.md
```

## Prasyarat

Run lengkap dapat memerlukan lebih dari enam menit tergantung beban mesin. Jika dijalankan melalui agent dengan batas command pendek, gunakan proses terpantau/notification; jangan memotong runner lalu menganggap JSON parsial sebagai hasil suite lengkap. CLI lokal biasa tidak bergantung pada batas tool chat. Command CDP memiliki deadline keseluruhan 30 detik agar event browser yang terus datang tidak memperpanjang satu command tanpa batas; ini tidak mengubah timeout HTTP produk.
Pastikan perangkat Anda telah memiliki Python 3.10 atau lebih baru, Node.js versi LTS, Git, dan PostgreSQL.

## Menjalankan Backend

Jalankan perintah berikut dari folder backend.

```
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements-auth.txt
python manage.py migrate
python manage.py runserver
```

Pada macOS atau Linux, aktivasi virtual environment menggunakan `source venv/bin/activate`. Backend berjalan di http://127.0.0.1:8000/. Konfigurasi development memakai PostgreSQL lokal; database `deksi` harus dibuat terlebih dahulu.

## Lapisan bukti dan batas
Jalankan perintah berikut dari folder backend.

```
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements-auth.txt
python manage.py migrate
python manage.py runserver
```

Pada macOS atau Linux, aktivasi virtual environment menggunakan `source venv/bin/activate`. Backend berjalan di http://127.0.0.1:8000/. Konfigurasi development memakai PostgreSQL lokal; database `deksi` harus dibuat terlebih dahulu.

## Konfigurasi PostgreSQL

Buat database bernama `deksi` di PostgreSQL, lalu salin `backend/.env.example` menjadi `backend/.env` dan isi `POSTGRES_PASSWORD` sesuai password lokal PostgreSQL Anda. Nilai awal koneksi mengikuti HeidiSQL: host `127.0.0.1`, port `5432`, dan user `postgres`. Sesuaikan `POSTGRES_DB` jika nama database Anda berbeda.

Konfigurasi juga menerima `DATABASE_URL` jika Anda lebih memilih satu URL koneksi. File `.env` berisi kredensial lokal dan tidak boleh dimasukkan ke Git. Migrasi hanya membuat skema pada database PostgreSQL yang dipilih; data yang ada di SQLite tidak dipindahkan otomatis.

Test settings dan demo sintetis terisolasi tetap memakai SQLite.

## Menjalankan dengan Docker

Pastikan Docker Desktop dan PostgreSQL lokal aktif, serta database `deksi` sudah dibuat. Siapkan `backend/.env` dengan menyalin `backend/.env.example` bila belum ada, lalu isi `SECRET_KEY` dengan nilai acak lokal dan `POSTGRES_PASSWORD` dengan password PostgreSQL Anda. Compose menghubungkan container backend ke PostgreSQL host pada `127.0.0.1:5432` melalui `host.docker.internal`; variabel host tersebut diatur khusus untuk Docker.

Dari root proyek jalankan:

```
docker compose up --build
```

Compose menjalankan migrasi sebelum backend, lalu menjalankan backend dan frontend. Buka frontend pada http://localhost:5174/. API backend juga tersedia di http://localhost:8000/. Data file mentah disimpan dalam volume Docker `backend_data`; database PostgreSQL tetap berada di host. Hentikan layanan dengan `Ctrl+C` atau `docker compose down`. Jangan gunakan `docker compose down -v` jika ingin mempertahankan volume data.

## Deploy Production ke Coolify

Untuk production, gunakan `docker-compose.prod.yml`, bukan Compose development. File ini membangun frontend sebagai aset statis di Nginx, menjalankan Django dengan Gunicorn, dan menggunakan PostgreSQL dengan volume persisten. Frontend menjadi satu-satunya service yang perlu diberi domain publik di Coolify; arahkan domain ke port container `80`. Backend dan PostgreSQL tetap internal. Pengalihan HTTP ke HTTPS ditangani Coolify agar tidak terjadi redirect berulang di belakang reverse proxy.

Push seluruh perubahan aplikasi dan konfigurasi Docker ke Git, tanpa mengunggah `backend/.env`. Di Coolify, buat resource Docker Compose dari repository dan branch tersebut, lalu atur Docker Compose location ke `/docker-compose.prod.yml`. Tambahkan environment variables berikut di Coolify:

```
SECRET_KEY=<kunci-rahasia-Django-yang-acak>
ALLOWED_HOSTS=<domain-aplikasi-tanpa-https>
POSTGRES_DB=deksi
POSTGRES_USER=deksi
POSTGRES_PASSWORD=<password-database-yang-kuat>
```

Jika frontend dan API memakai domain yang sama, `CSRF_TRUSTED_ORIGINS` dapat dikosongkan. Jika memakai origin HTTPS berbeda, isi dengan origin tepercaya lengkap, misalnya `https://app.example.com`. Atur domain pada service `frontend` ke port `80`, lalu deploy. Buat cadangan PostgreSQL secara berkala; volume persisten tidak menggantikan backup.
## Konfigurasi PostgreSQL

Buat database bernama `deksi` di PostgreSQL, lalu salin `backend/.env.example` menjadi `backend/.env` dan isi `POSTGRES_PASSWORD` sesuai password lokal PostgreSQL Anda. Nilai awal koneksi mengikuti HeidiSQL: host `127.0.0.1`, port `5432`, dan user `postgres`. Sesuaikan `POSTGRES_DB` jika nama database Anda berbeda.

Konfigurasi juga menerima `DATABASE_URL` jika Anda lebih memilih satu URL koneksi. File `.env` berisi kredensial lokal dan tidak boleh dimasukkan ke Git. Migrasi hanya membuat skema pada database PostgreSQL yang dipilih; data yang ada di SQLite tidak dipindahkan otomatis.

- `PLAN.md`: izin, batas dan urutan pilot → ekspansi.
- `qa/run_bdd.py`, `bdd_settings.py`: runner dan lingkungan disposable.
- `qa/browser.py`, `journal.py`, `features/environment.py`: Chrome, journal HTTP, bukti dan cleanup.
- `qa/features/steps/`: bindings API/browser/ekspansi.
- `qa/features/as-built/`, `qa/as-built-manifest.json`, `AS_BUILT_ALIGNMENT.md`: katalog aktual, fingerprint source dan delta terhadap baseline.
- `qa/report_results.py`: ringkasan mekanis hasil aktual, ID, hash dan cleanup.
- `qa/artifacts/<run>/`: `behave.json`, `run.json`, `cleanup.json`, bukti DOM/HTTP/screenshot per skenario.
- `FE_HANDOFF.md`: temuan dan reproduksi untuk pemilik frontend; dokumen lokal, bukan bukti pesan telah dikirim.
Test settings dan demo sintetis terisolasi tetap memakai SQLite.

## Menjalankan dengan Docker

Pastikan Docker Desktop dan PostgreSQL lokal aktif, serta database `deksi` sudah dibuat. Siapkan `backend/.env` dengan menyalin `backend/.env.example` bila belum ada, lalu isi `SECRET_KEY` dengan nilai acak lokal dan `POSTGRES_PASSWORD` dengan password PostgreSQL Anda. Compose menghubungkan container backend ke PostgreSQL host pada `127.0.0.1:5432` melalui `host.docker.internal`; variabel host tersebut diatur khusus untuk Docker.

Dari root proyek jalankan:

```
docker compose up --build
```

Compose menjalankan migrasi sebelum backend, lalu menjalankan backend dan frontend. Buka frontend pada http://localhost:5174/. API backend juga tersedia di http://localhost:8000/. Data file mentah disimpan dalam volume Docker `backend_data`; database PostgreSQL tetap berada di host. Hentikan layanan dengan `Ctrl+C` atau `docker compose down`. Jangan gunakan `docker compose down -v` jika ingin mempertahankan volume data.

## Deploy Production ke Coolify

Untuk production, gunakan `docker-compose.prod.yml`, bukan Compose development. File ini membangun frontend sebagai aset statis di Nginx, menjalankan Django dengan Gunicorn, dan menggunakan PostgreSQL dengan volume persisten. Frontend menjadi satu-satunya service yang perlu diberi domain publik di Coolify; arahkan domain ke port container `80`. Backend dan PostgreSQL tetap internal. Pengalihan HTTP ke HTTPS ditangani Coolify agar tidak terjadi redirect berulang di belakang reverse proxy.

Push seluruh perubahan aplikasi dan konfigurasi Docker ke Git, tanpa mengunggah `backend/.env`. Di Coolify, buat resource Docker Compose dari repository dan branch tersebut, lalu atur Docker Compose location ke `/docker-compose.prod.yml`. Tambahkan environment variables berikut di Coolify:

```
SECRET_KEY=<kunci-rahasia-Django-yang-acak>
ALLOWED_HOSTS=<domain-aplikasi-tanpa-https>
POSTGRES_DB=deksi
POSTGRES_USER=deksi
POSTGRES_PASSWORD=<password-database-yang-kuat>
```

Jika frontend dan API memakai domain yang sama, `CSRF_TRUSTED_ORIGINS` dapat dikosongkan. Jika memakai origin HTTPS berbeda, isi dengan origin tepercaya lengkap, misalnya `https://app.example.com`. Atur domain pada service `frontend` ke port `80`, lalu deploy. Buat cadangan PostgreSQL secara berkala; volume persisten tidak menggantikan backup.

## Menjalankan Frontend

Jalankan perintah berikut dari folder frontend.

```
cd frontend
npm install
npm run dev
```

Frontend berjalan di http://localhost:5173/.

## Konfigurasi Lingkungan

Simpan konfigurasi sensitif pada `backend/.env` dan jangan mengunggahnya ke repositori. Template dapat dilihat pada `backend/.env.example`. Contoh variabel aplikasi:

```
SECRET_KEY=isi-dengan-kunci-rahasia
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173
POSTGRES_DB=deksi
POSTGRES_USER=postgres
POSTGRES_PASSWORD=isi-password-postgresql-lokal
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

## Pemeriksaan Kode

```
cd frontend
npm run lint

cd ../backend
ruff check .
ruff format .
```

## Alur Kerja Git

Pengembangan dilakukan pada cabang fitur, misalnya feature/nama-fitur, kemudian digabungkan ke main melalui pull request setelah ditinjau anggota tim. Hindari melakukan push langsung ke main.

Format pesan commit yang digunakan:

```
feat(fitur-x): deskripsi singkat perubahan
fix(fitur-x): deskripsi perbaikan
docs: perubahan dokumentasi
```

## Tim Pengembang

Kelompok AgilePemdigi-2026, Universitas Airlangga.
