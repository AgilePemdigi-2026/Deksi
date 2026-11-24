# Ticket 01: Kebutuhan alat PDF

Type: research
Status: resolved

## Question

Perkakas ekstraksi PDF apa yang dipakai ingest KiTa (`fiscal.py`, `kemenkeu.py`, `fetch_kemenkeu.py`), dan apakah tersedia di image backend Docker (`backend/Dockerfile`, requirements)?

## Answer

`pdftotext` (Poppler CLI) via subprocess satu-satunya jalan (`kemenkeu.py:71-100`; dipakai `fiscal.py:80`). Tak ada di image (`python:3.14-slim` tanpa `poppler-utils`, tanpa lib PDF di requirements) dan tanpa fallback (raise `KitaError` bila hilang). Akibat: 19 pdf KiTa gagal ingest di mana pun tanpa Poppler; putuskan jalur host vs image di tiket 02.
