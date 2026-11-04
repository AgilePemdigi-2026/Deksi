import httpx

bases = [
    "https://djppr.kemenkeu.go.id",
]
paths = [
    "/api/paparan-apbn-kita",
    "/api/paparanapbnkita",
    "/api/getPaparanKita",
    "/api/v1/paparan",
    "/rest/v1/paparan",
    "/api/v1/tentang-paparan",
    "/api/v1/konten/",
]
for b in bases:
    for p in paths:
        try:
            r = httpx.get(b + p, timeout=20, follow_redirects=False)
            print(p, r.status_code, r.headers.get("content-type"), r.text[:200].replace("\n", " "))
        except Exception as e:
            print(p, "ERR", type(e).__name__)
