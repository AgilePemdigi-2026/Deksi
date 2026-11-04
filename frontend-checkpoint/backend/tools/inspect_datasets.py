import glob
import os
import openpyxl

BASE = r"C:\Users\azkad\Documents\PPLprak\Folder Scrapping"

for f in glob.glob(os.path.join(BASE, "*.xlsx")):
    wb = openpyxl.load_workbook(f, read_only=True)
    for ws in wb.worksheets:
        rows = list(ws.values)
        print("==", os.path.basename(f), "| sheet:", ws.title, "| rows:", ws.max_row, "| cols:", ws.max_column)
        for r in rows[5:12]:
            print([repr(c)[:40] if c else "" for c in r])
        print("last:", [repr(c)[:40] if c else "" for c in rows[-1]])
    wb.close()
