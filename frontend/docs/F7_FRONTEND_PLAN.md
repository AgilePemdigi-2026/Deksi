# Batch 3 — frontend F7 Source Trace

**Update dependency/publikasi:** koreksi F6 telah di-commit terpisah pada `13a7680e96c1170cb9dcc041577e626760d8d76f` dan branch F7 sudah fast-forward ke sana sebelum memulihkan delta F7. Pengguna kemudian mengizinkan commit F7 dan push dua feature branch; batas tanpa PR/shared-branch merge tetap berlaku. Rencana dan checkpoint `14be3d9` di bawah menjelaskan tahap awal. Lihat [handoff publikasi](F7_PUBLICATION.md).

Status: diizinkan oleh pilihan pengguna "Izinkan checkpoint lokal F6 dan lanjut frontend F7", lalu "lanjutkan". Tidak memerlukan persetujuan rencana berulang untuk scope yang sama.

Hasil 3 November 2026: item 5 dan 6 selesai pada batas frontend; [handoff](F7_FRONTEND_HANDOFF.md) memisahkan bukti teknis, API live yang belum terhubung, dan review estetika F7 yang pending. Harness browser F6 digunakan ulang melalui flag `--source-trace`, bukan menyalin keseluruhan harness ke file baru.

## Dependency yang sudah diselesaikan

- F6 di-checkpoint lokal pada `feat/6-detail-indikator-fe`: `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`.
- Commit tepat 19 file frontend/docs/tests, identitas Git existing cocok dengan fondasi, tidak ada active commit hook, worktree F6 bersih setelah commit. Tidak push/PR/merge.
- Worktree F7: `E:/Deksi-Team/.hermes/worktrees/feature-7-source-trace-fe`.
- Branch F7: `feat/7-source-trace-fe`, base/HEAD awal `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`.
- Lockfile/dependency sama dengan checkpoint F6; paket existing disalin lokal tanpa install/upgrade. Checkpoint gabungan lama tetap tidak diubah.

## Item 5 — implementasi frontend Source Trace

- Adaptasi perilaku SourceTracePage checkpoint lama ke DTO dan guard F6, bukan menyalin fixture/schema ID demo.
- Buat `src/features/indicators/SourceTracePage.tsx`, tampilkan indikator/periode/nilai/satuan, jenis data backend, status dari backend, hubungan metadata, formula/input/hasil belum tersedia, metadata sumber/rilis/RAW, keterbatasan, serta pemisahan histori observasi dan revisi.
- Reuse helper, validasi, URL/context guard, shell/style editorial dan field dari F6. Ekstrak hook loading/cancellation ke `useDetailData.ts` agar dua screen menggunakan jalur data yang sama, tanpa mengganti transport dashboard.
- Aktifkan link F6 → F7 hanya bila konteks yang dipilih mempunyai guard cocok dan tidak ambigu. Return link mengikat konteks yang sama dan disabled saat gagal; tanpa fallback latest.
- File wiring: `App.tsx`, perubahan kecil terarah `DetailPage.tsx`; tambahan styling scoped F7. Tidak mengganti tema global, dashboard, Login, model/provider, backend atau API ekonomi.
- RAW download link hanya path API yang sesuai indikator, kemudian diikat ke origin API existing; tidak server-fetch URL sumber arbitrer.
- Formula, input, versi metode, hasil presisi/pembulatan, referensi tambahan dan jurnal revisi tetap unavailable karena API belum menyediakannya. Angka observasi tidak dipresentasikan sebagai hasil kalkulasi DEKSI.

## Item 6 — verifikasi dan preview

- RED→GREEN untuk render SourceTrace dan active/disabled navigation, exact identity dan nilai nol; kompatibilitas suite F6 tetap diuji.
- Tambah suite Source Trace terpisah; test fixture tetap hanya di tests. Uji escape/unsafe URL, RAW path salah indikator/origin, missing/partial/error/loading, invalid/context mismatch, tanpa revision/latest fallback.
- Extend harness browser disposable yang sudah diperbaiki pada F6 untuk F6 → F7 → kembali (termasuk konteks historis), deep-link/reload, rilis berubah/mismatch, empty/error, keyboard dan responsive. Tidak menutup atau mengubah browser pengguna; scratch eksplisit.
- Jalankan suite fitur + editorial, build/lint wajib; bedakan actual browser dengan API sintetis, API live, dan review visual. Tidak menjalankan bootstrap/backend melalui canonical detector root yang memilih Django.
- Preview F7 memakai port lokal terpisah; F6 port 5186 dan checkpoint lama dipertahankan. Sediakan screenshot berlabel sintetis jika memakai intersepsi tes; preview runtime sendiri tidak punya demo fallback.
- Diff F7 dihitung terhadap commit F6 `14be3d9780f65ea0ea85244c1f089ae93f8dec3c`, bukan fondasi 505e971 agar perubahan F6 tidak terhitung sebagai patch F7.

## Stop condition

Frontend F7 berfungsi dan diverifikasi pada batas frontend, preview disediakan, source/test hashes dan ruang lingkup tercatat. Review estetika F7 tetap pending sampai pengguna menilai halaman ini. Tidak commit F7, push, PR, merge atau backend tanpa izin terpisah. Keberhasilan fixture/browser/build bukan bukti pinned backend revision atau data resmi benar.
