# Rancangan BDD Sprint 2 — fitur 12, 13, 14

**Status: DRAFT / semua skenario NOT RUN.** Ini hanya rancangan Gherkin, bukan hasil tes, bukti implementasi, persetujuan requirement, atau suite yang dapat dijalankan. Tidak ada binding/runner baru, provider, server, database, browser atau tes yang dijalankan dalam penyusunan. ID `BDD-F12-*` dst. adalah ID lokal rancangan, bukan nomor FR resmi.

## Cakupan

| Fitur | Rancangan | Skenario | Sasaran |
|---|---|---:|---|
| 12 | [Status sumber](f12_status_sumber.feature) | 8 | Aktif/nonaktif, kontrol revisi, akses, akuisisi dan hasil refresh |
| 13 | [Riwayat sinkronisasi](f13_riwayat_sinkronisasi.feature) | 9 | Daftar, filter, pagination, data kosong/gagal, keamanan dan navigasi |
| 14 | [Sinkronisasi ulang BPS](f14_resinkronisasi_bps.feature) | 12 | Permintaan, antrean, idempotensi, kegagalan, rekonsiliasi dan batas publikasi |

F12-01–08, F13-01–09, dan F14-01–12 masing-masing hanya rancangan. Label `@api` dan `@browser` menyatakan **lapisan uji yang diusulkan**, bukan tes yang sudah ada atau lulus. Paket sengaja disimpan di `qa/spec-reference/`, terpisah dari suite executable dan katalog Sprint 1; jangan menambahkannya ke discovery runner tanpa rancangan binding, review dan izin tersendiri.

## Dasar yang dibaca

- Branch `BDD-DEKSI` pada `5712091882e65ca6974708b6e6188efa8f994550`: format skenario F09–F11 dan F15–F18; isi paket ini tidak menimpa atau mengubah hasil dan skenario lama.
- Kode aplikasi `main` pada `eab9b393efdd5229a07a003126970d62ea44ba9f`: `frontend/src/components/AdminSourcesPage.tsx`, `frontend/src/features/resync/ResyncAction.tsx`, `backend/indicators/resync_views.py`, `backend/indicators/sync_history_views.py`, `backend/indicators/source_status.py`, dan `backend/indicators/urls.py`. Ini acuan perilaku yang dibaca, **bukan bukti deployment**.
- Dokumen operasional kandidat `docs/feature14-operations.md` dari worktree fitur 14: acuan batas worker, antrean, `unknown`, dan review sebelum publikasi; status kandidat historis dalam dokumen itu tidak diperbarui oleh rancangan ini.

## Review dan ketidakpastian sebelum otomatisasi

- F12-08 adalah **perilaku yang diharapkan untuk direview**, bukan klaim bahwa tampilan sekarang membedakan penyimpanan berhasil dari refresh gagal. Jangan mengubah ekspektasi hanya supaya lulus; catat gap jika belum tersedia.
- F12-05 mengusulkan guard untuk pekerjaan baru; F12-06 tidak menjanjikan pembatalan request/provider yang sudah berjalan. F14-10 terbatas pada jalur BPS yang dipagari; tidak mengklaim membatalkan request yang sudah terlanjur keluar.
- F14 saat ini dibatasi BPS. `queued` bukan sukses; `running` bukan bukti worker masih hidup; `unknown` bukan sukses maupun gagal. Identitas job berbeda dari ID run riwayat; periksa sebelum rekonsiliasi.
- F14-11 menyatakan batas produk: kandidat baru perlu review sebelum publikasi. Verifikasi detail aktual dan kesepakatan tim saat implementasi binding, jangan mengarang status atau nilai resmi.
- Berbagai halaman 2 dan 3 boleh berubah jika data bertambah selama pagination; F13-03 mensyaratkan dataset tidak berubah agar pemeriksaan tidak duplikat bermakna.
- Kontrak pengguna/peran, perubahan status saat proses berjalan, isi detail kegagalan, dan kesesuaian dengan dokumen backlog/SRS final masih perlu review tim. Jangan menganggap rancangan ini pengganti SRS atau persetujuan tim. REQ-03 soal reachability sumber adalah deviasi terpisah; rancangan ini tidak mengizinkan probe URL arbitrer.
- Saat tahap pengujian nanti disetujui, gunakan fixture sintetis berlabel, database dan profil browser disposable, proxy/port terpisah, pertahankan CSRF, dan mock provider. Jangan menyentuh DB aktif, menjalankan provider resmi, atau menganggap mock sebagai bukti data resmi.
