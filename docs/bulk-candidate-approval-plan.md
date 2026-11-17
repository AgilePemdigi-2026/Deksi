# Rencana implementasi: persetujuan massal kandidat sumber

**Status:** usulan untuk dievaluasi; fitur belum diimplementasikan.

**Baseline:** `main` commit `8c9a07604e27b010da36eeedd13dced2d476436f` (17 November 2026).

**Tujuan:** reviewer berwenang dapat menyetujui seluruh kandidat pending dari satu sumber yang dibuka, termasuk halaman lain, berdasarkan daftar kandidat yang dibekukan dan dikonfirmasi secara sadar. Kandidat bermasalah dilewati dan dilaporkan satu per satu.

## Kondisi yang sudah diperiksa

- `backend/indicators/candidate_views.py`: list difilter per sumber/status dan dipaginasi 20; review HTTP menerima satu ID dan fingerprint, mensyaratkan staf serta izin reviewer, dan memakai transaksi dengan pemeriksaan source, status dan fingerprint.
- `backend/indicators/lifecycle.py`: `review_candidate` memvalidasi kandidat dan basis sebelumnya, menyimpan reviewer/waktu serta pencatatan publikasi. Setiap transaksi dapat memperbarui observasi yang sudah ada bila kandidat adalah revisi.
- `frontend/src/features/candidates/CandidateReview.tsx`: review individual memakai konfirmasi, penanda hasil tidak pasti, pembacaan ulang dan kontrol busy. Penanda sesi bukan lock server atau bukti server sudah berhenti.
- `backend/indicators/management/commands/publish_observations.py` menerima ID eksplisit tetapi membungkus seluruh daftar dalam satu transaksi: itu **bukan** implementasi massal parsial yang diminta.
- Screenshot pengguna menunjukkan 98 kandidat BPS pending pada saat screenshot, bukan jumlah terkini yang dijamin. Tidak ada klaim bahwa kandidat-kandidat itu sudah diverifikasi.
- Pengguna menyatakan backup database produksi tidak ada; target database, pemulihan, status aktual Coolify, dan keputusan apakah backup sudah tersedia saat rilis masih harus dikonfirmasi.

## Kontrak perilaku yang diusulkan

1. Satu sumber pada panel aktif; mencakup seluruh halaman pending, bukan sumber lain. Kumpulan kandidat harus dibekukan sebagai pasangan **ID dan fingerprint** pada pratinjau; hasil pencarian yang berubah saat konfirmasi tidak boleh menambahkan anggota baru diam-diam. Bila snapshot lengkap tidak dapat dibuat secara konsisten atau melebihi batas aman, hentikan dengan pesan jelas, bukan menyetujui subset secara tersembunyi. Rancangan mekanisme snapshot dan batas jumlah perlu dibuktikan.
2. Sebelum keputusan, tampilkan daftar per kandidat (indikator, nilai, satuan, periode, source snapshot, indikasi revisi serta ketersediaan RAW/tanggal rilis), total dan cakupan. Buat daftar dapat ditelusuri tanpa menganggap Admin sudah membaca setiap item. Munculkan peringatan bahwa konfirmasi mempublikasikan data, perubahan observasi mungkin terjadi, dan konfirmasi bukan verifikasi otomatis. Batalkan tanpa efek.
3. Backend memeriksa otorisasi ulang dan CSRF serta source binding, status, fingerprint, validasi, stale-base, urutan lock dan audit pada setiap kandidat melalui lifecycle yang ada. Setiap kandidat memiliki transaksi independen: kandidat konflik, tidak cocok, sudah diproses atau tidak valid dilewati dan dicatat; kandidat lain tetap dapat diproses. Tidak ada bulk SQL langsung melewati lifecycle.
4. Hasil diklasifikasi per ID sebagai berhasil, dilewati/gagal dengan alasan aman, atau belum pasti/belum diketahui. Bedakan tidak dimulai, sedang berjalan, selesai dan hasil tidak pasti; hasil belum pasti tidak boleh dianggap gagal atau aman untuk diulang. Tampilkan total yang konsisten dengan detail.
5. Kandidat baru setelah snapshot, sumber lain dan kandidat yang sudah diproses tidak ikut dipublikasikan. Review individual tetap berfungsi. Tidak membuat angka, waktu rilis, RAW, status verifikasi atau sumber.
6. Selama aksi dan pembacaan hasil, cegah navigasi aplikasi terkait serta duplikasi submit; browser Back, reload dan tutup tab tidak dijanjikan tertahan. Jangan otomatis mengulang mutasi setelah timeout/terputus. Baca kembali hasil operasi dan kandidat yang tepat; `pending` pada satu waktu bukan bukti server sudah selesai. Bila hasil tidak dapat dipastikan, blokir pengulangan sampai ada prosedur pemeriksaan dan keputusan manusia.

## Keputusan produk yang belum ada jawaban

- **RAW atau tanggal rilis tidak tersedia:** pilih apakah (A) diperbolehkan setelah Admin memeriksa bukti resmi secara terpisah dan mengonfirmasi, atau (B) dikecualikan dari aksi massal. Keduanya tetap menampilkan data hilang apa adanya; link portal bukan bukti verifikasi. Ini **bukan** keputusan yang sudah diambil. Jangan mengaktifkan aksi massal sampai kebijakan disetujui.
- **Batas volume dan timeout:** tentukan berdasarkan batas request, beban terukur, dan pengalaman Admin, bukan menganggap 98 sebagai batas tetap. Kegagalan snapshot atau hasil parsial wajib terlihat.
- **Persetujuan dan pemulihan produksi:** identifikasi pemilik deployment dan database, rencana backup yang konsisten dan restore terpisah; pengguna menyatakan backup database belum tersedia. Implementasi/tes lokal bukan izin publikasi data atau deploy.

## Desain teknis untuk dievaluasi

**Opsi yang direkomendasikan untuk prototipe:** backend membuat pratinjau berupa daftar tetap dan pengenal snapshot yang terikat ke sumber, reviewer, fingerprint, serta masa berlaku; konfirmasi menerima identitas snapshot yang benar-benar ditampilkan. Setelah itu gunakan operasi yang punya identitas stabil dan catatan hasil yang dapat dibaca ulang. Implementasi spesifik—termasuk apakah perlu model/tabel job, berapa lama disimpan dan bagaimana proses berhenti/ditandai setelah server restart—perlu dibuktikan dan ditetapkan sebelum coding. Jangan menyebut snapshot atau operasi persisten sudah tersedia.

**Tradeoff:** catatan durable per batch memudahkan pemulihan ketika respons hilang/reload, tetapi bisa memerlukan migrasi, pembersihan data, dan pengujian PostgreSQL. Reuse endpoint satu per satu dari browser lebih kecil, tetapi halaman bisa tertutup di tengah proses; state sesi bukan lock server dan tidak membuktikan hasil semua request. Jangan memilih loop frontend sebagai jalan pintas tanpa rancangan hasil tak pasti dan uji kegagalan jaringan yang memadai. CLI existing all-or-nothing tidak memenuhi semantik parsial.

**Keamanan dan konsistensi:** batasi ukuran dan validasi input; jangan percaya jumlah/identitas dari frontend tanpa validasi server. Binding snapshot untuk reviewer lain dan sumber lain harus ditolak. Proses bersamaan atau permintaan duplikat tidak boleh mempublikasikan satu kandidat dua kali. Jaga konsistensi urutan lock dengan staging dan review individual; hindari transaksi sepanjang seluruh batch dan tampilkan status yang benar saat crash/restart. Gunakan idempotensi serta readback operasi yang terbukti; jangan menyatakan exactly-once tanpa bukti pada kondisi crash dan jaringan.

## Batch 1 — 1 dan 2: kontrak dan backend

### 1. Finalisasi kontrak, batas, dan skenario
- Tetapkan keputusan RAW/tanggal rilis, mekanisme snapshot/kedaluwarsa, semantik partial dan recovery, volume, audit dan kebutuhan migrasi setelah memeriksa versi terkini serta instruksi checkout.
- Rinci respons API preview/submit/status sebagai **proposal**, bukan klaim endpoint sudah ada; tentukan status ketika operasi tidak pernah dimulai, masih berjalan, terhenti, atau hasil belum pasti.
- Bukti penerimaan: setiap ID/fingerprint yang dikonfirmasi bisa dipetakan ke hasil; tidak ada item baru dari luar snapshot. Periksa contoh 0, 1, >20 kandidat, snapshot kedaluwarsa dan data berubah saat preview.

### 2. Backend batch memakai lifecycle existing
- Kandidat lokasi perubahan: `backend/indicators/candidate_views.py`, `backend/indicators/lifecycle.py`, `backend/indicators/urls.py`, model/migrasi hanya jika disetujui desain; tambahkan tes di `backend/indicators/tests/`.
- Uji data sintetis: sumber berbeda, kandidat lain disetujui bersamaan, kandidat diganti setelah preview, validasi gagal, izin ditarik, CSRF hilang, duplicate/replay, pembatalan sebelum submit dan audit per item. Validasi ulang otorisasi dan scope di server.
- Gunakan transaksi terpisah per kandidat dan PostgreSQL disposable pada uji race: bulk vs bulk, bulk vs individual dan bulk vs staging, order lock, kegagalan parsial serta crash/recovery. Tidak menguji database pengguna. Pastikan test PostgreSQL **tidak skip** untuk klaim konkurensi; SQLite bukan pengganti.

## Batch 2 — 3 dan 4: Admin UI dan integrasi

### 3. Tombol, preview, konfirmasi, hasil
- Kandidat lokasi: `frontend/src/features/candidates/CandidateReview.tsx`, `candidate-review.css`, `frontend/src/api.ts`, serta tes kandidat terkait.
- Daftar per item mudah dinavigasi, tidak melewatkan halaman, menonjolkan bukti tidak tersedia dan peringatan revisi, menyediakan pembatalan dan konfirmasi eksplisit. Pastikan aksesibilitas keyboard/fokus, status loading/error dan tombol sesuai izin.
- Ikuti kontrak penanda ketidakpastian yang telah ada tanpa menghapus penanda kandidat lain; pastikan mekanisme batch tidak memperlemah proteksi individual. Jangan menggunakan localStorage sebagai penyimpanan token.

### 4. Verifikasi end-to-end dan review
- Jalankan tes API dan browser dengan fixture sintetis, backend sesungguhnya dan database disposable; uji request tertahan, respons hilang, sebagian selesai, reload, sesi kedaluwarsa, kesalahan readback dan pemulihan tanpa replay otomatis. Cocokkan jumlah UI dengan hasil server per ID.
- Uji output public dashboard, grafik, detail dan Source Trace setelah subset publikasi sintetis; pastikan data pending dan sumber lain tidak terekspos. Uji regresi individual, lint dan build berdasarkan perintah proyek aktual; cakupan dan hasil dicatat apa adanya.
- Lakukan review kode terarah atas otorisasi, CSRF, race, transaksi dan paparan data; evaluasi visual Admin secara terpisah. Jangan klaim tes sintetis membuktikan data resmi benar atau kesiapan Coolify.

## Kriteria selesai dan gerbang

- Semua skenario di atas punya bukti test dan hasil aktual; perbedaan unit, API, browser sintetis, FE–BE, PostgreSQL dan visual dilaporkan secara terpisah.
- Keputusan kebijakan metadata disetujui dan terdokumentasi; desain snapshot/recovery dan konsekuensi migrasi disetujui sebelum implementasi terkait.
- Jika memerlukan migrasi, uji upgrade menggunakan data sintetis pada PostgreSQL disposable; database produksi hanya dapat disentuh dengan target, backup/restore dan izin terpisah.
- Commit/push rencana tidak berarti implementasi diterima, PR dibuat, fitur dideploy atau kandidat produksi disetujui. Rilis dan operasi publikasi data memerlukan persetujuan terpisah.

## Evaluasi rencana — 17 November 2026

- **Kesesuaian:** cakupan semua halaman, hanya satu sumber, konfirmasi manusia dan hasil parsial menjawab permintaan; setiap keputusan masih melalui lifecycle individual.
- **Risiko utama:** persetujuan massal tetap bisa menerbitkan angka salah. Snapshot mencegah perubahan cakupan tersembunyi, tetapi tidak membuktikan manusia memeriksa setiap angka. Ketiadaan RAW/backup serta kemampuan menimpa observasi sebelumnya memerlukan keputusan dan mitigasi nyata.
- **Kelayakan:** endpoint tunggal existing menyediakan fingerprint dan pemeriksaan review, tetapi **tidak** menyediakan batch snapshot/job atau pemulihan durable. Rancangan operasi harus diuji sebelum klaim hasil dapat direkonsiliasi setelah crash; kebutuhan migrasi masih belum diputuskan.
- **Batas evaluasi:** inspeksi statis dan penyusunan rencana saja; belum ada implementasi, tes fitur massal, validasi PostgreSQL, pemeriksaan visual, data resmi, atau verifikasi deployment. Rencana belum otomatis mengubah persyaratan tim.
