# Audit dan penutupan Batch 1

## Putusan

Kandidat lokal cukup untuk menjadi basis pengerjaan frontend Batch 2 pada kontrak API publik yang didokumentasikan. Ini **bukan** kelulusan produksi, seluruh Sprint 1, integrasi browser, data resmi atau audit keamanan seluruh repository. Tidak ada commit, push, PR atau merge branch tim.

Worktree: `E:/Deksi-Team/.hermes/worktrees/sprint-1-dashboard-be`; branch `integration/sprint-1-dashboard-be`; HEAD dasar tetap `5c9e20de5d71d74d2c9aabcf00dbf85d04ee8fe3`. Perubahan implementasi masih uncommitted. Rincian sumber/hash, perintah, jumlah tes dan batas bukti tersimpan di [VERIFICATION.json](VERIFICATION.json).

## Temuan yang diperbaiki

| ID | Bukti masalah sebelum perbaikan | Perbaikan minimum dan penerimaan |
|---|---|---|
| B1-01 | Graph mempunyai dua leaf: feedback `0004_feedback_model` dan provenance `0005_observation_candidate`. Tes graph RED. | Tambahkan merge migration `0006_merge_dashboard_feedback` tanpa mengubah migrasi historis. Graph tunggal dan upgrade dari kedua sisi mempertahankan record sintetis; jalur exact decimal mempertahankan seluruh digit yang diuji. |
| B1-02 | Filter tahun mengembalikan nilai `888` dari observasi tanpa review, unit/metadata dari observasi terbaru, bukan konteks terpilih. Tes HTTP-view/Django client RED. | Pilih observasi tahun itu lewat queryset publik yang sama dan gunakan ulang serializer ringkasan. Sumber, satuan, tanggal, delta, pembanding dan sparkline mengikuti satu konteks; tidak fallback tahun lain, tidak memakai nilai masa depan untuk sparkline. |
| B1-03 | Tahun 0, 10000, digit sangat panjang dan superscript dapat menghasilkan 500; filter berulang diambil diam-diam. | Batasi digit ASCII 1–9999 sebelum konversi/query; tolak parameter tidak didukung/berulang dengan 400. Batas sah dan unavailable tetap diuji. |
| B1-04 | Tipe field feedback bukan teks menghasilkan 500; input panjang dipotong diam-diam, JSON duplikat/oversize dapat tersimpan. | JSON UTF-8 dibatasi 32 KiB; key duplikat/nonfinite ditolak; validasi tipe/ukuran dan email native Django. Body oversize 413; field invalid 400 tanpa row baru; nilai opsional tidak dipotong. |
| B1-05 | Endpoint feedback publik memakai `csrf_exempt`; client dengan pemeriksaan CSRF tetap bisa menulis tanpa token. | Hilangkan exemption, pertahankan middleware dan bootstrap cookie/token melalui kategori feedback. Tes HTTP nyata membuktikan 403 tanpa token dan 201 dengan cookie/token yang benar, tanpa login. Frontend lama tanpa token perlu adapter Batch 2, bukan pelonggaran keamanan. |
| B1-06 | Staff dengan izin lihat feedback masih mendapat aksi perubahan status. | Kedua aksi Admin diberi `permissions=["change"]`; tes membuktikan akun view-only tidak mendapat aksi mutasi. Ini bukan bukti login/password atau seluruh workflow Admin. |
| B1-07 | `X-Forwarded-For` dapat mengganti IP tersimpan tanpa kebijakan trusted proxy. | Rekam peer `REMOTE_ADDR` yang valid; jangan percaya header proxy secara otomatis. Konfigurasi proxy produksi tetap terpisah. |
| B1-08 | Escaped unpaired surrogate lolos JSON lalu memicu 500 ketika disimpan. Tes RED; kontrol Unicode valid tetap 201. | Validasi encoding field yang akan disimpan. Input invalid kini 400; deskripsi Unicode valid pada batas 2000 karakter tetap diterima. |
| B1-09 | Konteks indikator berisi newline masuk ke log penerimaan sebagai baris palsu. Tes log RED. | Log hanya ID record dan enum kategori; konteks tetap disimpan sebagai data, tidak ditulis ke log. Tes regresi memastikan marker pengguna tidak muncul dalam log. |

Perubahan lain hanya integrasi backend fitur 5/8 milik tim, registrasi route/model/Admin, dokumentasi dan perapian lint pada kode kandidat. Tidak membangun framework, schema immutable baru, engine ekonomi baru, rate limiter, AI atau sumber data Sprint 2.

## Verifikasi akhir yang dieksekusi

- Suite `manage.py test indicators.tests --settings=backend.test_settings_indicators --noinput -v 2`: **97 tes unik; 96 PASS, 1 SKIP**, exit 0.
- Di dalam total tersebut terdapat **24 tes dashboard baru**, termasuk satu alur HTTP loopback nyata, dua tes upgrade migrasi dan satu tes graph. Jangan menjumlahkannya lagi sebagai tes tambahan di luar 97.
- SKIP: `RawDownloadTests.test_symlink_is_not_followed`, karena hak membuat symlink tidak tersedia pada proses Windows ini. Tidak mengklaim kontrol itu lulus runtime.
- HTTP nyata: ringkasan terbaru → filter tahun historis → histori exact → Source Trace konteks terpilih → metadata pembaruan → feedback ditolak tanpa CSRF → bootstrap → feedback tersimpan pending dengan CSRF. Menggunakan Django LiveServer dan urllib/cookie jar, bukan mock respons API; bukan browser React.
- Regresi inherited mencakup presisi, seri tidak sebanding, review/publication fallback, ingestion dengan provider sintetis, RAW, Source Trace, Admin numeric ordering dan transaksi kandidat. Bukan ingestion data resmi.
- Django system check: 0 isu. `makemigrations --check --dry-run`: tidak ada drift model/migrasi. `pip check`: tidak ada dependency rusak.
- Ruff check lulus pada 12 file Python kandidat yang diubah/ditulis; format check lulus pada 8 file baru/diadaptasi. Migrasi feedback historis yang disalin tetap sesuai Git blob upstream, tidak diformat ulang. Bukan klaim seluruh repository bebas lint.
- `git diff --check` lulus. Hash 13 file Python perubahan cocok sebelum dan sesudah verifikasi akhir.
- HEAD/status enam worktree terlindungi cocok snapshot awal; seluruh local branch ref existing tetap sama. Satu-satunya ref baru adalah branch kandidat integrasi. Prototype 2 masih cocok dengan hash baseline pilihan.

## Batas dan pekerjaan yang memang belum dilakukan

1. Frontend/Prototype 2 tidak dimodifikasi; filter grafik/rentang, adapter CSRF, penerusan konteks serta visual acceptance adalah Batch 2. Histori native tetap membutuhkan guard sumber/unit/frekuensi/jenis data di frontend.
2. Tidak menjalankan aplikasi normal, membuka `.env`, memigrasikan database pengguna, mengambil data provider, mengirim email, memasang paket atau mengubah model/provider agent. DB pengujian memakai in-memory SQLite dan fixture RAW di scratch yang dibersihkan oleh suite.
3. PostgreSQL, beban produksi, rate-limit/anti-spam, reverse proxy/CORS credential lintas origin dan integrasi seluruh auth/backend belum diverifikasi. Native HTTP test menggunakan same-origin dan bukan bukti CORS/SameSite di browser.
4. Metadata pembaruan dan kontrak publik lain yang diwarisi bukan audit menyeluruh semua field/route/operasional. Angka resmi, review konten di database kerja, immutable revision dan formula/input berversi tidak dibuktikan oleh status published atau checksum.
5. Audit ulang ini merupakan self-review terarah plus eksekusi tes. Tidak mengklaim kelulusan review independen dari delegasi yang hasil akhirnya tidak tersedia setelah interupsi.

## Catatan tooling/harness

Bukti RED disimpan, bukan ditimpa: graph, konteks filter, input filter, batas feedback, Unicode dan log. Percobaan awal `filter-context-green.log` berakhir error karena variabel `HERMES_TEST_SCRATCH` tidak tersedia pada invokasi berikutnya; itu bukan PASS dan bukan alasan mengubah kode domain. Invokasi akhir memasang environment eksplisit dan lulus. Timeout tool saat menulis bukti/patch diikuti pemeriksaan efek yang tersimpan sebelum melanjutkan; hasil final tidak bergantung pada klaim sukses dari invokasi yang terputus.

Detail kontrak dan kompatibilitas: [README.md](README.md). Gate berikutnya adalah port full dashboard React dengan kontrak ini, bukan publikasi/merge otomatis.

## Follow-up verifier kanonik

Setelah pengingat workspace unverified, seluruh hash 13 file Python dan hash log akhir dibandingkan dengan receipt: masih cocok. Bukti direct suite tetap 97 tes, 96 PASS dan 1 SKIP; tidak ada perubahan kode setelah run tersebut.

`hermes verify --detect-only --json` dari folder backend mendeteksi recipe Django generik: bootstrap `pip install -r requirements.txt`, test `python manage.py test`, start `python manage.py runserver 0.0.0.0:8000`. Recipe itu tidak mengunci interpreter proyek atau settings terisolasi.

Percobaan satu kali `hermes verify --phase test --skip-start --timeout 180 --json`, dengan environment child diarahkan ke venv existing dan `backend.test_settings_indicators`, **gagal sebelum koleksi tes**: proses verifier tidak menemukan Django (`ModuleNotFoundError: No module named 'django'`). Probe native shell sebelum pemanggilan memastikan Python venv proyek dan modul Django tersedia. Ini blocker environment/resolusi interpreter pada verifier, bukan kegagalan assertion suite domain. Hasil aktual dan probe tersimpan di `backend/.artifacts/dashboard-foundation/canonical-test.json` relatif root worktree.

Status pada percobaan awal tersebut belum lulus. Bootstrap/instalasi dan start all-interface tidak dijalankan; build recipe kosong bukan bukti build. Saat itu manifest `.hermes/environment.json`, ledger verifikasi, profil, interpreter global dan dependency tidak diubah untuk membuat status terlihat lulus. Recipe lokal masih membutuhkan persetujuan; penyelesaian setelah persetujuan dicatat di bawah, tanpa menghapus bukti kegagalan awal.

## Penyelesaian verifier setelah izin recipe lokal

Pengguna kemudian mengizinkan penambahan recipe khusus worktree dan verifikasi terisolasi. Ditambahkan `.hermes/environment.json` pada root kandidat, bukan profil Hermes. Semua command menunjuk interpreter proyek secara eksplisit dan mengisolasi proses Python; tidak mengandalkan resolusi `python` generik dari launcher Hermes.

`hermes verify --json --timeout 180 --ready-timeout 25` dari root kandidat berhasil: `source=manifest`, `ok=true`, exit 0. Seluruh command bootstrap/build/test berakhir 0; startup/readiness menjawab HTTP 200 pada `http://127.0.0.1:55945/api/indicators/`.

- Bootstrap hanya memeriksa interpreter, port loopback dan dependency existing; tidak menjalankan instalasi.
- Fase build menjalankan Ruff terarah, Django check dan pemeriksaan drift migrasi. Tidak mengklaim build frontend.
- Tes kanonik menjalankan suite yang sama: 97 tes, 96 PASS, 1 SKIP. Pengujian lain tidak dijumlahkan ulang sebagai kasus tambahan.
- Startup menjalankan aplikasi WSGI Django asli dalam satu proses/satu thread, settings terisolasi dan SQLite dalam memori. Migrasi hanya pada DB dalam memori tersebut; endpoint readiness mengakses schema nyata dengan data awal kosong, bukan respons sukses buatan atau data resmi.
- Server mempunyai timer penghentian 20 detik setelah listening untuk menutup celah teardown child shell Windows. Marker penghentian terekam; PID 320 sudah tidak ada dan port 55945 sudah tertutup setelah command selesai.
- Hash 13 file Python implementasi masih sesuai receipt sebelumnya. Tidak ada perubahan kode fitur untuk mengatasi masalah interpreter.

Hasil mentah lengkap disimpan pada `backend/.artifacts/dashboard-foundation/canonical-full-raw.json`; ringkasan penutupan pada `backend/.artifacts/dashboard-foundation/canonical-full-receipt.json` (relatif root worktree). Kegagalan `canonical-test.json` sebelumnya tetap dipertahankan sebagai bukti historis.

Kelulusan ini berlaku pada recipe backend Batch 1, bukan frontend/browser, integrasi seluruh autentikasi, data resmi, PostgreSQL atau produksi. Tidak ada perubahan profil/global dependency, commit, push, PR atau merge branch tim.

### Urutan pencatatan dan run penutup

Readback ledger setelah pembaruan dokumentasi menunjukkan event full PASS memang tercatat, tetapi timestamp edit dokumen lebih baru daripada event itu. Ini masalah freshness pencatatan, bukan perubahan hash 13 file Python atau kegagalan tes aplikasi. Seluruh dokumentasi/receipt diselesaikan sebelum satu run penutup, kemudian hanya readback ledger dan cleanup tanpa edit berkas lagi. Bukti output run penutup adalah `backend/.artifacts/dashboard-foundation/canonical-full-final.json`; status aktual pada file dan ledger tersebut yang dipakai saat menutup pekerjaan. Event/failure lama tidak diedit atau dipalsukan.
