# F7 — persiapan publikasi terpisah di atas F6 terkoreksi

Status dokumen: bukti pra-commit/pra-push untuk unit F7. Pengguna mengizinkan pemisahan commit F6/F7 dan push dua feature branch, bukan PR atau shared-branch merge. Sukses push harus dibuktikan oleh SHA remote, bukan pernyataan di dokumen ini.

## Struktur branch

- Fondasi editorial: `505e97116f132c8630ec08d07525b8aec9e00536`.
- F6 awal: `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`.
- F6 terkoreksi dan dependency F7: **`13a7680e96c1170cb9dcc041577e626760d8d76f`**, branch `feat/6-detail-indikator-fe`.
- F7: `feat/7-source-trace-fe`, fast-forward ke F6 terkoreksi sebelum mengembalikan overlay F7. Tidak melakukan rebase/amend atau mengganti sejarah publik.

Lima file adapter/helper/type/test yang terkoreksi tidak menjadi delta F7 lagi. Perbedaan DetailPage terhadap F6 hanya wiring Source Trace, binding context, dan ekstraksi loader untuk dipakai kedua screen. Test page F6 hanya mengubah assertion tombol disabled menjadi exact-context link. Implementasi lengkap dan koreksi grafik F6 diwarisi dari parent, bukan disalin sebagai patch F7.

## Pemulihan aman

Seluruh 22 file overlay sebelum pemisahan disalin ke scratch terkelola, dicatat SHA-256, lalu disimpan dalam stash scoped frontend. Setelah fast-forward lokal, stash diterapkan tanpa konflik; semua 22 file cocok dengan backup setelah konversi CRLF/LF yang memang diterapkan core.autocrlf existing. Tidak menimpa checkpoint gabungan lama atau Login. Backup/stash recovery dipertahankan lokal; tidak dipush.

## Verifikasi aktual pasca-pemisahan

- `npm run test:indicators`: 33/33 PASS, 0 skip.
- `npm run test:source-trace`: 12/12 PASS, 0 skip.
- `npm test`: 7/7 editorial PASS, 0 skip.
- `HERMES_TEST_SCRATCH=... npm run test:source-trace:browser`: 18 kelompok PASS (8 F7 + 10 shared/F6/koreksi), 0 runtime exception.
- `HERMES_TEST_SCRATCH=... npm run test:browser`: 5 kelompok editorial PASS, 0 runtime exception.
- `npm run build`: exit 0, warning chunk >500 kB existing tetap ada.
- `npm run lint`: exit 0, tiga warning existing, tidak ada warning fitur baru.
- `git diff --check`: exit 0.

Log dan hash source terkini ada pada [receipt publikasi](F7_PUBLICATION.json). Bukti ini dijalankan setelah dependency diperbarui dan overlay dipulihkan; bukan mengutip angka PASS lama. Browser menggunakan API sintetis, bukan validasi payload/backend resmi. Dokumen receipt sebelumnya dipertahankan sebagai riwayat dan dibedakan dari receipt pasca-pemisahan ini.

## Batas publikasi dan integrasi

Push branch tidak sama dengan PR, merge atau deployment. Keduanya masih mewarisi fondasi editorial; publikasi tidak otomatis memasukkan fondasi ke main. Jika PR diusulkan kemudian, bandingkan F6 terhadap fondasi atau destination yang disepakati dan F7 terhadap F6; jangan menganggap PR F7 langsung ke main hanya memuat F7 ketika parent belum terintegrasi.

Frontend publik tidak menambahkan login. Source Trace tetap menunjukkan metadata formula/input/revisi unavailable bila API belum menyediakannya, menjaga null/zero, menolak context mismatch, serta memvalidasi URL sumber dan path RAW. Tidak ada scraping/provider/AI call atau fixture fallback runtime.

Review estetika F7, API nyata, formula/immutable revision backend dan remote CI tetap acceptance terpisah. Tidak mengklaim canonical verification atau end-to-end acceptance dari build/unit/browser sintetis. Identitas Git existing dipertahankan; tidak ada dependency/backend/shared-branch modification.
