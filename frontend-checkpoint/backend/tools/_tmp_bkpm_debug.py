import os, io, csv, zipfile
from decimal import Decimal
base = os.path.join(os.environ["USERPROFILE"], "Documents", "PPLprak", "Folder Scrapping")
f = os.path.join(base, "data-realisasi-investasi-triwulan-i-tahun-2025_6ae5e33455348.zip")
with zipfile.ZipFile(f) as z:
    text = io.TextIOWrapper(z.open("2025 TW1.csv"), encoding="utf-8-sig").read()
dia = csv.Sniffer().sniff(text[:4096], delimiters=",;")
print("dia:", dia.delimiter, repr(dia.quotechar), dia.doublequote, dia.skipinitialspace, dia.quoting)
reader = csv.reader(text.splitlines(), dia)
header = next(reader)
idx = header.index("investasi_rp_juta")
print("idx", idx)
total = Decimal(0)
n = 0
for row in reader:
    if len(row) <= idx:
        continue
    raw = row[idx].strip()
    if not raw:
        continue
    try:
        v = Decimal(raw)
    except Exception:
        continue
    total += v
    n += 1
print("rows", n, "totalT", total / Decimal(10**6))
