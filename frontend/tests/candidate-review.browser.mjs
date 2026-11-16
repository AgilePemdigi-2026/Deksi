import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-review-browser-'))
const calls = []
let status = 'pending'
let releaseReview
let forcedReviewStatus = 0
let detailFailure = false
let includeEvidence = false
const candidate = () => ({ id: 1, fingerprint: 'a'.repeat(64), indicator: 'inflasi', indicatorName: 'Inflasi UJI',
  sourceId: 'BPS', sourceName: 'BPS UJI', sourceUrl: 'https://example.test/', period: 'UJI 2024',
  observationDate: '2024-01-31', publicationDate: null, frequency: 'monthly', dataType: 'yoy',
  value: '3.250000', unit: '%', rawFileId: includeEvidence ? 9 : null,
  rawEvidence: includeEvidence ? { documentName: 'Dokumen sintetis', periodLabel: 'Periode sintetis', retrievedAt: null, checksumSha256: 'c'.repeat(64) } : null,
  status, createdAt: '2024-02-01T00:00:00Z',
  reviewedAt: status === 'published' ? '2024-02-02T00:00:00Z' : null, reviewedBy: status === 'published' ? 'UJI' : null, reviewNotes: '' })
const mockApi = (req, res, next) => {
  if (!req.url.startsWith('/api/')) return next()
  calls.push({ method: req.method, path: req.url.split('?')[0] })
  res.setHeader('Content-Type', 'application/json')
  const route = req.url.split('?')[0]
  const send = body => res.end(JSON.stringify(body))
  if (route === '/api/admin/session/') return send({ authenticated: true, username: 'UJI', isStaff: true, canReviewCandidates: true })
  if (route === '/api/admin/sources/acquisition-methods/') return send({ methods: [], frequencies: [] })
  if (route === '/api/admin/sources/') return send({ sources: [{ sourceId: 'BPS', sourceName: 'BPS UJI',
    institution: 'Sumber UJI', status: 'active', acquisitionMethod: 'api_bps', dataFormat: 'json',
    frequency: 'mixed', lastFetch: {} }, { sourceId: 'OTHER', sourceName: 'Sumber lain',
    institution: 'Sumber UJI', status: 'active', acquisitionMethod: '', dataFormat: 'json',
    frequency: 'mixed', lastFetch: {} }] })
  if (route === '/api/admin/sources/BPS/resync-active/') return send({ job: null })
  if (route === '/api/auth/csrf/') return send({ csrfToken: 'synthetic-token' })
  if (route === '/api/admin/sources/BPS/candidates/') {
    const filter = new URL(req.url, 'http://localhost').searchParams.get('status') || 'pending'
    const items = filter === status ? [candidate()] : []
    return send({ items, page: 1, pageSize: 20, total: items.length, hasNext: false })
  }
  if (route === '/api/admin/sources/BPS/candidates/1/' && req.method === 'GET') {
    if (detailFailure) { res.statusCode = 503; return send({ error: 'synthetic failure' }) }
    return send({ candidate: candidate() })
  }
  if (route === '/api/admin/sources/BPS/candidates/1/review/' && req.method === 'POST') {
    let input = ''
    req.on('data', chunk => { input += chunk })
    req.on('end', () => {
      const body = JSON.parse(input)
      assert.equal(req.headers['x-csrftoken'], 'synthetic-token')
      assert.equal(body.fingerprint, 'a'.repeat(64))
      assert.equal(body.decision, 'publish')
      if (forcedReviewStatus) { res.statusCode = forcedReviewStatus; return send({ error: 'untrusted text' }) }
      releaseReview = () => { status = 'published'; send({ id: 1, status }) }
    })
    return
  }
  res.statusCode = 404
  return send({ error: 'synthetic endpoint not found' })
}
const app = await createServer({ root, configFile: false,
  plugins: [react(), { name: 'synthetic-api', configureServer(server) { server.middlewares.use(mockApi) } }],
  cacheDir: path.join(profile, 'vite'), server: { host: '127.0.0.1', port: 0, strictPort: true, hmr: false, ws: false } })
await app.listen()
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu',
  '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send
try {
  let port
  for (let i = 0; i < 100; i++) {
    try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {}
    await delay(100)
  }
  assert(port, 'Chrome did not start')
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', event => {
    const response = JSON.parse(event.data), entry = pending.get(response.id)
    if (!entry) return
    pending.delete(response.id); clearTimeout(entry.timer)
    if (response.error) entry.reject(new Error(JSON.stringify(response.error))); else entry.resolve(response.result)
  })
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const number = ++id, timer = setTimeout(() => reject(new Error(`CDP timeout ${method}`)), 30000)
    pending.set(number, { resolve, reject, timer }); ws.send(JSON.stringify({ id: number, method, params }))
  })
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  const wait = async expression => {
    for (let i = 0; i < 150; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(80) }
    throw new Error(`Timed out: ${expression}`)
  }
  const click = label => evaluate(`Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===${JSON.stringify(label)})?.click()`)
  await send('Page.enable'); await send('Runtime.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: `http://127.0.0.1:${app.httpServer.address().port}/admin/sumber` })
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Lihat Kandidat')")
  assert.equal(await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()==='Lihat Kandidat').getAttribute('aria-label')"), 'Lihat kandidat BPS UJI')
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()==='Lihat Kandidat').focus()")
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' })
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 })
  await wait("document.body.innerText.includes('Inflasi UJI') && document.body.innerText.includes('3.250000')")
  assert(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'narrow viewport must not overflow')
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  await wait("document.body.innerText.includes('Tanggal rilis') && document.body.innerText.includes('Tidak tersedia')")
  assert(await evaluate("document.body.innerText.includes('bukan bukti bahwa angka telah diverifikasi')"), 'missing evidence must not be portrayed as verified')
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false })
  assert(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'desktop viewport must not overflow')
  assert.equal(calls.filter(c => c.method === 'POST').length, 0)
  await click('Setujui untuk publikasi')
  await wait("document.body.innerText.includes('Konfirmasi publikasi kandidat #1')")
  assert(await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()==='Ya, konfirmasi').disabled"), 'publication requires explicit source verification acknowledgement')
  await evaluate("document.querySelector('.candidate-review__confirmation input[type=checkbox]').click()")
  assert.equal(calls.filter(c => c.method === 'POST').length, 0)
  await click('Ya, konfirmasi')
  for (let i = 0; i < 100 && !releaseReview; i++) await delay(30)
  assert(releaseReview, 'review request did not reach mock server')
  assert(await evaluate("Array.from(document.querySelectorAll('.source-card')).find(x=>x.textContent.includes('Sumber lain')).querySelector('button').disabled"), 'source switching must be disabled while review is in flight')
  releaseReview()
  await wait("document.body.innerText.includes('Status kandidat #1 saat diperiksa: published')")
  assert.equal(calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length, 1)
  assert(calls.some(c => c.path === '/api/admin/sources/BPS/candidates/1/' && c.method === 'GET'))
  for (const filter of ['published', 'rejected', 'pending']) {
    await evaluate(`{ const select = Array.from(document.querySelectorAll('select')).find(s => Array.from(s.options).some(o => o.value === 'published')); select.value = ${JSON.stringify(filter)}; select.dispatchEvent(new Event('change', { bubbles: true })); }`)
    await wait(`document.querySelector('section[aria-label="Kandidat BPS"] select').value === ${JSON.stringify(filter)}`)
    assert(await evaluate("document.body.innerText.includes('Kandidat yang menunggu review belum menjadi data publik.')"))
    assert.equal(await evaluate("document.body.innerText.includes('Kandidat belum menjadi data publik.')"), false)
  }
  for (const [code, expected, failDetail] of [
    [409, 'Kandidat berubah atau sudah direview', false],
    [401, 'Sesi Admin tidak tersedia', false],
    [403, 'Review ditolak: periksa izin Admin dan token keamanan', false],
    [503, 'Hasil dan status review belum dapat dipastikan', true],
    [401, 'Sesi Admin tidak tersedia', true],
  ]) {
    // Isolate independent mocked response cases; an uncertain case intentionally retains a marker.
    await click('Tutup kandidat')
    await evaluate('sessionStorage.clear()')
    await click('Lihat Kandidat')
    status = 'pending'; forcedReviewStatus = code; detailFailure = failDetail
    await click('Muat ulang')
    await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
    await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
    await click('Setujui untuk publikasi')
    await evaluate("document.querySelector('.candidate-review__source-check input').click()")
    await click('Ya, konfirmasi')
    await wait(`document.body.innerText.includes(${JSON.stringify(expected)})`)
    await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Muat ulang'&&!b.disabled)")
    if (code === 401 && failDetail) assert(await evaluate("document.body.innerText.includes('Status kandidat belum dapat dimuat ulang')"))
    assert.equal(await evaluate("document.body.innerText.includes('untrusted text')"), false)
  }
  await click('Tutup kandidat')
  await evaluate('sessionStorage.clear()')
  await click('Lihat Kandidat')
  status = 'pending'; forcedReviewStatus = 0; detailFailure = false; releaseReview = undefined
  await click('Muat ulang')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  await click('Setujui untuk publikasi')
  await evaluate("document.querySelector('.candidate-review__source-check input').click()")
  await evaluate("window.__originalTimeout = window.setTimeout; window.setTimeout = (fn, ms, ...args) => window.__originalTimeout(fn, ms === 15000 ? 100 : ms, ...args)")
  const beforePost = calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length
  await click('Ya, konfirmasi')
  await wait("document.body.innerText.includes('Status kandidat #1 saat diperiksa: pending')")
  await wait("document.body.innerText.includes('Status menunggu tidak menjamin proses server sudah selesai')")
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Muat ulang'&&!b.disabled)")
  assert.equal(calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length, beforePost + 1, 'timeout must not retry POST')
  await evaluate('window.setTimeout = window.__originalTimeout')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  assert.equal(await evaluate("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Setujui untuk publikasi')"), false, 'pending readback must not immediately permit another decision')
  assert(await evaluate("document.body.innerText.includes('Keputusan sebelumnya belum pasti')"))
  await click('Tutup kandidat')
  await click('Lihat Kandidat')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  assert(await evaluate("document.body.innerText.includes('Keputusan sebelumnya belum pasti')"), 'warning must survive closing and reopening panel')
  await click('Periksa status kandidat')
  await wait("document.body.innerText.includes('Status saat ini: pending')")
  assert.equal(await evaluate("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Setujui untuk publikasi')"), false, 'pending remains ambiguous after another GET')
  assert.deepEqual(await evaluate("JSON.parse(sessionStorage.getItem('deksi-review-uncertain:BPS'))"), [1], 'only candidate identifier is stored')
  await send('Page.reload')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.getAttribute('aria-label')==='Lihat kandidat BPS UJI'&&!b.disabled)")
  await click('Lihat Kandidat')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  assert(await evaluate("document.body.innerText.includes('Keputusan sebelumnya belum pasti')"), 'warning must survive same-tab page reload')
  assert(await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()==='Izinkan keputusan ulang').disabled"))
  detailFailure = true
  await click('Periksa status kandidat')
  await wait("document.body.innerText.includes('Pemeriksaan tidak membuka keputusan ulang')")
  assert(await evaluate("document.body.innerText.includes('Keputusan sebelumnya belum pasti')"))
  detailFailure = false
  await evaluate("document.querySelector('article[aria-label=\"Detail kandidat 1\"] input[type=checkbox]').focus()")
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, text: ' ' })
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 })
  assert(await evaluate("document.querySelector('article[aria-label=\"Detail kandidat 1\"] input[type=checkbox]').checked"), 'acknowledgement must work with keyboard')
  await click('Izinkan keputusan ulang')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Setujui untuk publikasi')")
  assert.equal(calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length, beforePost + 1, 'recovery check must not send another POST')
  await click('Tutup kandidat')
  await evaluate("sessionStorage.setItem('deksi-review-uncertain:BPS', JSON.stringify([1]))")
  await click('Lihat Kandidat')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  status = 'published'
  await click('Periksa status kandidat')
  await wait("document.body.innerText.includes('Status terminal berhasil dibaca')")
  assert.equal(await evaluate("sessionStorage.getItem('deksi-review-uncertain:BPS')"), null, 'terminal read clears marker')
  await click('Tutup kandidat')
  status = 'pending'; releaseReview = undefined
  await evaluate("window.__originalSetItem = Storage.prototype.setItem; Storage.prototype.setItem = function(k, v) { if (k.startsWith('deksi-review-uncertain:')) throw new Error('synthetic quota'); return window.__originalSetItem.call(this, k, v) }")
  await click('Lihat Kandidat')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  await click('Setujui untuk publikasi')
  await evaluate("document.querySelector('.candidate-review__source-check input').click()")
  const beforeBlockedPost = calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length
  const beforeBlockedCalls = calls.length
  await click('Ya, konfirmasi')
  await delay(200)
  assert.equal(calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length, beforeBlockedPost, 'failed session write must prevent review POST')
  assert.equal(calls.length, beforeBlockedCalls, 'failed session write must also prevent CSRF and readback requests')
  assert(await evaluate("document.body.innerText.includes('Penyimpanan sesi tidak tersedia')"), 'blocked submission must explain how to recover')
  await evaluate('Storage.prototype.setItem = window.__originalSetItem')
  await evaluate("window.__originalGetItem = Storage.prototype.getItem; Storage.prototype.getItem = function(k) { if (k.startsWith('deksi-review-uncertain:')) return null; return window.__originalGetItem.call(this, k) }")
  await click('Ya, konfirmasi')
  await delay(200)
  assert.equal(calls.length, beforeBlockedCalls, 'a failed storage readback must also prevent network requests')
  await evaluate("Storage.prototype.getItem = window.__originalGetItem; sessionStorage.removeItem('deksi-review-uncertain:BPS')")
  await click('Tutup kandidat')
  includeEvidence = true
  await click('Lihat Kandidat')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
  assert(await evaluate("document.body.innerText.includes('Dokumen sintetis') && document.body.innerText.includes('Periode sintetis')"), 'available snapshot evidence should be visible')
  console.log('PASS: synthetic browser flow, explicit confirmation, one POST and exact readback')
} catch (error) {
  console.error(error); console.error('Sanitized synthetic calls:', JSON.stringify(calls))
  if (send) console.error('Browser:', await send('Runtime.evaluate', { expression: 'location.href + " | " + document.body.innerText.slice(0,500)', returnByValue: true }).catch(() => ({})))
  process.exitCode = 1
} finally {
  if (releaseReview && status === 'pending') releaseReview()
  if (send) await send('Browser.close').catch(() => {})
  ws?.close(); chrome.kill(); await app.close(); await delay(500)
  await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 300 })
}
