# Kandidat backend Sprint 1 gabungan

Status: implementasi lokal diizinkan pengguna pada sesi ini; bukan izin commit/push/PR/merge.

Pembaruan izin setelah implementasi: pengguna meminta audit cepat lalu mengizinkan commit dan push `integration/sprint-1-unified-be`. Tidak ada izin PR, merge shared branch, atau publikasi ulang lane sumber. Status awal di atas dipertahankan sebagai riwayat batas tahap implementasi.

## Dua item dan acceptance
1. Gabungkan source existing Login/Reset dengan snapshot lengkap backend publik Batch 1 dalam worktree baru `sprint-1-unified-be`, branch `integration/sprint-1-unified-be`. Parent Git `5c9e20de5d71d74d2c9aabcf00dbf85d04ee8fe3`; auth checkpoint `a99830be1f6c877dd79feb704db191231afe0c7b`. Snapshot overlay mencakup source tracked + untracked nonignored backend publik, bukan DB/.env/artifact runtime. Jangan menulis ke kedua sumber atau frontend.
2. Jalankan suite auth/reset dan indikator dengan satu settings gabungan yang memakai aplikasi, URL, middleware dan backends konfigurasi aplikasi. Tambahkan uji lintas fitur melalui HTTP loopback: publik sebelum/setelah Login, feedback CSRF dan rotasi Login, reset locmem dan invalidasi sesi. Jalankan concurrency reset terpisah pada SQLite scratch; check migrasi/lint/dependency. Catat outcome aktual, hashes, source guards dan batas bukti.

## Batas izin dan risiko
- Reset tetap disabled pada konfigurasi aplikasi biasa; enabled hanya settings pengujian dengan locmem. Tidak ada SMTP/inbox/provider/AI/instalasi dependency.
- Database aplikasi, .env, profil Hermes dan frontend tidak disentuh. Server dimiliki test LiveServer dan dihentikan teardown.
- Kandidat lokal bukan update backend referensi session frontend. Peralihan runtime frontend memerlukan koordinasi setelah verifikasi.
- Integrasi kode bukan bukti visual frontend, data resmi, PostgreSQL, timing email atau production readiness.
- Source guards memeriksa kedua sumber backend; frontend boleh berubah oleh session pemiliknya dan bukan guard immutability session ini.

## Bukti
`backend/.artifacts/sprint1-unified/sources-before.json` berisi source hashes dan ref baseline. Dokumen verifikasi final akan memisahkan suite gabungan, concurrency, pemeriksaan statis, dan batas acceptance.
