# Acceptance backend fitur 7

**Status historis Batch 1: semua skenario di bawah NOT RUN.** Matriks ini disusun dari `be` commit `03052e3911966895456fd338300621c159ae30e4`. [Kontrak](README.md), [struktur kontrak](contract.json), [penilaian versi](VERSIONING.md).

**Pembaruan Batch 2–3:** 43 tes Python telah dieksekusi dan lulus pada PostgreSQL test, termasuk HTTP loopback nyata. [IMPLEMENTATION.md](IMPLEMENTATION.md) menjelaskan scope nyata dan keterbatasannya. Ini tidak otomatis mengesahkan setiap requirement produk: F7-BE-14 integrasi Laravel, data resmi, human acceptance dan perlindungan direct SQL tetap belum terbukti. Stop condition/gate Batch 1 di bawah adalah riwayat, bukan larangan terhadap Batch 2–3 yang kemudian diizinkan.

## Matriks requirement turunan

| ID | Requirement produk | Skenario dan hasil yang kelak wajib diuji | Lapisan |
|---|---|---|---|
| F7-BE-01 | F7-01, Q-04 | Anonymous GET 200 untuk revisi publik; tanpa token/session; token malformed tetap dapat membaca endpoint publik; endpoint Admin tetap menuntut autentikasi | API/security |
| F7-BE-02 | F7-01, F6-07 | Code/point/revision berbeda, UUID malformed, unknown dan draft menghasilkan generic 404 sama tanpa bocor identitas atau fallback indikator | API/security |
| F7-BE-03 | F7-02, F7-06 | Missing value, metadata kosong dan decimal zero dipertahankan; output decimal string empat digit, bukan float; tanggal date-only dan fetched_at/published_at tidak tertukar; timezone ambigu tidak ditebak | Serializer/API |
| F7-BE-04 | F7-03 | Official calculation null; derived menyajikan ekspresi/inputs yang terekam; formula ID/version dan input hilang ditandai; JSON legacy malformed tidak disalurkan mentah, formula tidak dieksekusi | Serializer/API |
| F7-BE-05 | F7-04, F6-07 | Edit master/working point/trace tidak mengubah pinned A; source_version kosong tetap null; revision UUID internal tidak menjadi versi resmi; current hanya memilih published dengan sequence deterministik | Storage/API |
| F7-BE-06 | F7-04, Q-04 | Buat B draft/pending/rejected atau simulasi fetch gagal: A tetap terbaca dan current=A; B tidak terlihat walau user login sebagai Admin di route publik; approval A tidak memberi publikasi otomatis B | Storage/API/publication |
| F7-BE-07 | F7-04 | History berisi hanya revisi publik point sama, descending sequence, parent nonpublik tidak bocor, pagination 20 dan invalid/out-of-range page mengikuti kontrak | API/storage |
| F7-BE-08 | F7-05, Q-04 | javascript/data/credentialed/control-char/backslash URL ditolak sebagai link; HTTP(S) valid dipertahankan; teks berbahaya tetap data; tidak ada outbound request/provider; internal notes, RAW, token dan reviewer tidak keluar; record RAW dengan status published legacy tetap tidak publik | Serializer/API/security |
| F7-BE-09 | F7-06 | Partial metadata 200 disertai missing fields; tidak ditemukan 404; snapshot invalid/DB error 503 tersanitasi, tidak berubah menjadi demo; completeness flag true tidak membuat verification official | API/error |
| F7-BE-10 | F7-01, Q-04 | GET/HEAD/OPTIONS tidak menulis row atau status; POST/PUT/PATCH/DELETE 405 tanpa mutasi; HEAD body kosong; OPTIONS dan exception tidak membuka field internal | API/security |
| F7-BE-11 | F7-04 | Snapshot tak dapat diedit/dihapus lewat jalur yang dijanjikan; PROTECT parent dan same-trace parent; review/publish hanya lewat policy berwenang; batas direct SQL dilaporkan, bukan diklaim otomatis | Storage/Admin |
| F7-BE-12 | F7-04 | Dua penulisan bersamaan tidak menghasilkan sequence ganda/lost revision; parent/order invalid ditolak; orphan/mixed point refs ditolak; nullable period ambiguity tidak dipilih sembarang | PostgreSQL/concurrency |
| F7-BE-13 | Q-04, Q-05 | Throttle tetap aktif dan 429/Retry-After benar; no-store pada respons yang direncanakan; akun Admin/regresi endpoint accounts tidak ikut dibuka oleh AllowAny lokal | API/regression |
| F7-BE-14 | F7-01, F6-07 | Laravel kelak menautkan tepat revision/point/value yang sedang dilihat; versi tidak cocok mematikan link secara jujur; kegagalan API bukan fallback demo tersembunyi | Integrasi FE–BE (di luar Batch 1) |

## Bukti yang diperlukan sebelum menyebut backend siap

1. Verifikasi root/branch/manifest/interpreter dan konfigurasi test yang **tidak** menuju DB produksi. Ambil perintah dari checkout/runtime aktual; paket ini tidak mengarang command install/test. Tentukan izin dependency, environment lokal dan database test sebelum menjalankan.
2. Setelah skema disetujui, buat test terarah RED pada perilaku belum tersedia; implementasi minimal; GREEN serializer/API/storage. Gunakan fixture synthetic berlabel, bukan menyebut data contoh sebagai rilis resmi. Mock outbound untuk membuktikan tidak ada request; DB dan HTTP acceptance tetap punya bukti eksekusi tersendiri.
3. Migrasi/additive schema diuji pada test PostgreSQL, termasuk rollback yang relevan dan efek PROTECT, nullable constraints serta transaksi. SQLite/mocked ORM tidak cukup untuk concurrency/PostgreSQL semantics.
4. Jalankan regresi backend tim yang relevan, catat command, exit code, count dan scope; suite frontend terdahulu tidak dianggap backend pass.
5. Lakukan satu real-path HTTP terhadap aplikasi + database test aktual, anonymous dan kasus penolakan/partial. Pengujian helper serializer saja bukan bukti routing/permission runtime.
6. Pisahkan penerimaan visual, integrasi Laravel, validitas angka ekonomi, review publikasi manusia, audit SQL/Admin dan CI. Tidak satu pun disahkan hanya karena dokumen lolos validator.

## Stop condition Batch 1

Batch ini selesai sebagai **paket rancangan** setelah JSON dapat diparse, mapping field cocok dengan AST model baseline, requirement turunan seluruhnya terpetakan, link lokal valid, scope perubahan hanya file dokumen baru, dan backend/frontend existing tidak berubah. Receipt validasi tersimpan lokal di `.hermes/receipts/feature7-backend-batch1.json` pada worktree backend. Receipt bukan sertifikat acceptance API atau persetujuan D1.

Gate berikut: review kontrak dan keputusan D1 pada VERSIONING; kemudian izin implementasi skema/API dan prasyarat database test. Commit/push/PR/merge tetap membutuhkan izin terpisah.
