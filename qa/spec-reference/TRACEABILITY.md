# Matriks BDD Sprint 1

Status spesifikasi: **DRAFT FOR REVIEW**. Status seluruh skenario: **NOT RUN**. ID R-* adalah ID lokal paket ini, bukan ID FR resmi dari SRS.

Sumber dan fingerprint: [sources.json](sources.json). Batas keputusan: [REVIEW_GATES.md](REVIEW_GATES.md). Daftar mesin: [catalog.json](catalog.json).

## Kebutuhan → skenario

| Requirement lokal | Perilaku | Dasar bacaan | Skenario API | Skenario browser |
|---|---|---|---|---|
| R-F01-01 | Akses Admin dan akses publik terpisah | AUTH; SRS 1.1, 2.3 | BDD-F01-02 | BDD-F01-01 |
| R-F01-02 | Validasi kredensial dan pembatasan percobaan | AUTH | BDD-F01-04 | BDD-F01-03 |
| R-F01-03 | Sesi dan logout ditegakkan server | AUTH | BDD-F01-05 | BDD-F01-06 |
| R-F01-04 | CSRF dan kegagalan autentikasi ditangani jujur | AUTH | BDD-F01-07 | BDD-F01-08 |
| R-F02-01 | Permintaan reset menjaga kerahasiaan akun | RESET; SPRINT | BDD-F02-01 | BDD-F02-02 |
| R-F02-02 | Token dan password divalidasi sebelum perubahan | RESET | BDD-F02-03 | BDD-F02-04 |
| R-F02-03 | Reset sukses tidak otomatis Login dan mencabut sesi lama | RESET | BDD-F02-06 | BDD-F02-05 |
| R-F02-04 | Reset gagal atau disabled tetap fail-closed | RESET | BDD-F02-07 | BDD-F02-08 |
| R-F03-01 | Ringkasan publik mempertahankan nilai dan konteks | SPRINT; SRS 2.2; DASH | BDD-F03-02 | BDD-F03-01 |
| R-F03-02 | Missing dan nol serta status pembaruan dibedakan | SRS 2.2; DASH | BDD-F03-04 | BDD-F03-03 |
| R-F03-03 | Hanya observasi yang layak publik boleh tampil | DASH; PRD Q-04 | BDD-F03-05 | BDD-F03-06 |
| R-F03-04 | Loading dan error bukan data sintetis pengganti | DASH; PRD Q-03 |  | BDD-F03-07, BDD-F03-08 |
| R-F04-01 | Histori mempertahankan seri dan presisi | DASH; PRD F6-04 | BDD-F04-01 | BDD-F04-02 |
| R-F04-02 | Granularitas dan kalkulasi berasal dari backend | DASH | BDD-F04-03 | BDD-F04-04 |
| R-F04-03 | Histori kosong dan gap tidak menjadi nol | PRD F6-04; DASH |  | BDD-F04-05, BDD-F04-06 |
| R-F04-04 | Perubahan indikator dan error tidak menampilkan seri keliru | DASH; PRD Q-03 |  | BDD-F04-07, BDD-F04-08 |
| R-F05-01 | Kategori dan tahun memilih konteks yang konsisten | SPRINT; DASH | BDD-F05-01 | BDD-F05-02 |
| R-F05-02 | Tahun tanpa data tidak memakai tahun lain | DASH | BDD-F05-03 | BDD-F05-04 |
| R-F05-03 | Parameter filter invalid ditolak aman | DASH | BDD-F05-05, BDD-F05-06 |  |
| R-F05-04 | Filter dapat dipulihkan tanpa data stale | DASH; FEPLAN |  | BDD-F05-07, BDD-F05-08 |
| R-F06-01 | Akses publik dan identitas indikator benar | PRD F6-01; SRS UC-02 |  | BDD-F06-01, BDD-F06-02 |
| R-F06-02 | Nilai dan perubahan tidak direka frontend | PRD F6-02,F6-03,F6-05 |  | BDD-F06-03, BDD-F06-04 |
| R-F06-03 | Histori dan metadata parsial ditampilkan jujur | PRD F6-04,F6-06 |  | BDD-F06-05, BDD-F06-06 |
| R-F06-04 | Navigasi dan request mempertahankan konteks | PRD F6-07; DASH |  | BDD-F06-07, BDD-F06-08 |
| R-F07-01 | Trace publik terikat observasi yang dipilih | PRD F7-01,F7-04; DASH | BDD-F07-01, BDD-F07-02 |  |
| R-F07-02 | Metadata resmi dan formula mempunyai batas epistemik | PRD F7-02,F7-03 |  | BDD-F07-03, BDD-F07-04 |
| R-F07-03 | Sumber dan RAW aman serta dapat ditelusuri | PRD F7-05; DASH | BDD-F07-06 | BDD-F07-05 |
| R-F07-04 | Partial missing dan error trace dibedakan | PRD F7-06; DASH |  | BDD-F07-07, BDD-F07-08 |
| R-F08-01 | Pengiriman anonim tersimpan pending | SPRINT; SRS UC-05; DASH | BDD-F08-02 | BDD-F08-01 |
| R-F08-02 | Validasi kategori deskripsi dan identitas opsional | DASH | BDD-F08-03 | BDD-F08-04 |
| R-F08-03 | CSRF dan pembatasan data publik ditegakkan | DASH | BDD-F08-05, BDD-F08-06 |  |
| R-F08-04 | Kegagalan dan konteks laporan tidak menyesatkan | SPRINT; DASH | BDD-F08-08 | BDD-F08-07 |
| R-X-01 | Publik tetap tersedia terlepas dari sesi Admin | SRS 1.1,2.2; FEPLAN | BDD-X-02 | BDD-X-01 |
| R-X-02 | Alur ringkasan detail trace dan feedback konsisten | SPRINT; DASH |  | BDD-X-03, BDD-X-04 |
| R-X-03 | Aksesibilitas dan status loading error tersedia | PRD Q-01,Q-02,Q-03 |  | BDD-X-05, BDD-X-06 |
| R-X-04 | Batas test dan informasi sensitif terjaga | PRD Q-04,Q-05; BEPLAN | BDD-X-07 | BDD-X-08 |

## Skenario → kebutuhan dan lapisan

| ID | Judul | Requirement | Lapisan | File | Gate khusus | Status |
|---|---|---|---|---|---|---|
| BDD-F01-01 | Admin aktif berhasil masuk | R-F01-01 | browser | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-02 | Akun non-Admin tidak memperoleh sesi Admin | R-F01-01 | api | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-03 | Password salah tidak memberi keberhasilan palsu | R-F01-02 | browser | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-04 | Lockout mengikuti kebijakan kandidat | R-F01-02 | api | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-05 | Sesi kedaluwarsa tidak tetap terautentikasi | R-F01-03 | api | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-06 | Logout membatalkan sesi server | R-F01-03 | browser | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-07 | Login tanpa CSRF ditolak | R-F01-04 | api | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F01-08 | Gangguan Login bukan kredensial salah atau sukses | R-F01-04 | browser | [f01_login.feature](features/f01_login.feature) | — | NOT RUN |
| BDD-F02-01 | Email dikenal dan tidak dikenal mendapat acknowledgement generik | R-F02-01 | api | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-02 | Form meminta koreksi email malformed | R-F02-01 | browser | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-03 | Token kedaluwarsa dan token terpakai ditolak | R-F02-02 | api | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-04 | Password konfirmasi tidak cocok | R-F02-02 | browser | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-05 | Reset lengkap melalui email locmem | R-F02-03 | browser | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-06 | Password tidak memenuhi policy tidak mengubah akun | R-F02-03 | api | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-07 | Reset default disabled tidak mengirim email | R-F02-04 | api | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F02-08 | Hasil confirm tidak pasti tidak diulang otomatis | R-F02-04 | browser | [f02_reset.feature](features/f02_reset.feature) | — | NOT RUN |
| BDD-F03-01 | Ringkasan dapat dibaca tanpa Login | R-F03-01 | browser | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-02 | Ringkasan mengikuti identitas pengukuran | R-F03-01 | api | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-03 | Nol sah tidak disamakan dengan data hilang | R-F03-02 | browser | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-04 | Pembaruan gagal mempertahankan last-valid | R-F03-02 | api | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-05 | Draft dan published tanpa review tidak bocor | R-F03-03 | api | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-06 | Tanggal sumber bukan waktu halaman dibuka | R-F03-03 | browser | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-07 | Loading tidak memakai angka demo | R-F03-04 | browser | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F03-08 | Error berbeda dari ringkasan kosong | R-F03-04 | browser | [f03_summary.feature](features/f03_summary.feature) | — | NOT RUN |
| BDD-F04-01 | Histori mengirim desimal exact | R-F04-01 | api | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-02 | Seri tidak sebanding tidak disambung | R-F04-01 | browser | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-03 | Agregasi deterministik sesuai oracle | R-F04-02 | api | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-04 | Pilihan frekuensi mengikuti backend | R-F04-02 | browser | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-05 | Gap kalender tidak menjadi observasi nol | R-F04-03 | browser | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-06 | Histori kosong memberi empty state | R-F04-03 | browser | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-07 | Respons indikator lama tidak mengganti pilihan baru | R-F04-04 | browser | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F04-08 | Grafik gagal memberi error dan retry | R-F04-04 | browser | [f04_trend.feature](features/f04_trend.feature) | — | NOT RUN |
| BDD-F05-01 | Filter tahun memilih observasi pada tahun itu | R-F05-01 | api | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-02 | Ringkasan dan histori mengikuti filter | R-F05-01 | browser | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-03 | Tahun kosong tidak fallback ke terbaru | R-F05-02 | api | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-04 | Rentang kosong tetap memperlihatkan filter aktif | R-F05-02 | browser | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-05 | Tahun di luar domain ditolak | R-F05-03 | api | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-06 | Parameter berulang dan kategori asing ditolak | R-F05-03 | api | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-07 | Reset filter kembali ke konteks terbaru | R-F05-04 | browser | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F05-08 | Request filter lama tidak menimpa pilihan aktif | R-F05-04 | browser | [f05_filter.feature](features/f05_filter.feature) | — | NOT RUN |
| BDD-F06-01 | Detail langsung dan dari kartu konsisten | R-F06-01 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-02 | Indikator asing tidak diganti PDB | R-F06-01 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-03 | Perubahan poin persentase tidak menjadi persen relatif | R-F06-02 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-04 | Tanpa fakta kausal tidak ada narasi sebab akibat | R-F06-02 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-05 | Metadata rilis yang hilang tetap hilang | R-F06-03 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-06 | Grafik detail mempunyai alternatif dan gap | R-F06-03 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-07 | Detail meneruskan selector observasi ke trace | R-F06-04 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F06-08 | Pergantian detail tidak dicemari respons lama | R-F06-04 | browser | [f06_detail.feature](features/f06_detail.feature) | — | NOT RUN |
| BDD-F07-01 | Selector lengkap tidak fallback ke terbaru | R-F07-01 | api | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F07-02 | Selector parsial ditolak | R-F07-01 | api | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F07-03 | Nilai resmi tidak memiliki formula buatan | R-F07-02 | browser | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F07-04 | Provenance belum immutable tidak diklaim versi beku | R-F07-02 | browser | [f07_trace.feature](features/f07_trace.feature) | Q03 | NOT RUN |
| BDD-F07-05 | Konten sumber berbahaya tidak dieksekusi | R-F07-03 | browser | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F07-06 | RAW checksum rusak tidak diunduh | R-F07-03 | api | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F07-07 | Metadata parsial tetap dapat dibaca | R-F07-04 | browser | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F07-08 | Error trace berbeda dari tidak ditemukan | R-F07-04 | browser | [f07_trace.feature](features/f07_trace.feature) | — | NOT RUN |
| BDD-F08-01 | Feedback anonim berhasil dikirim | R-F08-01 | browser | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-02 | Publik tidak dapat menentukan status Admin | R-F08-01 | api | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-03 | Batas panjang deskripsi kandidat | R-F08-02 | api | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-04 | Identitas opsional tidak menjadi kewajiban akun | R-F08-02 | browser | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-05 | Feedback tanpa CSRF tidak tersimpan | R-F08-03 | api | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-06 | Payload malformed tidak tersimpan | R-F08-03 | api | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-07 | Kegagalan simpan tidak memberi konfirmasi sukses | R-F08-04 | browser | [f08_feedback.feature](features/f08_feedback.feature) | — | NOT RUN |
| BDD-F08-08 | Konteks advisory bukan binding revisi | R-F08-04 | api | [f08_feedback.feature](features/f08_feedback.feature) | Q04 | NOT RUN |
| BDD-X-01 | Dashboard publik sebelum dan sesudah Login | R-X-01 | browser | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |
| BDD-X-02 | Pencabutan role Admin ditegakkan | R-X-01 | api | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |
| BDD-X-03 | Ringkasan detail trace membawa identitas yang sama | R-X-02 | browser | [x_cross.feature](features/x_cross.feature) | Q02 | NOT RUN |
| BDD-X-04 | Feedback setelah Login memakai CSRF yang berlaku | R-X-02 | browser | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |
| BDD-X-05 | Alur utama dapat dioperasikan keyboard | R-X-03 | browser | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |
| BDD-X-06 | Konten penting tetap terbaca pada viewport kecil | R-X-03 | browser | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |
| BDD-X-07 | Tes tidak memakai database atau provider kerja | R-X-04 | api | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |
| BDD-X-08 | Input sensitif tidak masuk URL atau storage | R-X-04 | browser | [x_cross.feature](features/x_cross.feature) | — | NOT RUN |

Coverage ini membuktikan setiap kebutuhan lokal dipetakan, bukan bukti seluruh FR rinci SRS sudah tercakup atau perilaku aplikasi telah lulus. Backend-only dan browser-only sengaja tidak diduplikasi untuk setiap requirement; skenario browser hanya dihitung E2E jika benar menggunakan backend/database pengujian, bukan mock.
