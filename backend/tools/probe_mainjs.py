import httpx
import re

r = httpx.get("https://djppr.kemenkeu.go.id/main.c943a91b9ad5a740.js", timeout=60)
text = r.text
print("size", len(text))
pats = set(re.findall(r'["\'](/[A-Za-z0-9_\-/]{3,60})["\']', text))
hits = [p for p in pats if any(k in p.lower() for k in ("paparan", "kita", "publikasi", "produk", "dokumen", "download"))]
for h in sorted(hits):
    print(h)
