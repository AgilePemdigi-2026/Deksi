import glob
import io
import zipfile
import os

for f in sorted(glob.glob(r"C:\Users\azkad\Documents\PPLprak\Folder Scrapping\*2026*.zip")):
    with zipfile.ZipFile(f) as z:
        for name in z.namelist():
            if name.lower().endswith(".csv"):
                text = io.TextIOWrapper(z.open(name), encoding="utf-8-sig").readline()
                print(os.path.basename(f), "|", name)
                print("   header:", text.strip()[:400])
                with zipfile.ZipFile(f) as z2:
                    lines = io.TextIOWrapper(z2.open(name), encoding="utf-8-sig").readlines()
                    print("   rows:", len(lines))
                    for line in lines[1:3]:
                        print("   sample:", line.strip()[:220])
                    for line in lines[-2:]:
                        print("   last:", line.strip()[:220])
