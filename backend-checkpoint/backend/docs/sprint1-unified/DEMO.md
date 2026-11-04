# Dataset simulasi Sprint 1 — backend demo terisolasi

Dataset ini berisi enam indikator dan 48 observasi contoh (2024–2025). **Seluruh angka, nama sumber dan institusi adalah simulasi; bukan data resmi.** Reviewer nonaktif `demo-simulation-not-human-review` hanya penanda teknis agar preview publik bekerja; bukan review manusia atau verifikasi resmi. Reset Password tetap disabled.

## Jalankan database demo secara terpisah

Dari root checkout backend yang **sudah memuat file demo ini**, di PowerShell dengan Docker Desktop aktif:

```powershell
$env:DEKSI_DEMO_SECRET_KEY = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
docker compose -p deksi-demo -f compose.demo.yml build backend
docker compose -p deksi-demo -f compose.demo.yml run --rm backend python manage.py migrate --noinput
docker compose -p deksi-demo -f compose.demo.yml run --rm backend python manage.py seed_demo
docker compose -p deksi-demo -f compose.demo.yml up -d backend
```

Buka `http://127.0.0.1:18080/api/indicators/`. Port 18080 harus kosong; jangan hentikan container lain otomatis. Server ini khusus demo, bukan produksi. Simpan kunci lokal dengan aman jika ingin sesi login tetap konsisten setelah container dibuat ulang; jangan bagikan atau commit kuncinya.

**Perintah seed wajib hanya dijalankan sekali** pada database demo baru. Jika database memiliki indikator, sumber, observasi, kandidat, RAW, feedback atau user, perintah berhenti tanpa menimpa apa pun. Perintah juga menolak settings selain `backend.settings_demo`, `DEBUG=False`, atau database selain `/data/deksi-demo.sqlite3`. Database demo disimpan dalam volume project Compose `deksi-demo`, bukan volume backend biasa. Jangan gunakan `down -v`: itu menghapus volume beserta datanya. Backup volume sebelum migrasi bila berisi data penting.

## Hasil pemeriksaan tahap ini

Tiga tes unit lulus pada database SQLite memori; lint lulus. Build image dari source lokal, migrasi pada volume uji baru, seed, penolakan seed ulang, startup dan HTTP indikator/trend lulus; container dan volume uji milik tes dibersihkan. Uji ini bukan uji checkout bersih pada laptop teman, frontend atau produksi.

File ini, command seed, settings demo dan Compose demo **belum tentu tersedia di GitHub** sampai ada commit/push tersendiri. Frontend Docker saat ini mengarah ke host port 18080; integrasi dan instruksi lengkap frontend–backend dari checkout bersih adalah langkah terpisah yang belum diuji pada tahap ini.
