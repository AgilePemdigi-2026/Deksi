# Ticket 05: Muat dan verifikasi

Type: task
Status: resolved
Blocked by: 02, 03, 04

## Answer

Selesai di stack compose (backend `127.0.0.1:8000`, frontend `127.0.0.1:5174`, db service `db` volume `pgdata`).
- Image tambah `poppler-utils` (`pdftotext` 25.03.0) + `openpyxl==3.1.5`; mount `../Folder Scrapping:/scraping:ro`.
- `ingest_datasets --dir /scraping`: BI 3978 baris, BKPM 43 triwulan, 0 error (6 xlsx awal gagal tanpa openpyxl, sukses setelah tambah).
- `fetch_kemenkeu --from-dir /scraping`: 19/19 pdf sukses, 0 gagal; `synthetic-kita.pdf` terlewati otomatis oleh glob.
- DB: 4062 kandidat pending, 68 RAW, 23 sync-run (1 failed warisan upaya pertama: BI read_file tanpa openpyxl). Sequence disejajarkan ulang.
- API publik benar tampil tak-tersedia (kandidat belum direview). Sisa manual: kurasi + publish di Review Hasil Analisis (`:5174`).
- Catatan: Postgres host tak ada di mesin ini, jadi DB hidup sebagai service `db` di compose (bukan host). Password dev `deksi`, tanpa port publik.

## Question

Mount Folder Scrapping read-only ke backend, jalankan ingest xlsx/zip/pdf sesuai keputusan 02-04, catat counts/errors, verifikasi via API dan UI web.

Checklist:

- [ ] Mount `../Folder Scrapping:/scraping:ro` di compose (atau salin bila spasi ganggu).
- [ ] `ingest_datasets --dir /scraping`; catat bi_rows/bkpm_quarters/errors.
- [ ] Ingest pdf via jalur tiket 02; catat hasil per file.
- [ ] Kandidat terbit sesuai tiket 04; cek dashboard tampil nilai baru.
