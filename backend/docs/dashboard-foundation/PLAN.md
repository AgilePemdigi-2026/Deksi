# Batch 1 — kandidat fondasi API dashboard Sprint 1

## Izin dan kepemilikan
Pengguna mengizinkan Batch 1: integrasi backend filter/feedback dengan perbaikan publik fitur 6–7, perbaikan filter tahun, penguncian kontrak, serta pengujian terisolasi. Tidak termasuk frontend/Prototype 2, pengambilan provider, database pengguna, instalasi, commit/push/PR atau merge branch tim.

## Checkpoint
- Kandidat lokal: `integration/sprint-1-dashboard-be`, berangkat dari BE7 `5c9e20de5d71d74d2c9aabcf00dbf85d04ee8fe3` (mewarisi BE6 `14a4017ea9ee7499df64ea7dca111a6c0438359e`).
- Reuse backend fitur 5/8 dari `f638bf8d5c40f91076caa893dac44d62a2049b88`, bukan menyalin frontend atau fitur sumber data Sprint 2.
- Kandidat integrasi ini bukan pengganti branch/unit publikasi fitur asli.

## Dua item implementasi
1. Integrasikan model, API, Admin dan migrasi feedback serta filter kategori/tahun. Pertahankan riwayat migrasi kedua cabang; tambahkan merge migration tanpa mengubah migrasi existing. Buktikan graph dan upgrade dari kedua sisi menggunakan DB sintetis.
2. Reproduksi bug filter tahun terlebih dahulu, lalu gunakan serializer yang sama untuk observasi terpilih: nilai, unit, sumber, rilis/akuisisi, sparkline, pembanding dan status ketersediaan harus selaras. Terapkan batas publikasi/review yang sama pada jalur baru. Kunci kontrak dan regresi public APIs, termasuk input feedback tak tepercaya.

## Acceptance dan stop condition
- Endpoint ringkasan tanpa filter tetap kompatibel; dashboard tanpa filter setara selain `activeFilters`.
- Filter tahun memilih observasi publik yang direview, tidak membocorkan pending/rejected/unreviewed, tidak menarik nilai/sparkline masa depan, dan tidak mencampur sumber/unit/frekuensi/jenis data.
- Nol tetap nol; nilai kosong bukan nol; desimal asli dan perubahan persen/poin persentase tetap backend deterministik.
- Filter invalid menghasilkan 400, unknown/empty series tetap explicit unavailable.
- Feedback tersimpan pending secara anonim, input tidak valid ditolak tanpa 500, tidak membuka daftar/identitas publik; CSRF middleware tidak dinonaktifkan.
- Satu leaf migrasi; upgrade kedua jalur preservasi data sintetis lulus; tidak memigrasikan DB kerja.
- Unit/regresi public F6/F7, Django check, migration drift dan lint terarah dijalankan dengan interpreter existing. Satu alur HTTP nyata untuk ringkasan/filter/histori/trace/feedback pada database runner-owned. Tidak ada provider data/AI.
- Frontend, checkpoint asal dan shared refs tidak diubah. Setelah pemeriksaan selesai, laporkan bukti serta batas; Batch 2 dan publikasi tetap terpisah.

## Risiko/batas
Tidak membuktikan isi database kerja memenuhi review, kebenaran angka resmi, SMTP, produksi, PostgreSQL, browser frontend, ataupun persetujuan visual. Narasi AI, immutable revision/formula inputs, rate limiting produksi dan fitur sumber data Sprint 2 bukan penambahan batch ini.

## Hasil penutupan teknis

Kedua item Batch 1 selesai pada kandidat lokal: integrasi filter/feedback, penyelarasan konteks/review dan merge migration telah dieksekusi serta diuji. Suite akhir 97 tes unik: 96 lulus, 1 dilewati karena izin symlink Windows. Alur HTTP nyata dan kedua jalur upgrade termasuk dalam total tersebut. Django check, migration drift, lint terarah, format terarah, dependency check dan whitespace check lulus.

Rincian dan batas bukti: [AUDIT.md](AUDIT.md), kontrak frontend: [README.md](README.md), receipt hash/perintah: [VERIFICATION.json](VERIFICATION.json). Ini penutupan teknis Batch 1, bukan persetujuan visual, publikasi, integrasi seluruh auth, atau kelulusan produksi. Batch 2 belum dikerjakan.
