import os, io, csv, zipfile
from decimal import Decimal
from indicators.parsing import parse_id_number
base = os.path.join(os.environ["USERPROFILE"], "Documents", "PPLprak", "Folder Scrapping")
f = os.path.join(base, "data-realisasi-investasi-triwulan-i-tahun-2025_6ae5e33455348.zip")
with zipfile.ZipFile(f) as z:
    with z.open("2025 TW1.csv") as fh:
        rd = csv.reader(io.TextIOWrapper(fh, encoding="utf-8-sig").read().splitlines())
        header = next(rd)
        idx = header.index("investasi_rp_juta")
        shown = 0
        diff = 0
        total = Decimal(0)
        for row in rd:
            if len(row) <= idx:
                continue
            raw = row[idx].strip()
            if not raw:
                continue
            try:
                direct = Decimal(raw)
            except Exception:
                continue
            parsed = parse_id_number(raw)
            total += parsed
            if parsed != direct:
                diff += 1
                if shown < 10:
                    shown += 1
                    print("DIFF", raw, "=>", parsed)
        print("diffs", diff, "totalT_parsed", total / Decimal(10**6))
