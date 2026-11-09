# Frontend Docker — demo lokal Sprint 1

Jalankan backend demo terpisah terlebih dahulu sesuai `backend/docs/sprint1-unified/DEMO.md` pada checkout backend. Dataset demo adalah simulasi, bukan data resmi. Docker Desktop harus aktif dan port 5174 serta 18080 tidak boleh dipakai layanan lain.

Dari root checkout frontend, jalankan:

```powershell
docker compose -p deksi-frontend-demo -f compose.frontend.yml up --build -d
```

Buka `http://127.0.0.1:5174/`. Konfigurasi memakai Docker Desktop `host.docker.internal:18080` untuk API dan autentikasi. Untuk menghentikan hanya frontend ini, jalankan dari root checkout yang sama:

```powershell
docker compose -p deksi-frontend-demo -f compose.frontend.yml down
```

Tidak ada volume frontend dalam Compose ini. Jangan menghentikan atau menghapus volume backend untuk menghentikan frontend. `compose.frontend.yml` menggantikan `docker-compose.yml` frontend agar dapat berdampingan dengan konfigurasi backend; gunakan perintah eksplisit di atas. Ini konfigurasi pengembangan lokal, bukan produksi.
