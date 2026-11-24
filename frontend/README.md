# DEKSI Frontend

Antarmuka DEKSI dibangun dengan React, TypeScript, dan Vite.

## Menjalankan

```powershell
npm install
npm run dev
```

Jalankan `npm run build` untuk pemeriksaan TypeScript dan build produksi, serta
`npm run lint` untuk lint. Daftar tes dan runner browser tersedia di `package.json`.

## Struktur

- `src/components/`: komponen bersama dan halaman pengelolaan Admin.
- `src/features/`: fitur yang dikelompokkan per area, seperti dashboard, indikator,
  autentikasi Admin, dan riwayat sinkronisasi.
- `src/styles/` dan stylesheet dekat fitur: gaya global dan gaya khusus fitur.
- `tests/`: tes unit/integrasi serta runner browser dan fixture yang digunakannya.
- `docs/`: keputusan, bukti verifikasi, dan catatan serah-terima frontend.
- `public/`: aset statis yang disalin apa adanya ke build.
