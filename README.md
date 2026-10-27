# DEKSI Project

Project ini terdiri dari dua layanan utama dalam satu repositori:

- `backend/` : API REST berbasis Django
- `deksi/` : aplikasi Laravel
- `docker-compose.yml` : menjalankan seluruh stack lokal beserta PostgreSQL

Tujuan proyek ini adalah menyediakan layanan autentikasi, indikator, dan feedback dalam satu ekosistem yang terintegrasi.

## Teknologi yang Digunakan

### Backend
- Python
- Django
- Django REST Framework
- PostgreSQL
- Token Authentication
- CORS

### Frontend / App
- PHP
- Laravel
- Blade
- Composer
- npm / Vite

## Struktur Proyek

```text
PPL PRAK/
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── feedback/
│   │   └── indicators/
│   ├── backend/
│   ├── .env
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   ├── manage.py
│   └── requirements.txt
│
├── deksi/
│   ├── app/
│   ├── config/
│   ├── database/
│   ├── public/
│   ├── resources/
│   ├── routes/
│   ├── tests/
│   ├── .env
│   ├── .env.example
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   ├── composer.json
│   ├── package.json
│   └── artisan
│
├── docker-compose.yml
├── .dockerignore
├── README.md
└── .gitignore
```

## Fitur Utama

- Autentikasi dan manajemen akun
- Endpoint API untuk indikator
- Endpoint API untuk feedback
- Integrasi backend dan frontend dalam satu monorepo
- Setup lokal berbasis Docker

## Persyaratan Sistem

Sebelum menjalankan project, pastikan perangkat Anda sudah memiliki:

- Docker + Docker Compose
- Git
- Browser untuk mengakses frontend/backend

Untuk setup non-Docker, Anda juga butuh:

- Python 3.10+
- pip
- PHP 8.3+
- Composer
- Node.js + npm
- PostgreSQL

## Setup dengan Docker

Pastikan Docker sudah aktif di mesin Anda.

Jalankan perintah berikut di root project:

```bash
docker compose up --build
```

Setelah semua container berjalan, maka:

- Backend Django: http://localhost:8000
- Laravel App: http://localhost:8001
- PostgreSQL: localhost:5432

## Konfigurasi Default Database

Database yang digunakan adalah PostgreSQL dengan detail berikut:

```env
DB_NAME=deksi
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

## File Environment

Sudah disiapkan file environment untuk masing-masing layanan:

- `backend/.env`
- `deksi/.env`

Jika dibutuhkan, Anda bisa menyesuaikan nilai env sesuai kebutuhan deploy atau local development.

## Run Manual (Tanpa Docker)

### 1. Backend Django

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 2. Laravel App

```bash
cd deksi
composer install
php artisan key:generate
php artisan migrate
php artisan serve --host=0.0.0.0 --port=8001
```

## Endpoint API Utama

Backend Django menyediakan route utama berikut:

- `/api/v1/auth/`
- `/api/v1/indicators/`
- `/api/v1/feedback/`

## Catatan Pengembangan

- Untuk lokal development, gunakan konfigurasi Docker agar lebih konsisten.
- File `.env` tidak disarankan dipublish ke repository production dalam bentuk yang sama.
- Pastikan port `8000`, `8001`, dan `5432` tidak digunakan oleh aplikasi lain.
- Jika menjalankan di production, ubah `DEBUG=True` dan kunci secret ke nilai yang aman.

## Kontrol Docker

Untuk melihat container yang sedang berjalan:

```bash
docker compose ps
```

Untuk menghentikan container:

```bash
docker compose down
```

Untuk membersihkan volume database:

```bash
docker compose down -v
```

## Lisensi

Project ini belum memiliki lisensi eksplisit yang ditetapkan secara formal. Anda dapat menyesuaikan sesuai kebijakan tim atau institusi.

## Frontend root dan Detail Indikator (fitur 6)

Repository juga memuat aplikasi frontend Laravel/Blade pada root, hasil pemindahan dari `Frontend/`. Aplikasi ini berbeda dari aplikasi Laravel pada `deksi/` yang dijelaskan pada setup Docker di atas; pemindahan lokasi tidak otomatis mengubah target Docker.

- [Panduan frontend root: setup, fitur, pengujian, dan batas integrasi](docs/FRONTEND.md).
- [Bukti pengujian dan batas penerimaan fitur 6](docs/FEATURE_6_VERIFICATION.md).

Halaman Detail Indikator dapat diakses publik tanpa login dan saat ini memakai data demo lokal. Dokumen ini tidak menyatakan frontend root sudah terhubung ke API/data resmi atau dijalankan oleh Docker. Pengujian fitur secara historis tidak menggantikan pengujian hasil integrasi.
