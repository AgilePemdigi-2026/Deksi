import re
import sys
import httpx
H = {'User-Agent': 'Mozilla/5.0 DEKSI-research'}
try:
    t = httpx.get('https://anggaran.kemenkeu.go.id/main.js', timeout=90, headers=H).text
except Exception as e:
    print('FETCH_ERR', type(e).__name__, str(e)[:150])
    sys.exit(0)
print('LEN', len(t))
for key in ['GeneralSearch', 'PageIndex', 'PageSize', 'Keyword']:
    idxs = [m.start() for m in re.finditer(re.escape(key), t)]
    print('####', key, 'hits:', len(idxs))
    for i in idxs[:3]:
        print(t[max(0, i-160):i+160].replace('\n', ' '))
        print('---')
