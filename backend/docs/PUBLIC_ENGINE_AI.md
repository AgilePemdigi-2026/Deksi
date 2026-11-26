# Penjelasan Economic Engine melalui Gemini

## Alur yang tersedia

Dashboard publik menampilkan **Lihat penjelasan sederhana** di bagian Struktur ekonomi. Halaman yang dibuka atau dimuat ulang tidak mengirim permintaan generasi. Klik melakukan POST ber-CSRF untuk mengajukan versi data saat ini. Pengunjung lain dengan konteks yang sama mendapat identitas permintaan tersimpan yang sama, bukan panggilan Gemini baru. Jika versi sudah disetujui, klik itu langsung mengambil dan menampilkan kontennya.

Worker terpisah `public-engine-ai-worker` mengklaim antrean secara atomik. Ia menggunakan host Gemini tetap, model yang dikonfigurasi operator dan `GEMINI_API_KEY` hanya di environment worker. Tidak ada key pada frontend, bundle JavaScript, request browser ke Google atau repository. Worker tidak memegang transaksi database saat HTTP. Request running yang terputus ditandai unknown setelah tiga menit; tidak ada retry inference otomatis atau fallback model.

Hanya metrik backend yang memenuhi syarat dikirim. PMTB saja dapat dijelaskan ketika konsumsi rumah tangga belum tersedia; nilai yang hilang bukan nol. Paket memuat periode, formula, hasil, sumber dan batasannya. Validator membatasi struktur serta teks. Ini bukan bukti kebenaran semantik atau pengganti review.

Draft siap berada di **Admin → Review Narasi AI** (`/admin/public-engine-ai`). Akses memerlukan sesi staff aktif dan permission `indicators.review_publicengineairequest` (atau superuser yang sah). Tidak ada penambahan hak otomatis. Reviewer melihat snapshot dan teks lalu menyetujui/menolak digest konten tersebut. Publik tidak memperoleh draft atau catatan reviewer. Simulasi reviewer dalam tes bukan keputusan manusia pada produksi.

Pembacaan publik mengecek snapshot sumber terkini lagi dan mengembalikan identitas tiap metrik. Frontend menolak konten dengan periode/input/result yang tidak cocok. Ketika data berubah, narasi lama tidak dipasangkan pada hasil baru. Status gagal, rejected, unknown dan stale ditampilkan tanpa mengarang penjelasan. Tidak ada regenerasi otomatis untuk request gagal/unknown; rekonsiliasi operator memerlukan keputusan terpisah, jangan menghapus riwayat untuk memaksa retry.

## Aktivasi di Coolify

Key telah dimasukkan pengguna di Coolify, tetapi penyimpanannya bukan bukti validitas key atau keberhasilan koneksi ke Gemini. Compose meneruskan key hanya ke worker. Tambahkan tiga environment variable runtime berikut ketika siap mengaktifkan:

| Name | Value awal |
|---|---|
| `DEKSI_PUBLIC_ENGINE_AI_ENABLED` | `true` |
| `DEKSI_ENGINE_AI_DAILY_LIMIT` | `1` |
| `DEKSI_PUBLIC_ENGINE_AI_MODEL` | `gemini-3.5-flash-lite` |

Defaults tetap **false / 0 / kosong** agar deploy tanpa konfigurasi tidak mengirim inference. Tidak perlu menyalin key ke `VITE_...`, Compose literal, Git, log atau chat. Gunakan nilai key yang sudah disimpan sebagai `GEMINI_API_KEY`. Runtime dan buildtime adalah pengaturan yang berbeda; key tidak dibutuhkan saat build.

Pengguna mengonfirmasi project Gemini free tier tanpa billing aktif. Model tersebut tercantum di dokumentasi resmi Google saat diperiksa pada 26 November 2026: [model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) dan [pilihan model](https://ai.google.dev/gemini-api/docs/choosing-a-model). Ini bukan inspeksi billing project atau jaminan kuota akun. Jangan aktifkan billing, model/fallback berbayar, tool grounding atau retry untuk mengatasi limit. Ketersediaan aktual tetap harus dibuktikan oleh respons akun.

Limit adalah jumlah **pengajuan baru per hari** (timezone aplikasi), direservasi dengan transaksi dan pembaruan bersyarat lintas worker; dibatasi maksimal 100 oleh kode, defaults 0. Reuse konteks tidak menambah hitungan. Ini bukan pembatas tagihan moneter atau jaminan jumlah dispatch pada satu tanggal jika antrean hari sebelumnya baru diproses kemudian. Awali 1; jangan menaikkan limit tanpa izin pengguna. Request tanpa hasil juga dapat menghabiskan satu reservasi, secara konservatif.

Sesudah kode/variabel siap, deploy menggunakan alur Coolify tim. Startup backend yang sudah ada menjalankan `migrate`; migrasi baru `0027_public_engine_ai` **menambah tiga tabel**, tidak mengubah observasi/RAW lama. User melanjutkan setelah risiko auto-deploy/migrasi dan backup belum terverifikasi disampaikan; hal itu bukan bukti backup tersedia atau deploy sukses. Periksa backup dan rollback operasional sebelum migrasi bila kebijakan tim mensyaratkan. Agent tidak menjalankan migrasi pada database produksi secara langsung.

Setelah deployment, periksa health/log backend dan worker tanpa menampilkan nilai environment; gunakan tombol publik hanya untuk satu percobaan yang diizinkan, lalu review di Admin. Jika disabled/limit/model/key belum siap, jangan menyebut inference berhasil. Jika 403 di Admin, periksa izin akun, jangan melemahkan proteksi. Jika status unknown, jangan mengulang dengan identitas baru.

## Endpoint

- POST `/api/public-engine-ai/requests/`: `requestKey` UUID dan `quarter` tanggal akhir triwulan. Ber-CSRF; hanya enqueue atau reuse. Respons metadata dapat memakai UUID bersama yang berbeda dari UUID pengunjung.
- GET `/api/public-engine-ai/requests/<uuid>/`: status; konten dan `metricsBinding` hanya setelah approved dan snapshot cocok.
- GET `/api/admin/public-engine-ai/`: draft siap/current untuk reviewer berizin.
- POST `/api/admin/public-engine-ai/<id>/review/`: `contentDigest`, `decision` (`approved`/`rejected`), `notes`; sesi/permission/CSRF dan digest diperiksa.

## Pemeriksaan aktual

- Backend: 176 tes SQLite hermetik lulus; termasuk satu jalur POST → worker dengan transport Gemini palsu → draft tersembunyi → review simulasi → GET publik, dengan hanya PMTB tersedia. Tidak ada panggilan provider nyata.
- Frontend: 10 tes client publik/review, 19 tes Economic Engine dan 100 regresi Sprint 1 lulus pada pemeriksaan terkait; angka tersebut bukan seluruh suite repository.
- Browser: enam skenario menggunakan Chrome disposable dan komponen React yang sebenarnya, dengan API **sintetis**: tidak ada request saat mount; klik enqueue; reuse UUID bersama; draft tersembunyi; approved teks escaped; mismatch identitas ditolak. Ini bukan browser-ke-Django atau pembuktian produksi.
- TypeScript dan production build lulus. Warning bundle >500 kB tetap ada; lint terarah memiliki warning set-state-in-effect pada halaman Admin yang baru, bukan dianggap nol warning.
- Uji upgrade SQLite memori 0026 → 0027, schema drift dan apply ulang lulus; tabel lama serta satu sentinel auth sintetis tidak berubah. Tidak membuktikan upgrade/konkurensi PostgreSQL produksi atau backup nyata.

Perintah dari root, interpreter/dependency existing:

```text
<backend-python> -B backend/indicators/tests/run_engine_ai_tests.py --scratch <absolute-existing-scratch>
```

Dari `frontend`: `npm run test:public-engine-ai`, `npm run test:economic-engine`, `npm run test:sprint-1`, dan `npm run build`. Browser memerlukan Chrome existing dan `HERMES_TEST_SCRATCH` absolut: `node tests/public-engine-ai.browser.mjs`. Tidak ada install dependency di fase ini.

Push kode, status CI, deploy, respons Gemini nyata dan review manusia adalah bukti terpisah. Jangan mengklaim seluruhnya selesai berdasarkan tes di atas.
