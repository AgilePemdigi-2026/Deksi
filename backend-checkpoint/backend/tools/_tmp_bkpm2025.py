import glob, io, zipfile, os
base = os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "PPLprak", "Folder Scrapping")
for f in sorted(glob.glob(os.path.join(base, "*investasi*2025*.zip"))):
    with zipfile.ZipFile(f) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            print("=" * 20, os.path.basename(f), name)
            lines = io.TextIOWrapper(z.open(name), encoding="utf-8-sig").readlines()
            print("rows:", len(lines))
            for line in lines[:3]:
                print("  H:", line.strip()[:400])
            for line in lines[3:8]:
                print("  R:", line.strip()[:400])
            for line in lines[-2:]:
                print("  L:", line.strip()[:400])
