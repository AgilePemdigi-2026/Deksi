# Ticket 03: Cakupan dan duplikat

Type: grilling
Status: resolved

## Question

Muat semua 89 file? Bagaimana perlakukan duplikat `(1)` vs `(10tahun)`, dan `synthetic-kita.pdf` ikut atau tidak?

## Answer

Muat semua kecuali `synthetic-kita.pdf` (data uji, cemari provenance). Duplikat `(1)` vs `(10tahun)` biar dedup checksum putuskan; file sama dilewati otomatis.
