# Keputusan, gap dan gate review

Tanggal: 4 November 2026 (UTC+07). Tidak ada keputusan produk baru yang disahkan oleh paket ini.

| Gate | Temuan / keputusan yang dibutuhkan | Dampak pada Batch 2 |
|---|---|---|
| Q01 | SRS lokal approved 7 Oktober 2026 berhasil dibaca pada bagian 1–2; ekstraksi pagination berikutnya gagal. Laporan Sprint1 memverifikasi delapan nama backlog, tetapi uraian stand-up di dalamnya adalah usulan. Cocokkan matriks dengan seluruh FR terperinci SRS final bersama PO/tim sebelum menyebutnya final. | Semua spesifikasi berstatus draft; bukan pengesahan cakupan FR lengkap. |
| Q02 | Alur filtered dashboard → detail → trace harus meneruskan konteks observasi yang sama; koordinasikan route/selector dengan pemilik integrasi FE. | BDD-X-03 menunggu keputusan/wiring hasil integrasi, bukan fallback ke latest. |
| Q03 | Kontrak kandidat menyatakan revisionId null dan immutableSnapshot false. Historical PRD meminta binding versi/revisi dan formula/input lengkap. ID observasi tidak memenuhi immutable revision. | BDD-F07-04 hanya menguji keterbatasan jujur. Full historical revision/formula acceptance masih gap dan tidak dapat ditutup dengan skenario tersebut. |
| Q04 | Feedback kandidat hanya menyimpan related_indicator_code dan related_period yang bersifat advisory, bukan foreign key versi analisis. | BDD-F08-08 tidak membuktikan binding revisi. Tim perlu memutuskan apakah advisory cukup untuk acceptance Sprint1; jangan menambah schema sendiri. |
| Q05 | Reset default disabled; dukungan kandidat hanya locmem pada test. SMTP dan privacy timing/delivery produksi belum diterima. | Skenario reset sukses memakai outbox locmem dalam proses uji, bukan inbox nyata. Hasilnya tidak membuktikan email produksi. |
| Q06 | Policy kandidat: Login staff aktif, expiry 8 jam, lima kegagalan/cooloff 15 menit; reset timeout 1800 detik; feedback 10–2000 karakter. Detail ini berasal dari kontrak implementasi, bukan angka normatif SRS/ISO. | Review sebelum dijadikan acceptance final. Gunakan jam terkontrol; jangan sleep delapan jam atau mengubah policy supaya tes lulus. |
| Q07 | Lane FE/BE aktif dan dirty. Branch/HEAD saja tidak mengidentifikasi overlay source yang berubah. Snapshot sumber bacaan terdapat di sources.json. | Minta checkpoint/handoff stabil dari kedua pemilik lane, termasuk source/test hashes dan konfigurasi API/proxy. Jangan menyisipkan file BDD ke worktree mereka. |
| Q08 | SRS menyebut FastAPI/PostgreSQL; implementasi kandidat React/Django dan tes SQLite. Paket mengikuti stack yang dipakai tim untuk rancangan tes, tidak mengesahkan perubahan arsitektur SRS. | Catat perbedaan dokumentasi dan cakupan engine database; SQLite PASS bukan PostgreSQL PASS. |
| Q09 | Alt teks/tabel, keyboard, responsive dan tanpa interpretasi buatan adalah target kualitas; approval visual/semantik terpisah. | Tidak menganggap screenshot/build atau pemeriksaan DOM sebagai approval manusia. |

## Konflik dokumen yang sudah direkonsiliasi
- `Spesifikasi_Use_Case_Sistem_DEKSI_Revisi_v2.docx` masih menyebut registrasi publik dan feedback wajib Login; bertentangan dengan SRS approved bagian 1.1/2.2 dan keputusan pengguna. Tidak digunakan sebagai otoritas kebutuhan aktif.
- Nomor backlog Sprint1 1–8 berbeda dari nomor System Feature/UC di SRS. Fitur 3–6 backlog berada dalam UC-02; backlog 7 dalam UC-04; backlog 8 dalam UC-05. Jangan membuat pemetaan nomor satu-banding-satu.
- Dokumen auth/reset lama menyebut frontend belum terhubung. Itu status saat dokumen ditulis, bukan bukti terbaru lane FE; jangan memundurkan hasil kerja lane lain berdasarkan kalimat historis.
- Scope dokumentasi lama personal fitur 6–7 diperluas oleh persetujuan chat terbaru untuk BDD seluruh delapan fitur Sprint1, bukan seluruh produk atau fitur Sprint2 9/10.

## Batas cakupan yang tidak boleh disamarkan
- Paket tidak membuat CRUD sumber, review feedback Admin, review analisis, konfigurasi operasional, engine baru, sinkronisasi provider, atau narasi AI. Kontrol publikasi hanya diuji sebagai prasyarat data yang boleh tampil.
- Input hostile dan checks jaringan adalah fixture lokal terkendali; tidak melakukan probing situs institusi atau URL pengguna.
- BDD-F03-04 memeriksa pemilihan data/log yang tersimpan setelah kegagalan sintetis, bukan menjalankan pengambilan data resmi.
- Skenario keamanan contoh tidak menggantikan suite security existing atau audit lengkap; expiry/replay/role/CSRF tetap harus dibuktikan eksekusi.
- Target viewport 390/1280 adalah pilihan pengujian, bukan ambang ISO atau fidelity High-Fi yang sudah disetujui.

## Handoff untuk pemilik integrasi
1. Berikan snapshot FE dan BE stabil beserta route halaman, transport/proxy, endpoint, selector elemen stabil dan fixture contract.
2. Pertahankan pemisahan publik dan Admin, review publikasi, exact decimal, missing-not-zero, serta CSRF. Tidak menurunkan proteksi untuk mengakomodasi Selenium.
3. Konfirmasi Q01–Q09 yang mempengaruhi acceptance; jawaban yang belum tersedia tetap OPEN.
4. Izin Batch1 tidak mengizinkan runner/steps, install, migrasi database kerja, commit/push/PR/merge atau provider.
