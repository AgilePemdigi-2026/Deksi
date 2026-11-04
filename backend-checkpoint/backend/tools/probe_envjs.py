import httpx

r = httpx.get("https://djppr.kemenkeu.go.id/assets/js/env.js", timeout=30)
print(r.text[:1500])
