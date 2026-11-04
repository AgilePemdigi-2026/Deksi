# BDD DEKSI — seluruh Sprint 1, Batch 1

**Tanggal:** 4 November 2026, UTC+07. **Status:** DRAFT FOR REVIEW; semua skenario **NOT RUN**.

Paket lokal ini berisi matriks kebutuhan dan Gherkin untuk delapan fitur backlog Sprint1: Login Admin, Lupa/Reset Password, Ringkasan Indikator, Grafik Tren, Filter Dashboard, Detail Indikator, Source Trace, dan Kirim Umpan Balik. Skenario lintas fitur menghubungkan alur tersebut. Fitur Sprint2, termasuk daftar/tambah sumber data, tidak termasuk.

## Hasil dua item Batch1
1. [Matriks traceability](TRACEABILITY.md): kebutuhan lokal → skenario API/browser dan pemetaan balik, dengan [katalog JSON](catalog.json).
2. [Skenario Gherkin](features/): spesifikasi Given–When–Then per fitur dan lintas fitur. Belum ada step definitions, runner, hook baru, fixture database ataupun perubahan aplikasi.

Baca [gate review dan gap kontrak](REVIEW_GATES.md) sebelum mengimplementasikan. [Sumber dan fingerprint](sources.json) membedakan SRS/laporan, proposal requirement lokal dan kontrak kandidat. [Verification](VERIFICATION.json) hanya memuat pemeriksaan dokumen/parser yang benar-benar dijalankan.

## Cara membaca skenario
- Keywords `Feature`, `Scenario`, `Given`, `When`, `Then` memakai bahasa Inggris agar parser default tidak memerlukan perubahan konfigurasi. Isi skenario menggunakan Bahasa Indonesia.
- `@sprint1`, `@f01` sampai `@f08`, `@x`: scope.
- `@BDD_*`: ID skenario; `@R_*`: requirement lokal; `@api`/`@browser`: lapisan utama yang diusulkan.
- `@not_run`: status saat penulisan, bukan hasil tes. `@needs_confirmation @Q*`: gate khusus yang belum final. Semua skenario lain juga menunggu review dan implementasi steps.
- ID R-* bukan ID FR resmi yang dikutip dari SRS. Detail parameter/status mengikuti kandidat yang dibaca dan harus direview.
- Browser berarti target E2E React → Django → database uji. Jika memakai mock, laporan harus menamainya browser-mocked, bukan E2E.

## Fixture dan oracle Batch2 yang diusulkan
- Akun Admin/nonstaff/nonaktif, password/email sintetis di database disposable; tidak membaca .env atau database aplikasi.
- Data indikator sintetis yang dibedakan draft, published tanpa review dan reviewed-published; API tidak boleh mengangkat angka nonpublik menjadi fixture sukses publik.
- Oracle desimal dan agregasi dari konstanta fixture yang diketahui, bukan menyalin actual response sebagai expected. Simbol `A`/`B` adalah label fixture, bukan ID produksi.
- Fault harness mengendalikan transport, urutan respons, jam, dan kegagalan simpan secara lokal; tidak perlu mematikan server kerja atau memakai provider.
- Reset menggunakan mailer locmem dalam proses backend test; harness mengambil email tanpa mencetak token. Tidak mengirim email atau menggunakan inbox nyata.
- Browser terisolasi, hostname/proxy yang konsisten dan CSRF aktif. Profil Chrome pengguna tidak dipakai. Fixture dibersihkan per skenario sesuai strategi isolasi runner yang diverifikasi pada Batch2.

## Struktur dan kewenangan
Paket berada di folder dokumentasi lokal yang Git root induknya adalah `Tonyraflysudarsono/Practice`, bukan checkout DEKSI. **Jangan commit di sini.** Lokasi ini sengaja tidak menyentuh dua worktree integrasi aktif. Perpindahan ke branch pengujian DEKSI merupakan pekerjaan berikutnya setelah izin dan checkpoint disepakati.

Dokumen lama di luar paket tetap historis dan tidak ditimpa. User telah memperluas scope BDD ke seluruh Sprint1 melalui chat; itu tidak memberikan izin implementasi fitur baru atau perubahan profil.

## Batch2 — belum dijalankan
Sesudah review matriks/kontrak dan izin implementasi: gunakan Behave-Django untuk API serta Behave + Selenium untuk alur browser. Buktikan satu jalur API dan satu browser lebih dahulu, kemudian otomatisasi matriks lengkap pada checkpoint gabungan. Instalasi bila perlu, service uji, migrasi disposable dan publication tetap mengikuti izin tersendiri.

Tidak ada perintah `behave` untuk eksekusi aplikasi yang dinyatakan siap dalam Batch1; file .feature ini belum mempunyai steps. Parsing sukses tidak berarti aplikasi PASS, fixture diterima sebagai data resmi, visual approval, production/security readiness atau seluruh FR final SRS tercakup.
