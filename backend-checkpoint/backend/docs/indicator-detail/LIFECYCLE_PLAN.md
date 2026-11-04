# Batch 1 — desain implementasi lifecycle dan penyesuaian Batch 2

Otorisasi pengguna: kerjakan Batch 1 lalu sesuaikan Batch 2. Baseline F6 `032b9aec4de0a5d9d96fe94b638329ab5207b586`; F7 `df7f3bd8a0dad2caacb1fe5b22cb2ed6067faabb`. Tidak ada izin baru untuk commit/push/PR/merge, instalasi, provider nyata, atau database pengguna. Checkpoint lama tidak diubah.

## Item 1 — kandidat terpisah dan regresi RED → GREEN

Gunakan satu tabel `ObservationCandidate` dengan payload fakta bertipe JSON tervalidasi, snapshot basis, fingerprint unik, relasi indikator/sumber, status pending/published/rejected dan metadata review tersendiri. Observation publik serta unique constraint-nya dipertahankan. Nilai payload diserialisasi sebagai decimal exact, tanggal ISO; tidak ada float.

Seluruh importer BI/BKPM/fiskal/BPS menyimpan kandidat; fakta identik menjadi no-op. Tidak ada overwrite atau automatic publication atas Observation. Metadata master existing tidak boleh diperbarui diam-diam; perbedaan harus ditolak dengan konflik eksplisit, bukan diabaikan. Source/Indicator Admin CRUD di luar ingestion tetap bukan sistem snapshot immutable.

Mulai dari reproduksi overwrite BI memakai caller asli dan DB test terisolasi, lalu tambah writer lain satu per satu dengan provider offline. Buat migration sumber dan uji pada database task-owned saja.

## Item 2 — review/publikasi dan integrasi

Promosi/rejeksi melalui service transaksi yang memerlukan Admin aktif dengan permission perubahan kandidat. Kandidat dan snapshot basis diverifikasi ulang; candidate basi/ditamper/berulang/konflik tidak diterbitkan. Gunakan update bersyarat pada basis dan unique key untuk menjaga satu pemenang; rollback publikasi dan log jika gagal. Snapshot basis lama disimpan di kandidat sebagai bukti internal, bukan klaim kontrak revision immutable publik.

Django Admin kandidat hanya read-only facts dan action review/publish/reject; tidak ada form publik atau perubahan Login. CLI memakai username Admin existing serta ID kandidat eksplisit, tidak membuat Admin/credential atau mempublikasikan semua kandidat. Jalur legacy validated Observation hanya boleh dipublikasikan lewat tindakan Admin sah yang eksplisit.

Verifikasi idempotensi, presisi, missing vs zero, validasi, hak akses, rejection, stale/concurrent basis dan rollback. Sesuaikan F7 dengan koreksi shared yang sama tanpa rewrite checkpoint. Tambahkan real React→Django skenario data lama saat pending/rejected dan baru setelah review; test guard konteks lama. Update dokumentasi aktif dan resep verifikasi terarah setelah code baru diuji. Bukti unit, browser fixture, real loopback, migration, lint dan canonical tetap terpisah; PostgreSQL, provider resmi dan human visual acceptance tidak diklaim.
