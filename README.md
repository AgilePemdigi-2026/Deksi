# DEKSI Project

Project ini merupakan aplikasi monorepo yang terdiri dari dua bagian utama:

- `backend/` : API REST berbasis Django untuk autentikasi, indikator, dan feedback
- `deksi/` : aplikasi Laravel yang berfungsi sebagai frontend / aplikasi utama

Tujuan dari proyek ini adalah menyediakan sistem yang terintegrasi untuk manajemen autentikasi, data indikator, serta umpan balik pengguna dalam satu ekosistem yang lebih terstruktur.

## Teknologi yang Digunakan

### Backend
- Python
- Django
- Django REST Framework
- PostgreSQL
- CORS headers
- Token Authentication

### Frontend / App
- PHP
- Laravel
- Blade Templates
- Vite
- Composer + npm

## Struktur Proyek

```text
PPL PRAK/
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── feedback/
│   │   └── indicators/
│   ├── backend/
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
│   ├── .env.example
│   ├── composer.json
│   ├── package.json
│   ├── artisan
│   └── vite.config.js
│
└── README.md
```

## Fitur Utama

- Autentikasi pengguna
- Manajemen akun dan login
- API indikator
- Pengumpulan data feedback
- Integrasi backend dan frontend dalam satu proyek

## Persyaratan Sistem

Sebelum menjalankan project, pastikan environment berikut sudah tersedia:

- Python 3.10+
- pip
- PostgreSQL
- PHP 8.3+
- Composer
- Node.js + npm
- Git

## Setup Backend Django

Masuk ke folder backend:

```bash
cd backend
python -m venv .venv
```

Aktifkan virtual environment:

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Install dependency:

```bash
pip install -r requirements.txt
```

Buat file `.env` di folder `backend/` dengan contoh konfigurasi berikut:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=deksi
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173
FRONTEND_URL=http://localhost:8000
```

Lakukan migrasi database:

```bash
python manage.py migrate
```

Jalankan server backend:

```bash
python manage.py runserver 0.0.0.0:8000
```

API backend biasanya tersedia pada endpoint seperti:

```text
http://localhost:8000/api/v1/
```

## Setup Aplikasi Laravel

Masuk ke folder `deksi`:

```bash
cd deksi
```

Install dependency PHP:

```bash
composer install
```

Salin file environment:

```bash
copy .env.example .env
```

Generate application key:

```bash
php artisan key:generate
```

Install dependency frontend:

```bash
npm install
```

Jalankan migrasi database Laravel:

```bash
php artisan migrate
```

Jalankan server Laravel:

```bash
php artisan serve
```

Jika ingin menjalankan mode development frontend Vite:

```bash
npm run dev
```

## Menjalankan Project Secara Bersamaan

Untuk pengembangan penuh, biasanya jalankan dua terminal terpisah:

Terminal 1 (backend Django):
```bash
cd backend
python manage.py runserver 0.0.0.0:8000
```

Terminal 2 (Laravel):
```bash
cd deksi
php artisan serve
```

Atau untuk frontend Vite:

```bash
cd deksi
npm run dev
```

## Endpoint API Utama

Backend Django menyediakan route API utama berikut:

- `/api/v1/auth/`
- `/api/v1/indicators/`
- `/api/v1/feedback/`

## Catatan Pengembangan

- Pastikan PostgreSQL sudah aktif sebelum menjalankan backend.
- Gunakan `.env` secara terpisah untuk konfigurasi lingkungan yang sensitif.
- Saat deploy ke production, jangan memakai `DEBUG=True` dan ganti `SECRET_KEY` dengan nilai yang aman.
- Pastikan port backend dan frontend tidak bentrok jika dijalankan pada mesin yang sama.
