# Rancangan BDD Sprint 2 — fitur 19, 23, 24, 26, 27

**Status: DRAFT / sebagian NOT RUN.** Berkas `.feature` di folder ini adalah
rancangan Gherkin, bukan bukti implementasi atau persetujuan requirement.
ID `BDD-F*` adalah ID lokal rancangan, bukan nomor FR resmi.

Skenario bertanda `@api` yang SUDAH diikat ke binding executable hidup di:
- `qa/features/monitoring-schedules/` — F19 Monitoring Admin, F23 Jadwal Pembaruan
- `qa/features/config/` — F24 Threshold Diagnostik, F26 Notifikasi, F27 Restore Default

Skenario bertanda `@browser` saja adalah usulan lapisan uji, belum ada binding.
Jangan menambahkannya ke discovery runner tanpa binding, review, dan izin tersendiri.

## Cakupan

| Fitur | Rancangan | Skenario | Terikat executable |
|---|---|---|---|
| 19 | [Monitoring Admin](f19_monitoring.feature) | 7 | 6 @api |
| 20 | [Narasi Grounded AI](f20_narasi.feature) | 5 | 0 — DRAFT, belum ada implementasi |
| 21 | [Detail Peninjauan](f21_review.feature) | 7 | 5 @api |
| 22 | [Keputusan Publikasi](f22_keputusan.feature) | 7 | 5 @api |
| 23 | [Jadwal Pembaruan](f23_jadwal.feature) | 9 | 7 @api |
| 24 | [Threshold Diagnostik](f24_threshold.feature) | 11 | 9 @api |
| 25 | [Kebijakan Grounded AI](f25_kebijakan_ai.feature) | 6 | 0 — DRAFT, belum ada implementasi |
| 26 | [Notifikasi](f26_notifikasi.feature) | 8 | 6 @api |
| 27 | [Restore Default](f27_restore.feature) | 7 | 5 @api |

F20 dan F25 tidak memiliki endpoint, model, maupun halaman di codebase.
Skenarionya murni rancangan menunggu kontrak disepakati. Fallback yang sudah
ada: tanpa narasi, indikator terstruktur dan Source Trace tetap tampil.

Pemetaan goals: F19 mencakup ringkasan, kartu status, dan proteksi akses;
pengalihan pengunjung ke halaman login adalah perilaku routing browser dan
tercatat sebagai skenario browser terpisah. F23 mencakup validasi, versi, audit,
dan jaminan akses publik tidak terganggu; penundaan saat bentrok dengan akuisisi
berjalan BELUM diimplementasikan API dan dicatat sebagai gap. F24 mencakup
penolakan nilai invalid dengan pesan yang diharapkan, penguncian formula inti
(parameter tak terdaftar selalu 404), peran non-staf 403, versi, dan audit;
konfirmasi tambahan untuk perubahan kritis BELUM ada di API. F26 mencakup tiga
jenis minimal, validasi, versi, audit, dan event mengikuti preferensi;
pembatalan sebelum simpan adalah state frontend. F27 mencakup pesan pengaturan
awal, audit `restore-default`, threshold `skipped`, dan validasi domain;
penundaan saat bentrok proses aktif BELUM diimplementasikan API.

## Dasar yang dibaca

- Branch `BDD-DEKSI` setelah merge `origin/main`: `backend/indicators/monitoring_views.py`,
  `schedule_views.py`, `threshold_views.py`, `notification_views.py`,
  `config_restore_views.py`, `config_restore_service.py`, `threshold_registry.py`,
  `notification_model.py`, `schedule_model.py`, `threshold_model.py`, `urls.py`.
  Ini acuan perilaku yang dibaca, **bukan bukti deployment**.
- Kontrak data sintetis: semua record BDD bernama `SYNTHETIC BDD`, hidup di
  database disposable milik runner, tanpa provider resmi dan tanpa data aktif.

## Review dan ketidakpastian sebelum otomatisasi

- F19 memakai ringkasan baca-saja; label kualitas (`Baik`/`Perlu perhatian`/`Buruk`)
  dihitung dari observasi, bukan status buatan. Jangan mengklaimnya sebagai
  penilaian resmi lembaga.
- F23 `next_run` hanya informasi; tidak ada worker terjadwal yang mengeksekusinya
  di codebase ini. Jangan menyajikan jadwal sebagai janji eksekusi otomatis.
- F24 tidak menyentuh formula inti Economic Engine; registry hanya ambang peringatan.
  Status `inactive` berarti evaluasi memakai default — sepakati maknanya dulu.
- F26 `notified` mengikuti preferensi saat event dicatat; kanal eksternal belum ada.
  Jangan mengklaim email/Telegram terkirim.
- F27 threshold selalu `skipped-unsupported` menurut implementasi saat ini.
  Jangan mengarang nilai restore untuk threshold.
- `unknown` bukan sukses maupun gagal. `queued` bukan bukti worker hidup.
- Saat tahap pengujian disetujui, gunakan fixture sintetis berlabel, database dan
  profil browser disposable, port terpisah, pertahankan CSRF, mock provider.
  Jangan menyentuh DB aktif atau menjalankan provider resmi.
