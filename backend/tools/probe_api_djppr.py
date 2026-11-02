import httpx

BASE = "https://api-djppr.kemenkeu.go.id/web/api/v1"
paths = [
    "/landing/paparan",
    "/paparan",
    "/paparanapbnkita",
    "/menu/paparan",
    "/produk/paparan",
    "/publikasi/paparan",
    "/slot",
]
for p in paths:
    try:
        r = httpx.get(BASE + p, timeout=20, follow_redirects=False)
        body = r.text[:300].replace("\n", " ")
        print(p, r.status_code, r.headers.get("content-type", ""), body)
    except Exception as e:
        print(p, "ERR", type(e).__name__, str(e)[:120])
