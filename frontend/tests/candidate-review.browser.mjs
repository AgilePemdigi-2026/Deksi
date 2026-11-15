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
const candidate = () => ({ id: 1, fingerprint: 'a'.repeat(64), indicator: 'inflasi', indicatorName: 'Inflasi UJI',
  sourceId: 'BPS', sourceName: 'BPS UJI', sourceUrl: 'https://example.test/', period: 'UJI 2024',
  observationDate: '2024-01-31', publicationDate: null, frequency: 'monthly', dataType: 'yoy',
  value: '3.250000', unit: '%', rawFileId: null, status, createdAt: '2024-02-01T00:00:00Z',
  reviewedAt: status === 'published' ? '2024-02-02T00:00:00Z' : null, reviewedBy: status === 'published' ? 'UJI' : null, reviewNotes: '' })
const mockApi = (req, res, next) => {
  if (!req.url.startsWith('/api/')) return next()
  calls.push({ method: req.method, path: req.url.split('?')[0] })
  res.setHeader('Content-Type', 'application/json')
  const route = req.url.split('?')[0]
  const send = body => res.end(JSON.stringify(body))
  if (route === '/api/admin/session/') return send({ authenticated: true, username: 'UJI' })
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
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false })
  assert(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'desktop viewport must not overflow')
  assert.equal(calls.filter(c => c.method === 'POST').length, 0)
  await click('Setujui untuk publikasi')
  await wait("document.body.innerText.includes('Konfirmasi publikasi kandidat #1')")
  assert.equal(calls.filter(c => c.method === 'POST').length, 0)
  await click('Ya, konfirmasi')
  for (let i = 0; i < 100 && !releaseReview; i++) await delay(30)
  assert(releaseReview, 'review request did not reach mock server')
  assert(await evaluate("Array.from(document.querySelectorAll('.source-card')).find(x=>x.textContent.includes('Sumber lain')).querySelector('button').disabled"), 'source switching must be disabled while review is in flight')
  releaseReview()
  await wait("document.body.innerText.includes('Status kandidat #1 saat diperiksa: published')")
  assert.equal(calls.filter(c => c.path.endsWith('/review/') && c.method === 'POST').length, 1)
  assert(calls.some(c => c.path === '/api/admin/sources/BPS/candidates/1/' && c.method === 'GET'))
  for (const [code, expected, failDetail] of [
    [409, 'Kandidat berubah atau sudah direview', false],
    [401, 'Sesi Admin tidak tersedia', false],
    [403, 'Review ditolak: periksa izin Admin dan token keamanan', false],
    [503, 'Hasil dan status review belum dapat dipastikan', true],
    [401, 'Sesi Admin tidak tersedia', true],
  ]) {
    status = 'pending'; forcedReviewStatus = code; detailFailure = failDetail
    await click('Muat ulang')
    await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Inflasi UJI'))")
    await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Inflasi UJI')).click()")
    await click('Setujui untuk publikasi')
    await click('Ya, konfirmasi')
    await wait(`document.body.innerText.includes(${JSON.stringify(expected)})`)
    await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Muat ulang'&&!b.disabled)")
    if (code === 401 && failDetail) assert(await evaluate("document.body.innerText.includes('Status kandidat belum dapat dimuat ulang')"))
    assert.equal(await evaluate("document.body.innerText.includes('untrusted text')"), false)
  }
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
