import os, sys, io, csv, zipfile, re
from decimal import Decimal
base = os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "PPLprak", "Folder Scrapping")
files = sorted(glob := __import__("glob").glob(os.path.join(base, "*investasi*.zip")))
pats = sys.argv[1:] or ["2025", "2026"]
for f in files:
    if not any(p in os.path.basename(f) for p in pats):
        continue
    with zipfile.ZipFile(f) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        text = io.TextIOWrapper(z.open(name), encoding="utf-8-sig").read()
        header = text.splitlines()[0]
        if "investasi_rp_juta" not in header:
            print("SKIP", os.path.basename(f))
            continue
        idx = header.split(",")[11] and [h.strip('"') for h in header.split(",")].index("investasi_rp_juta")
        total = Decimal(0)
        bad = 0
        n = 0
        mx = Decimal(0)
        for row in csv.reader(text.splitlines()):
            if row and len(row) > idx:
                raw = row[idx].strip()
                if raw == "":
                    continue
                try:
                    v = Decimal(raw)
                except Exception:
                    bad += 1
                    if bad <= 3:
                        print("   unparsed:", raw)
                    continue
                total += v
                n += 1
                mx = max(mx, v)
        grand = total / Decimal(10**6)
        print(os.path.basename(f)[:60], f"rows={n} totalT={grand} maxRowT={mx/Decimal(10**6)} bad={bad}")
