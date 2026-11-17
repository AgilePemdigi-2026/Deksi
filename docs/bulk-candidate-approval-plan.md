# Rencana implementasi: persetujuan massal kandidat sumber

**Status:** kebijakan metadata untuk bulk dipilih pengguna; desain teknis tetap usulan dan fitur belum diimplementasikan.

**Baseline:** `main` commit `8c9a07604e27b010da36eeedd13dced2d476436f` (17 November 2026).

**Tujuan:** reviewer berwenang dapat menyetujui seluruh kandidat pending **yang memenuhi syarat bulk** dari satu sumber yang dibuka, termasuk halaman lain, berdasarkan daftar kandidat yang dibekukan dan dikonfirmasi secara sadar. Kandidat tanpa RAW atau tanggal rilis dikecualikan secara terlihat dan tetap dapat direview individual; kandidat yang berubah atau gagal validasi dilewati dan dilaporkan satu per satu.

## Kondisi yang sudah diperiksa

- `backend/indicators/candidate_views.py`: list difilter per sumber/status dan dipaginasi 20; review HTTP menerima satu ID dan fingerprint, mensyaratkan staf serta izin reviewer, dan memakai transaksi dengan pemeriksaan source, status dan fingerprint.
- `backend/indicators/lifecycle.py`: `review_candidate` memvalidasi kandidat dan basis sebelumnya, menyimpan reviewer/waktu serta pencatatan publikasi. Setiap transaksi dapat memperbarui observasi yang sudah ada bila kandidat adalah revisi.
- `frontend/src/features/candidates/CandidateReview.tsx`: review individual memakai konfirmasi, penanda hasil tidak pasti, pembacaan ulang dan kontrol busy. Penanda sesi bukan lock server atau bukti server sudah berhenti.
- `backend/indicators/management/commands/publish_observations.py` menerima ID eksplisit tetapi membungkus seluruh daftar dalam satu transaksi: itu **bukan** implementasi massal parsial yang diminta.
- Screenshot pengguna menunjukkan 98 kandidat BPS pending pada saat screenshot, bukan jumlah terkini yang dijamin. Tidak ada klaim bahwa kandidat-kandidat itu sudah diverifikasi.
- Pengguna menyatakan backup database produksi tidak ada; target database, pemulihan, status aktual Coolify, dan keputusan apakah backup sudah tersedia saat rilis masih harus dikonfirmasi.

## Kontrak perilaku yang diusulkan

1. Satu sumber pada panel aktif; pratinjau mencakup seluruh halaman pending, bukan sumber lain, dan memisahkan item yang layak dari yang dikecualikan. Kumpulan kandidat harus dibekukan sebagai pasangan **ID dan fingerprint** pada pratinjau; hasil pencarian yang berubah saat konfirmasi tidak boleh menambahkan anggota baru diam-diam. Bila snapshot lengkap tidak dapat dibuat secara konsisten atau melebihi batas aman, hentikan dengan pesan jelas, bukan menyetujui subset secara tersembunyi. Rancangan mekanisme snapshot dan batas jumlah perlu dibuktikan.
2. Sebelum keputusan, tampilkan daftar per kandidat (indikator, nilai, satuan, periode, source snapshot, indikasi revisi serta ketersediaan RAW/tanggal rilis), total pending, total layak, total dikecualikan dan alasannya. Buat daftar dapat ditelusuri tanpa menganggap Admin sudah membaca setiap item. Munculkan peringatan bahwa konfirmasi mempublikasikan data layak, perubahan observasi mungkin terjadi, dan konfirmasi bukan verifikasi otomatis. Batalkan tanpa efek.
3. Backend memeriksa otorisasi ulang dan CSRF serta source binding, kelayakan metadata, status, fingerprint, validasi, stale-base, urutan lock dan audit pada setiap kandidat yang layak melalui lifecycle yang ada. Setiap kandidat layak memiliki transaksi independen: kandidat konflik, tidak cocok, sudah diproses atau tidak valid dilewati dan dicatat; kandidat layak lain tetap dapat diproses. Tidak ada bulk SQL langsung melewati lifecycle.
4. Hasil diklasifikasi per ID sebagai berhasil, dilewati/gagal dengan alasan aman, atau belum pasti/belum diketahui. Bedakan tidak dimulai, sedang berjalan, selesai dan hasil tidak pasti; hasil belum pasti tidak boleh dianggap gagal atau aman untuk diulang. Tampilkan total yang konsisten dengan detail.
5. Kandidat baru setelah snapshot, sumber lain dan kandidat yang sudah diproses tidak ikut dipublikasikan. Review individual tetap berfungsi. Tidak membuat angka, waktu rilis, RAW, status verifikasi atau sumber.
6. Selama aksi dan pembacaan hasil, cegah navigasi aplikasi terkait serta duplikasi submit; browser Back, reload dan tutup tab tidak dijanjikan tertahan. Jangan otomatis mengulang mutasi setelah timeout/terputus. Baca kembali hasil operasi dan kandidat yang tepat; `pending` pada satu waktu bukan bukti server sudah selesai. Bila hasil tidak dapat dipastikan, blokir pengulangan sampai ada prosedur pemeriksaan dan keputusan manusia.

## Keputusan produk dan gerbang yang tersisa

- **RAW atau tanggal rilis tidak tersedia — diputuskan 17 November 2026:** pengguna memilih opsi B: **kecualikan dari aksi massal**, tampilkan ID dan alasan, sediakan review individual. Cakupan aksi harus disebut "semua kandidat yang memenuhi syarat", bukan "semua pending" bila ada pengecualian. Tidak mengarang metadata; link portal bukan bukti verifikasi. Keputusan ini bukan persetujuan atas rancangan teknis atau izin mempublikasikan data.
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

## Urutan 1 — kontrak keselamatan sebelum implementasi (kebijakan metadata diputuskan; rancangan teknis masih usulan)

Bagian ini merinci enam prioritas pertama. Ini **bukan** implementasi atau keputusan untuk mempublikasikan kandidat. Jangan memulai migrasi/job atau mengaktifkan tombol sampai rancangan perubahan skema disetujui dan kebijakan metadata benar-benar ditegakkan di server. `docs/PRD.md` dan `docs/DECISIONS.md` dari paket dokumentasi baseline tidak ada dalam checkout aplikasi ini; periksa lagi keputusan tim sebelum implementasi.

### 1. Bukti dan metadata yang hilang — opsi B dipilih pengguna pada 17 November 2026

- **Kebijakan:** kandidat tanpa RAW atau tanggal rilis tidak dapat disetujui lewat batch; tampilkan ID, alasan pengecualian, dan jalur review individual. Jangan mengurangi total cakupan secara tersembunyi: bedakan total pending sumber, jumlah layak, dan jumlah dikecualikan. Label aksi: **"Setujui semua kandidat yang memenuhi syarat"**, bukan "semua pending" bila ada pengecualian. Bila jumlah layak nol, aksi tidak dapat dilanjutkan dan Admin melihat alasannya.
- Aturan berlaku sama bagi kandidat baru dan revisi. Pemeriksaan server menggunakan keberadaan `raw_file_id`, catatan RAW yang benar-benar ada dan terikat ke sumber (`candidate_raw` bukan sekadar ID), serta `publication_date` yang tersedia. `publication_date` adalah tanggal dalam model, jangan menyebutnya timestamp rilis yang lebih presisi. Metadata RAW/checksum yang kosong tetap ditandai sebagai bukti tidak lengkap, bukan diisi rekaan; perincian syarat metadata RAW tambahan harus selaras dengan kontrak data tim sebelum implementasi. Validasi ulang kelayakan saat commit per item; yang berubah menjadi tidak layak dilewati dan dilaporkan.

### 2. Snapshot cakupan konsisten dan kedaluwarsa

- **Proposal server-side:** satu query terbatas untuk semua kandidat `pending` pada satu `source_id`, diurutkan deterministik berdasarkan ID, dievaluasi dalam satu pembacaan database yang konsisten; jangan merangkai halaman dari endpoint `page=...` yang bisa bergeser. Jika hitungan melebihi batas terukur, gagal seluruh preview (bukan mengambil potongan pertama). Simpan pasangan ID/fingerprint, source, identitas reviewer, waktu pembuatan/kedaluwarsa, serta informasi preview yang ditampilkan sebagai snapshot immutable. Kandidat baru setelah query tidak ikut; kandidat berubah setelah query harus berakhir konflik, bukan diganti nilai terbaru secara diam-diam.
- Konfirmasi menyebut identitas snapshot server dan identitas operasi yang stabil; backend memvalidasi reviewer, sumber, izin, kedaluwarsa, dan himpunan item sebelum memulai. Jangan menerima daftar ID, hitungan, atau fingerprint baru dari browser sebagai cakupan otoritatif. Preview kosong dan snapshot kedaluwarsa tidak mempublikasikan apa pun. Uji snapshot saat staging dan review berlangsung bersamaan pada PostgreSQL disposable.
- Snapshot yang telah dikonfirmasi tidak boleh berubah; kalau ingin mencakup kandidat baru, Admin membuat preview baru dan mengonfirmasi ulang. Waktu berlaku, batas jumlah, penyimpanan/penghapusan, dan migrasi diputuskan bersama desain implementasi; bukan menganggap 98 item sebagai batas permanen.

### 3. Publikasi dan hasil per item harus atomik

- **Proposal penyimpanan durable:** entitas operasi dengan item snapshot terpisah dan kunci unik `(operation, candidate)`. Dalam **transaksi yang sama per item**, kunci dan periksa ulang kandidat + source, fingerprint, status, basis observasi dan izin; panggil lifecycle review existing, lalu tulis hasil item sukses dan tautan audit/publikasi. Jangan menandai sukses sebelum commit. Jika validasi/konflik, tulis hasil skip yang spesifik setelah kegagalan transaksi review di-rollback; jangan menangkap error database di dalam transaksi yang rusak.
- `record_update_success` existing dipanggil dalam transaksi review kandidat. Hasil item baru harus terikat pada commit publikasi yang sama; pesan log existing saja tidak cukup untuk merekonstruksi hasil batch per ID. Kegagalan sistemik menghentikan pemrosesan dan meninggalkan sisa item sebagai belum diproses/tidak pasti; jangan memberi label semua sisa sebagai gagal. Jangan membungkus seluruh batch dalam satu transaksi seperti CLI existing.
- Hasil yang dibaca ulang menampilkan status per ID, alasan aman, dan total yang dihitung dari item persisted (bukan angka browser). `sukses`, `dilewati`, `belum dimulai`, `diproses`, dan `belum pasti` dibedakan. Periksa hubungan commit hasil item dengan observasi dan audit menggunakan fault injection sebelum/sesudah commit.

### 4. Proses terputus, retry, dan rekonsiliasi

- Simpan identitas operasi saat konfirmasi, sebelum mutasi pertama. Pengiriman POST duplikat dengan identitas yang sama harus membaca operasi yang sudah ada, bukan memulai batch kedua. `GET` status tidak boleh diam-diam memulai ulang pekerjaan. Respons HTTP timeout/terputus bukan bukti server sudah berhenti atau tidak mempublikasikan apa pun.
- Jika proses berhenti, hasil item yang **sudah commit** tetap dapat dibaca; item yang belum commit tidak dianggap sukses. Item `diproses` yang tertinggal harus direkonsiliasi dari state database/audit setelah ada bukti worker lama benar-benar berhenti. Lease/heartbeat, penguncian pengeksekusi, status `terputus`, dan mekanisme lanjut eksplisit masih memerlukan desain serta uji crash/restart; tidak boleh mengandalkan `sessionStorage` atau status `pending` sesaat sebagai bukti aman untuk replay.
- Jangan menyediakan tombol "coba lagi" otomatis untuk item belum pasti. Lanjutkan hanya melalui operasi/prosedur eksplisit yang memeriksa ulang hasil dan mendapat keputusan manusia; jika tidak dapat dibuktikan aman, hentikan dan eskalasi pemeriksaan manual. Catat item mana yang tidak pernah dimulai terpisah dari yang statusnya belum dapat dipastikan.

### 5. Revisi dan keterlacakan keputusan manusia

- Preview menandai kandidat yang mengubah observasi publik existing; tampilkan nilai/periode/satuan lama dan baru serta identitas kandidat dan fingerprint. Perubahan observasi existing diuji ulang terhadap `base_snapshot` di transaksi item; konflik dilewati dan tidak menimpa perubahan Admin lain.
- Konfirmasi Admin tidak sama dengan verifikasi sumber resmi. Catat identitas reviewer, waktu server, cakupan dan pernyataan keputusan yang sebenarnya; jangan menulis catatan generik "semua sudah diverifikasi". Bukti manual per kandidat yang RAW/tanggal rilisnya hilang tidak menjadikannya layak untuk bulk di bawah kebijakan opsi B; kandidat itu tetap melalui review individual. Struktur audit perlu ditentukan bersama aturan retensi dan privasi.

### 6. Gate penerimaan untuk urutan 1

- Kebijakan metadata opsi B telah dipilih pengguna. Makna "semua" adalah semua kandidat **layak** pada snapshot, dengan total pending dan daftar yang dikecualikan terlihat; review individual tetap tersedia untuk kandidat yang tidak layak batch. Syarat metadata RAW tambahan dan rancangan teknis masih perlu diselaraskan dengan kontrak tim; keputusan pengguna ini tidak membuktikan nilai kandidat benar.
- Desain snapshot + operasi durable + hasil atomik direview terhadap model/migrasi aktual; contoh 0, 1, lebih dari 20 kandidat, perubahan saat preview, dua reviewer, revisi, timeout dan crash diuji dengan fixture sintetis; race diuji pada PostgreSQL disposable dan tidak di-skip. Uji juga izin, CSRF, hasil per ID dan readback setelah restart. Ini kriteria untuk implementasi nanti, **belum hasil tes**.
- Sebelum fitur dipakai untuk publikasi nyata: backup database konsisten, uji restore terpisah dan izin deployment/publikasi tersendiri. Sampai terpenuhi, jangan menyebutnya siap produksi.

## Urutan 2 — keamanan dan konsistensi (usulan untuk implementasi berikutnya)

Bagian ini merinci poin 7–13 dari audit. Pemeriksaan terhadap `candidate_views.py`, `lifecycle.py`, `resync_model.py`, `resync_views.py` dan `CandidateReview.tsx` bersifat statis. Review individual punya lock, fingerprint, izin reviewer dan audit; **belum ada endpoint atau tes batch**. Fitur resync memiliki pola request key/status durable, tetapi job resync bukan job persetujuan dan tidak boleh dipakai untuk mempublikasikan kandidat.

### 7. Dua reviewer/tab dan sinkronisasi bersamaan

- Semua pengeksekusi batch harus memakai kontrak lock review individual: kandidat dahulu, lalu indikator dan sumber dalam urutan yang sama dengan staging; validasi ulang source binding, fingerprint, status dan basis tepat sebelum publikasi. Publikasi serta hasil item commit bersama (lihat urutan 1). Dua operasi berbeda pada kandidat sama: paling banyak satu sukses, lainnya konflik/skip. Jangan mengunci seluruh batch selama seluruh proses.
- Uji PostgreSQL disposable dengan dua koneksi tersinkronisasi untuk batch–batch, batch–review individual dan batch–staging pada kandidat baru maupun revisi; assert status kandidat, nilai observasi, satu audit publikasi dan satu hasil sukses. Tes individual existing `test_candidate_review_postgres.py` tidak membuktikan race batch yang belum dibuat.

### 8. Izin dicabut atau sesi berakhir saat batch berlangsung

- Endpoint preview, konfirmasi dan readback harus memeriksa sesi/staf serta izin reviewer di server. Ulangi pemeriksaan izin **sebelum setiap item** dengan fungsi `require_reviewer`; bila ditarik, hentikan sebelum item berikutnya, simpan hasil yang sudah commit, lalu tampilkan sisa belum diproses. Tentukan siapa boleh membaca hasil historis setelah izin dicabut: paling aman, hanya reviewer berizin saat readback; Admin lain dengan izin yang sama memerlukan kontrak akses terpisah, bukan otomatis mewarisi hasil.
- Pencabutan izin yang terjadi sesudah pemeriksaan item tetapi saat transaksi berlangsung adalah race tersendiri; jangan janjikan penghentian instan. Uji pencabutan sebelum item pertama dan di antara dua item, tanpa memalsukan kegagalan pada item sukses.

### 9. Binding dan perlindungan request

- Snapshot immutable mengikat `source_id` internal + kode rute sumber, reviewer ID, daftar ID/fingerprint, kelayakan, dan kedaluwarsa. Konfirmasi hanya menerima identitas snapshot dan kunci request terikat ke reviewer/sumber; jangan menerima daftar atau nilai baru dari browser. Tolak perubahan akun, sumber, preview kedaluwarsa, snapshot asing dan payload yang dimodifikasi. Jika kunci request dipakai ulang dengan snapshot/akun lain, kembalikan konflik, bukan status operasi lain.
- Gunakan proteksi CSRF Django untuk semua POST berbasis sesi; tidak mengubah CORS global atau menaruh token autentikasi di `localStorage`. GET status harus read-only dan `Cache-Control: no-store`; error tidak membocorkan payload internal atau sumber lain. Uji dengan client Django yang benar-benar menegakkan CSRF serta kasus 401/403, bukan hanya `force_login` default.

### 10. Penanda browser bukan lock lintas perangkat

- Penanda `sessionStorage` individual hanya per sesi tab; jangan menggantikannya dengan daftar batch lalu mengklaim lock global. Setelah reload/tab baru, UI membaca operasi aktif/terakhir yang **diotorisasi** dari server sebelum menawarkan konfirmasi baru pada sumber itu. Penanda individual yang belum pasti tetap dipertahankan; jangan hapus untuk menampilkan batch seolah-olah aman.
- UI boleh mencegah klik ganda/navigasi aplikasi selama submit, tetapi keamanan terhadap dua tab, dua Admin atau browser tertutup ada di operasi dan transaksi server. Uji reload/tab terpisah, penyimpanan browser gagal, dan konflik individual vs batch tanpa mengandalkan state React saja.

### 11. Timeout, duplikasi dan readback

- Buat identitas request durable sebelum mutasi pertama; POST duplikat untuk identitas dan snapshot sama membaca hasil yang sama serta tidak menjalankan item dua kali. Timeout klien, hasil GET sesaat `pending`, atau lease kedaluwarsa **tidak** membuktikan worker lama berhenti; readback status dan item yang sudah commit terlebih dahulu, lalu tahan retry bila ada item belum pasti.
- GET status tidak menjalankan pekerjaan dan tidak otomatis mengubah unknown menjadi gagal. Sebelum langkah lanjut manual, buktikan pekerja lama tidak aktif dan rekonsiliasi hasil per ID; uji respons POST hilang sebelum operasi tersimpan, setelah tersimpan/sebelum publikasi, sebelum commit item, sesudah commit item, dan setelah semua selesai. Jangan meminjam status resync sebagai bukti hasil kandidat.

### 12. Kegagalan per kandidat vs kegagalan sistem

- Kontrak hasil: metadata tidak layak = dikecualikan sebelum submit; perubahan status/fingerprint/basis, validasi data, atau constraint konflik pada satu kandidat = skip beralasan aman dan lanjut; permission dicabut, database/koneksi rusak, deadlock berulang atau crash = berhenti dan tandai sisa belum diproses/belum pasti sesuai bukti. Tangkap exception per item **di luar** transaksi yang gagal; jangan menyembunyikan error sistem sebagai 98 kali skip.
- Setiap hasil item punya ID, fingerprint snapshot, status final yang jelas, alasan aman, dan kaitan audit bila sukses. Jumlah berhasil + skip + belum dimulai + belum pasti harus konsisten dengan jumlah item layak; item tidak layak dihitung terpisah. Uji kegagalan di tengah daftar dan kembalikan hasil dari penyimpanan server, bukan kalkulasi frontend.

### 13. Reuse lifecycle, bukan CLI massal existing

- `publish_observations.py` saat ini membungkus seluruh ID dalam satu `@transaction.atomic`; kegagalan satu ID dapat membatalkan semuanya. Jangan memanggilnya dari endpoint batch atau menyalin transaksinya. Panggil `review_candidate` untuk item yang telah diverifikasi melalui jalur server batch dengan transaksi **per item**, pertahankan pemeriksaan fingerprint/source binding sebelum panggilan dan aturan review existing di dalamnya.
- Kriteria penerimaan: hasil parsial yang benar, audit satu per publikasi, tidak ada jalur bulk SQL yang melewati izin/review, dan tidak ada perubahan perilaku CLI individual existing tanpa keputusan terpisah. Detail operasi durable dan kebutuhan model/migrasi tetap perlu review desain tersendiri sebelum coding.
