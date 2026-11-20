# Ticket 02: Jalur ingest PDF

Type: grilling
Status: resolved
Blocked by: 01

## Question

Ingest 19 pdf KiTa jalan dari host (venv + perkakas lokal, tulis ke Postgres host) atau tambah perkakas ke image lalu exec di container?

## Answer

Tambah `poppler-utils` ke `backend/Dockerfile`; pdf jalan di container bareng xlsx/zip. Satu baris `apt-get`, permanen untuk semua orang. Jalur host ditolak: tambah variabel Poppler Windows + env DB, rapuh tiap mesin.
