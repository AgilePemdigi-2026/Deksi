import httpx
import re

r = httpx.get("https://djppr.kemenkeu.go.id/main.c943a91b9ad5a740.js", timeout=60)
text = r.text
idxs = [m.start() for m in re.finditer("aparan", text, re.IGNORECASE)]
print("hits", len(idxs))
seen = set()
for i in idxs[:40]:
    s = text[max(0, i - 120):i + 120]
    if s not in seen:
        seen.add(s)
        print("----")
        print(s)
