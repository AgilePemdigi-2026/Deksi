# Penyesuaian BDD ke fitur dan dashboard asli — as-built v2

Instruksi: sesuaikan BDD dengan fitur dan dashboard asli. Scope perubahan hanya QA dan dokumentasi di `E:/Deksi-BDD-Sprint1`; bukan izin mengubah produk, database demo, konfigurasi provider, dependency atau Git publikasi.

**Catatan izin lanjutan:** paragraf di atas mencatat scope saat alignment v2. Pada 7 November 2026 pengguna kemudian meminta "perbaiki yang fail atau hapus jika emang itu ga ada di fitur kita". Kedua FAIL relevan dengan layout dashboard dan konteks filter→Detail, sehingga tes dipertahankan dan dua file produk diperbaiki hanya di worktree BDD milik tugas. Kandidat v2.1 memakai branch lokal `fix/sprint1-bdd-layout-empty-year`; belum di-commit/dipublikasikan. Oracle regresi justru diperkuat agar penolakan eksplisit harus menyebut tahun yang dipilih. Acceptance lama dan source lane sesi lain tetap tidak diubah.

## Basis implementasi yang diperiksa

FE `integration/sprint1-docker-fe` (`e35d97899d345f18a3341bc19beba431f94179d9`) dan BE `integration/sprint-1-unified-be` (`d9c673fac84992b91c160bfaa4f0de33a8ce548b`). Ref integration lokal dan status lane diperiksa ulang; tidak ditemukan FE integration lokal lebih baru atau overlay FE. BE pemilik hanya menunjukkan `.hermes/` dan `NUL` untracked; tidak diambil sebagai source aplikasi. Tidak ada klaim refresh GitHub.

## Batch dan acceptance pekerjaan QA

1. Inventarisasi kontrol, route dan API asli; buat suite **as-built v2** terpisah. Pertahankan baseline v1 dan hasil historis, beri ID baru pada skenario yang berubah, serta petakan gap kebutuhan yang belum ditutup.
2. Buktikan tiga skenario pengganti lewat browser/API asli, jalankan seluruh katalog as-built dan regresi, cek tidak ada DTO sukses mock, tidak ada ID ganda, source pin cocok dan resource disposable dibersihkan. Hasil FAIL produk tetap FAIL.

## Pemetaan delapan fitur

Semua path source FE di bawah relatif terhadap `frontend-checkpoint/frontend/src/`. Endpoint dijalankan melalui proxy same-origin menuju Django pengujian, bukan aplikasi demo aktif.

| Fitur | Halaman/kontrol nyata | API yang diuji | Source utama |
|---|---|---|---|
| 1 Login Admin | `/admin/login`, identifier, password, tampilkan password, masuk, status sesi dan Logout; publik tanpa akun | `/api/auth/csrf/`, `/api/auth/login/`, `/api/auth/session/`, `/api/auth/logout/` | `features/admin/LoginPage.tsx`, `auth.ts` |
| 2 Reset Password | `/admin/forgot-password`, email, kirim ulang; `/admin/reset-password`, dua password, capability dari fragment yang dikonsumsi UI, kembali Login | `/api/auth/password-reset/request/`, `/check/`, `/confirm/` di prefix reset yang sama | `features/admin/ForgotPasswordPage.tsx`, `ResetPasswordPage.tsx` |
| 3 Ringkasan | Dashboard `/`, hero/ikhtisar dan kartu memakai angka API, unit, periode dan rilis; loading/error/empty tanpa angka demo | `/api/indicators/dashboard/`, `/api/indicators/`, status pembaruan tersimpan | `features/dashboard/Dashboard.tsx`, `hooks.ts`, `client.ts` |
| 4 Tren | Panel DERET WAKTU, pilihan indikator; periode asli/Kuartalan/Bulanan/Tahunan hanya jika ditawarkan backend; rentang 3/5/10/Semua; titik, tabel histori dan JSON | `/api/indicators/<code>/trend/`, parameter `granularity`; konteks trace untuk titik | `features/dashboard/DashboardTrend.tsx` |
| 5 Filter | Cari indikator/institusi, kategori, `#filter-year`, Reset; tahun tidak memiliki data tetap unavailable | Dashboard query `category`/`year`, `/api/indicators/categories/` | `components/DashboardFilter.tsx`, `Dashboard.tsx` |
| 6 Detail | `/indikator/<code>`, kartu → detail, nilai/unit/periode, pembanding backend, tabel histori, selector observasi, sumber dan waktu | Summary + trend + source-trace; empat selector URL dan guard frontend | `features/indicators/DetailPage.tsx`, `api.ts` |
| 7 Source Trace | `/indikator/<code>/sumber`, nilai/sumber/periode, metadata rilis/RAW, URL aman, selector konteks dan kembali Detail; keterbatasan formula/revisi ditampilkan | `/api/indicators/<code>/source-trace/`, RAW download yang sudah tervalidasi pada backend | `features/indicators/SourceTracePage.tsx`, `api.ts` |
| 8 Feedback | Form dashboard, kategori/deskripsi, identitas dan konteks opsional, hasil hanya sesudah simpan pending; tidak otomatis mengulang POST gagal | `/api/feedback/categories/`, `/api/feedback/` dengan CSRF | `components/FeedbackForm.tsx` |

Data pengujian tetap **SYNTHETIC**, direkam pada database disposable. “Asli” berarti source React/Django, kontrol, route dan kontrak aktual—bukan memakai data resmi atau mengirim feedback ke database kerja.

## Perubahan yang disengaja

69 skenario tetap memakai ID dan oracle sebelumnya. Tiga skenario diganti dengan ID as-built yang berbeda, sehingga PASS baru tidak menulis ulang kegagalan acceptance lama:

| Baseline v1 tetap ada | As-built v2 | Yang benar-benar diperiksa | Gap yang tidak ditutup |
|---|---|---|---|
| `BDD-F06-02` menuntut not-found khusus | `ASBUILT-F06-02` | Kode asing tetap asing, nilai tidak tersedia, rincian HTTP 404 dapat dibuka, tidak ada angka PDB/fallback/Login | Banner/state not-found khusus masih kebutuhan acceptance terbuka |
| `BDD-F07-03` memerlukan DTO official mock | `ASBUILT-F07-03` | Respons backend nyata `unclassified`, `officialVerification=unassessed`, formula/input tidak tersedia, `revisionId=null`, `immutableSnapshot=false`; UI tidak membuat angka/formula/revisi | Dukungan klasifikasi official/derived pada backend–adapter–UI belum dibuktikan; tes mock lama bukan E2E |
| `BDD-F07-08` menuntut state error terpisah pada tampilan utama | `ASBUILT-F07-08` | Rincian respons dibuka melalui kontrol asli: HTTP 404 berbeda dari transport gagal; nilai/provenance tidak diisi pengganti, Coba lagi tersedia | Pemisahan state utama yang lebih menonjol tetap gap acceptance, bukan dinyatakan sudah diperbaiki |

Dasar source: adapter `features/indicators/api.ts:94-111` menyimpan status HTTP/transport pada warnings, UI menyediakan rincian melalui `details`; `SourceTracePage.tsx:30` belum merender klasifikasi. Backend `indicators/views.py:406-417` memang belum menyimpan formula berversi atau revisi immutable untuk observasi ini.

## Pengujian yang tidak diturunkan standarnya

- Publik anonim, pembatasan Admin, CSRF, validasi payload dan publication/review gate.
- Angka exact, persen vs poin persentase, nilai kosong bukan nol, gap kalender dan seri tidak sebanding.
- Respons terlambat tidak mencampur indikator/tahun, serta selector konteks tidak boleh berpindah ke angka lain.
- Teks sumber dan URL berbahaya tidak menjadi eksekusi; integritas RAW dan feedback pending ditegakkan.
- **`REG-EMPTY-YEAR-DETAIL`** dan **`BDD-X-06`** tetap berjalan; navigasi tahun kosong ke terbaru dan overflow tidak dijadikan expected behaviour agar hijau.

## Struktur versi dan bukti

- `qa/features/*.feature`: baseline v1, tidak diubah.
- `qa/features/as-built/*.feature`: sembilan feature as-built, 72 skenario, tag `@as_built`.
- `qa/as-built-manifest.json`: 72 ID persis, tiga penggantian, hash feature, hash baseline dan gap acceptance; v2.1 menambah fingerprint dashboard CSS ke 17 source pin awal serta metadata overlay lokal. Manifest v2 sebelum perbaikan dipertahankan terpisah.
- `qa/features/steps/asbuilt_steps.py`: tiga binding baru tanpa DTO success mock.
- Runner default `--suite as-built`. Baseline tetap dapat dipilih dengan `--suite baseline`; filter path mencegah kedua versi ditemukan sekaligus.
- Run receipt menyimpan suite ID, manifest dan source hashes. Reporter memeriksa katalog yang benar, bukan menganggap semua versi adalah baseline lama.
- SMTP, provider resmi, Selenium, rekonsiliasi SRS final dan persetujuan visual/manusia tidak diklaim dari hasil teknis ini. Q01–Q09 tidak ditutup otomatis.
