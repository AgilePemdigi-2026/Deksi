# Docker backend Sprint 1 — pengembangan lokal

Setup ini untuk **pengembangan lokal saja**. Pada 4 November 2026, Compose config, build image, migrasi pada volume uji baru, startup, HTTP `/api/indicators/` (200), dan Django check lulus dengan Docker Desktop. Resource project dan volume uji dibersihkan sesudahnya. Ini tidak membuktikan kesiapan produksi, data resmi atau integrasi frontend.

## Prasyarat

Docker Desktop dengan Compose, akses build/pull image dan paket, serta checkout branch yang memuat file ini. Backend dan Docker adalah kandidat integrasi, belum PR atau rilis produksi.

## Menjalankan (PowerShell, dari root repository)

Buat kunci acak untuk sesi PowerShell saat ini, jangan gunakan contoh ini sebagai kunci produksi:

```powershell
$env:DEKSI_SECRET_KEY = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
docker compose build backend
docker compose run --rm backend python manage.py migrate --noinput
docker compose up backend
```

Buka `http://127.0.0.1:8000/api/indicators/`. Untuk berhenti tekan Ctrl+C. Kunci di atas berubah setiap sesi baru: ini membatalkan sesi login/token lama; untuk konsistensi lokal, simpan dan gunakan ulang kunci secara aman, tanpa commit atau mengirimkannya.

Database SQLite dan RAW di named volume Compose `backend_data`, bukan database pada host/worktree. **Migrasi mengubah database dalam volume tersebut.** Jika volume berisi data penting, backup terlebih dahulu. Jangan gunakan `docker compose down -v` karena menghapus volume dan data. Build memakai context root agar `backend/requirements-auth.txt` bisa menemukan `../requirements.txt`.

Untuk akun Admin lokal, setelah migrasi:

```powershell
docker compose run --rm backend python manage.py createsuperuser
```

Akun harus dibuat sendiri; jangan membagikan password. Database baru mungkin belum memuat observasi/indikator yang telah direview. Tidak ada data resmi ditambahkan secara otomatis.

## Batas

- Hanya backend. Compose lama dari branch historis juga memuat Laravel dan PostgreSQL; setup baru ini **tidak** mengaktifkan keduanya atau mengklaim dukungan PostgreSQL.
- `DEBUG=True`, Django development server dan binding host loopback hanya untuk penggunaan lokal, bukan deployment.
- Frontend tidak termasuk; origin Vite lokal `localhost:5173` dan `127.0.0.1:5173` diizinkan secara eksplisit. Sesuaikan bila origin frontend berbeda, tanpa membuka CORS ke semua origin.
- BPS tidak dikonfigurasi secara default. Variabel `BPS_API_KEY` dan `BPS_API_BASE_URL` dapat diberikan secara lokal bila sudah tersedia dan diizinkan; jangan commit secret. Tidak ada provider yang dipanggil oleh setup ini.
- Reset Password tetap disabled di settings aplikasi biasa; locmem saat tes bukan email nyata.
- Setelah source berubah, image perlu dibangun ulang. `docker compose build` memakai jaringan dan dapat mengunduh image/dependency.
