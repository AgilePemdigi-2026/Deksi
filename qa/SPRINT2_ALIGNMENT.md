# Penyesuaian BDD sumber: kontrak aplikasi aktual

Sumber katalog awal: BDD-DEKSI `e9f7837e372c4bf6d371121aff87dd07cd09e74e`; kandidat aplikasi awal `df9d584c1f47826bb10b56dac7b6480f560ffaee`. Pengguna meminta penyesuaian BDD ke aplikasi yang diperbarui; ini bukan perubahan SRS yang disetujui tim.

- Skenario sumber F09–F11 tanpa perubahan perilaku dipertahankan. Binding diselaraskan dengan CSRF, `expectedRevision`, dan seed sumber yang sudah ada. F09-01 memastikan fixture dua sumber, bukan mengabaikan tambahan sumber seed. Run `20261117-233800-sprint2-sources-compatible`: 21 passed, 2 sengaja tidak dipilih, 83 steps passed; bukan laporan seluruh acceptance awal.
- `BDD-F10-05` dan `BDD-F11-04` aslinya mengharapkan endpoint tak terjangkau ditolak. Kedua acceptance dan hasil gagal `20261117-232324-sprint2-sources-csrf` dipertahankan; ini adalah ketidakselarasan persyaratan historis, bukan dihapus atau lulus.
- Skenario baru `ASBUILT-F10-05` dan `ASBUILT-F11-04` memeriksa create/edit menyimpan endpoint yang belum terbukti terjangkau tanpa menghubunginya, mempertahankan CSRF dan memeriksa revisi. Hasil `20261117-233108-sprint2-sources-current-fixed`: 2 passed. Pengujian memblokir probe menggunakan collaborator test; tidak membuktikan endpoint dapat dicapai. Run sebelumnya gagal karena harness memeriksa objek patch bukan mock dan tetap dipertahankan.
- F15–F18: `20261117-232139-sprint2-feedback-baseline` lulus 10 skenario API (SQLite disposable), pada kandidat `df9d584`; bukan hasil browser atau produksi. Hasil harus diperbarui bila source relevan berubah.
- `main` maju ke `11700194ab543af8198a4f72df78f1a3822d6bc6`; hasil di atas belum membuktikan kandidat itu. Cocokkan perubahan dan jalankan regresi ulang setelah upgrade kandidat.
