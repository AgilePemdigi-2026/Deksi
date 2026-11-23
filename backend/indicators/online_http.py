"""Bounded GETs to fixed official hosts; no credentials or download-form bypass."""
import time
from urllib.parse import urljoin, urlsplit

import httpx


class AcquisitionError(RuntimeError):
    """Safe operational error; never interpolate source payloads or tokens."""


def official_url(url):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname in {
            'bi.go.id', 'www.bi.go.id', 'data.bkpm.go.id', 'stats.bis.org', 'anggaran.kemenkeu.go.id',
        } and parsed.port in (None, 443) and not parsed.username and not parsed.password
            and not parsed.fragment and not any(ord(c) < 33 or c == '\\' for c in url))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise AcquisitionError('URL sumber tidak diizinkan.')
    return url


class OfficialHTTP:
    def __init__(self, *, client=None, pause=0.15, max_requests=160, max_bytes=2 * 1024 * 1024,
                 deadline_seconds=240):
        self.client = client
        self.own_client = client is None
        self.pause = pause
        self.max_requests = max_requests
        self.max_bytes = max_bytes
        self.deadline = time.monotonic() + deadline_seconds
        self.requests = 0

    def __enter__(self):
        if self.own_client:
            self.client = httpx.Client(timeout=httpx.Timeout(20, connect=10), follow_redirects=False,
                headers={'User-Agent': 'DEKSI/1.0 (official public statistics)'})
        return self

    def __exit__(self, *args):
        if self.own_client and self.client is not None:
            self.client.close()

    def get_bytes(self, url, params=None):
        if self.client is None:
            raise AcquisitionError('Klien HTTP belum dibuka.')
        current = official_url(url)
        # A redirect must stay within the same institution, not just any allowed host.
        institution = urlsplit(current).hostname
        if institution in ('bi.go.id', 'www.bi.go.id'):
            institution = 'bi.go.id'
        for _ in range(4):
            if self.requests >= self.max_requests or time.monotonic() >= self.deadline:
                raise AcquisitionError('Batas waktu atau jumlah request sumber terlampaui.')
            if self.requests:
                time.sleep(self.pause)
            self.requests += 1
            try:
                with self.client.stream('GET', current, params=params, follow_redirects=False) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        target = official_url(urljoin(str(response.url), response.headers.get('location', '')))
                        next_institution = urlsplit(target).hostname
                        if next_institution in ('bi.go.id', 'www.bi.go.id'):
                            next_institution = 'bi.go.id'
                        if next_institution != institution:
                            raise AcquisitionError('Redirect sumber berpindah institusi.')
                        current, params = target, None
                        continue
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.max_bytes or time.monotonic() >= self.deadline:
                            raise AcquisitionError('Respons sumber melewati batas ukuran atau waktu.')
                        chunks.append(chunk)
                    if not size:
                        raise AcquisitionError('Respons sumber kosong.')
                    return b''.join(chunks)
            except httpx.HTTPError as exc:
                raise AcquisitionError('Sumber resmi tidak dapat diakses; data lama tidak diganti.') from exc
        raise AcquisitionError('Redirect sumber terlalu banyak.')
