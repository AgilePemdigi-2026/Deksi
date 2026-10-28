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

Pastikan perangkat Anda telah memiliki Python 3.10 atau lebih baru, Node.js versi LTS, dan Git.

## Menjalankan Backend

Jalankan perintah berikut dari folder backend.

```
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Pada macOS atau Linux, aktivasi virtual environment menggunakan `source venv/bin/activate`. Backend berjalan di http://127.0.0.1:8000/.

Jika berkas requirements.txt belum ada, buat terlebih dahulu dari environment yang aktif dengan perintah `pip freeze > requirements.txt`.

## Menjalankan Frontend

Jalankan perintah berikut dari folder frontend.

```
cd frontend
npm install
npm run dev
```

Frontend berjalan di http://localhost:5173/.

## Konfigurasi Lingkungan

Simpan konfigurasi sensitif pada berkas .env dan jangan mengunggahnya ke repositori. Contoh variabel yang dapat digunakan:

```
SECRET_KEY=isi-dengan-kunci-rahasia
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173
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
