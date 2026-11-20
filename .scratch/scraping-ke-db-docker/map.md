# Map: Folder Scrapping masuk DB Docker

## Destination

Seluruh isi Folder Scrapping termuat ke database yang dipakai web Docker (RAW + kandidat ter-review/publish) dan tampil di dashboard, dengan keputusan jalur-PDF, cakupan, dan kebijakan publish terkunci.

## Notes

- Domain: pipeline ingest DEKSI (`ingest_datasets --dir` untuk xlsx/zip; `fetch_kemenkeu --from-dir` untuk pdf KiTa). Kandidat butuh review Admin sebelum publish; publik hanya lihat published + reviewed.
- Skills tiap sesi: `grilling` + `domain-modeling` untuk tiket HITL. Ikut aturan suara caveman di AGENTS.md.
- Berdiri: tanpa push tanpa izin; verifikasi via tes terarah; mari bicara DB sementara, bukan DB pengguna. Eksekusi ikut di peta ini (pengecualian wayfinder): tiket tugas terakhir wujudkan perubahan.

## Decisions so far

- [Ticket 01: Kebutuhan alat PDF](issues/01-kebutuhan-alat-pdf.md): ingest PDF hanya via `pdftotext`, hilang di image dan tanpa fallback.
- [Ticket 02: Jalur ingest PDF](issues/02-jalur-ingest-pdf.md): tambah `poppler-utils` ke image; tolak jalur host.
- [Ticket 03: Cakupan dan duplikat](issues/03-cakupan-dan-duplikat.md): semua file kecuali `synthetic-kita.pdf`; duplikat ikut dedup checksum.
- [Ticket 04: Kebijakan publish](issues/04-kebijakan-publish.md): kurasi satu-satu di Review Hasil Analisis, tanpa auto-publish.
- [Ticket 05: Muat dan verifikasi](issues/05-muat-dan-verifikasi.md): 3978 BI + 43 BKPM + 19 pdf masuk DB compose; publish tinggal kurasi manual.

## Not yet specified

- Jadwal ingest ulang rutin: sekali jalan cukup atau perlu cron/scheduler?
- Interaksi dengan sync BPS terjadwal: timpa, duplikat, atau saling lepas?
- Beban 44 zip + 19 pdf di container: memori/waktu, perlu batch?

## Out of scope

- Ubah parser, formula Economic Engine, atau skema DB.
- Sumber di luar Folder Scrapping; sinkronisasi API live.
- Deploy prod/Coolify; di luar DB web Docker lokal.
