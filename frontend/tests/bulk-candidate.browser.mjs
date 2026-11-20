import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch, 'Set HERMES_TEST_SCRATCH to the agent-owned scratch directory')
const profile = await mkdtemp(path.join(scratch, 'deksi-bulk-browser-'))
const batchId = 'a0000000-0000-4000-8000-000000000001'
const candidate = id => ({ id, fingerprint: 'a'.repeat(64), indicator: 'uji', indicatorName: 'Indikator Uji',
  sourceId: 'BPS', sourceName: 'BPS sintetis', sourceUrl: 'https://example.test/', period: `Periode ${id}`,
  observationDate: '2024-01-01', publicationDate: null,
  frequency: 'monthly', dataType: 'level', value: `${id}.000000`, unit: '%', rawFileId: id === 21 ? 9 : null,
  previousValue: null, previousUnit: null, previousPeriod: null, status: 'pending', createdAt: '2024-02-01T00:00:00Z',
  reviewedAt: null, reviewedBy: null, reviewNotes: '', rawEvidence: id === 21 ? {
    documentName: 'Dokumen Uji', periodLabel: 'Januari 2024', retrievedAt: '2024-02-01T00:00:00Z',
    checksumSha256: 'c'.repeat(64) } : null })
const preview = { id: batchId, status: 'preview', expiresAt: '2099-01-01T00:00:00Z', total: 21, eligible: 1, excluded: 20,
  items: Array.from({ length: 21 }, (_, i) => ({ ...candidate(i + 1), eligible: i === 20,
    exclusionReason: i === 20 ? null : 'raw_file_unavailable' })) }
const counts = { total: 21, eligible: 1, excluded: 20, published: 1, skipped: 0, pending: 0, unknown: 0 }
const result = { id: batchId, status: 'completed', counts, items: preview.items.map(item => ({ id: item.id,
  status: item.eligible ? 'published' : 'excluded', reason: item.exclusionReason })) }
const running = { ...result, status: 'running', counts: { ...counts, published: 0, pending: 1 },
  items: result.items.map(item => item.id === 21 ? { ...item, status: 'pending' } : item) }
const reconciledResult = { ...running, status: 'unknown', resolvedAt: '2026-11-17T15:00:00Z',
  resolvedBy: 'UJI', resolutionReason: 'Diperiksa manual',
  counts: { ...running.counts, pending: 0, unknown: 1 },
  items: running.items.map(item => item.id === 21 ? { ...item, status: 'unknown' } : item) }
let postCount = 0
let releaseConfirm
let submitted = false
let unresolved = false
let reconciled = false
let recoveryCount = 0
const mockApi = (req, res, next) => {
  if (!req.url.startsWith('/api/')) return next()
  res.setHeader('Content-Type', 'application/json')
  const route = req.url.split('?')[0]
  const send = body => res.end(JSON.stringify(body))
  if (route === '/api/admin/session/') return send({ authenticated: true, username: 'UJI', isStaff: true, canReviewCandidates: true })
  if (route === '/api/admin/sources/acquisition-methods/') return send({ methods: [], frequencies: [] })
  if (route === '/api/admin/sources/') return send({ sources: [{ sourceId: 'BPS', sourceName: 'BPS sintetis',
    institution: 'Sintetis', status: 'active', acquisitionMethod: 'api_bps', dataFormat: 'json', frequency: 'mixed', lastFetch: {} }] })
  if (route === '/api/admin/sources/BPS/resync-active/') return send({ job: null })
  if (route === '/api/auth/csrf/') return send({ csrfToken: 'synthetic-token' })
  if (route === '/api/admin/sources/BPS/candidates/bulk-review/active/') return send({ batch:
    unresolved ? (reconciled ? reconciledResult : running) : submitted ? result : null })
  if (route === '/api/admin/sources/BPS/candidates/bulk-preview/' && req.method === 'POST') {
    assert.equal(req.headers['x-csrftoken'], 'synthetic-token'); return send(preview)
  }
  if (route === `/api/admin/sources/BPS/candidates/bulk-review/${batchId}/` && req.method === 'GET') return send(
    unresolved ? (reconciled ? reconciledResult : running) : result)
  if (route === `/api/admin/sources/BPS/candidates/bulk-review/${batchId}/reconcile/` && req.method === 'POST') {
    assert.equal(req.headers['x-csrftoken'], 'synthetic-token')
    let body = ''; req.on('data', chunk => { body += chunk }); req.on('end', () => {
      assert.deepEqual(JSON.parse(body), { acknowledged: true, reason: 'Diperiksa manual' })
      recoveryCount++; reconciled = true; send(reconciledResult)
    }); return
  }
  if (route === `/api/admin/sources/BPS/candidates/bulk-review/${batchId}/confirm/` && req.method === 'POST') {
    assert.equal(req.headers['x-csrftoken'], 'synthetic-token')
    let body = ''; req.on('data', chunk => { body += chunk }); req.on('end', () => {
      assert.deepEqual(JSON.parse(body), { confirmed: true }); postCount++; releaseConfirm = () => { submitted = true; send(result) }
    }); return
  }
  if (route === '/api/admin/sources/BPS/candidates/') {
    const query = new URL(req.url, 'http://localhost').searchParams
    const items = query.get('status') === 'pending' ? [candidate(Number(query.get('page')))] : []
    return send({ items, page: Number(query.get('page')), pageSize: 20, total: 21, hasNext: query.get('page') === '1' })
  }
  res.statusCode = 404; return send({ error: 'not mocked' })
}
const app = await createServer({ root: path.resolve('.'), configFile: false,
  plugins: [react(), { name: 'synthetic-api', configureServer(server) { server.middlewares.use(mockApi) } }],
  cacheDir: path.join(profile, 'vite'), server: { host: '127.0.0.1', port: 0, strictPort: true, hmr: false, ws: false } })
await app.listen()
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu',
  '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws
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
  let seq = 0; const pending = new Map()
  ws.addEventListener('message', event => {
    const response = JSON.parse(event.data), entry = pending.get(response.id)
    if (!entry) return
    pending.delete(response.id); clearTimeout(entry.timer)
    if (response.error) entry.reject(new Error(JSON.stringify(response.error))); else entry.resolve(response.result)
  })
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq, timer = setTimeout(() => reject(new Error(`CDP timeout ${method}`)), 30000)
    pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params }))
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
  const button = label => `Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===${JSON.stringify(label)})`
  await send('Page.enable'); await send('Runtime.enable')
  await send('Page.navigate', { url: `http://127.0.0.1:${app.httpServer.address().port}/admin/sumber` })
  await wait(button('Lihat Kandidat'))
  await evaluate(`${button('Lihat Kandidat')}.click()`)
  await wait(`${button('Pratinjau kandidat yang memenuhi syarat')} && !${button('Pratinjau kandidat yang memenuhi syarat')}.disabled`)
  await evaluate(`${button('Pratinjau kandidat yang memenuhi syarat')}.click()`)
  await wait("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Total pending: 21')")
  assert.equal(await evaluate("document.querySelectorAll('.candidate-review__bulk-preview li').length"), 21)
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Dokumen Uji')"), true)
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Tanggal rilis: Tidak tersedia')"), true)
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Tanggal observasi: 2024-01-01')"), true)
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-preview [role=alert]')?.textContent.includes('Tanggal observasi bukan tanggal rilis')"), true)
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Dikecualikan: 20')"), true)
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Berkas bukti tidak tersedia')"), true)
  assert.equal(await evaluate(`${button('Setujui semua kandidat yang memenuhi syarat')}.disabled`), true)
  await evaluate("document.querySelector('.candidate-review__bulk-preview input[type=checkbox]').click()")
  await evaluate(`${button('Setujui semua kandidat yang memenuhi syarat')}.click()`)
  await wait('Boolean(document.querySelector(".candidate-review__bulk-preview button:disabled")) && Boolean(' + button('Tutup kandidat') + '?.disabled)')
  await evaluate(`${button('Setujui semua kandidat yang memenuhi syarat')}.click()`)
  assert.equal(postCount, 1, 'second click cannot replay the write')
  releaseConfirm()
  await wait("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('berhasil 1')")
  assert.equal(await evaluate("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('#21 · published')"), true)
  assert.equal(postCount, 1)
  unresolved = true
  await send('Page.reload', { ignoreCache: true })
  await wait(button('Lihat Kandidat'))
  await evaluate(`${button('Lihat Kandidat')}.click()`)
  await wait("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('Operasi running')")
  assert.equal(await evaluate(`${button('Pratinjau kandidat yang memenuhi syarat')}.disabled`), true)
  await wait(button('Tutup operasi setelah pemeriksaan manual'))
  assert.equal(await evaluate(`${button('Tutup operasi setelah pemeriksaan manual')}.disabled`), true)
  await evaluate("(()=>{const e=document.querySelector('.candidate-review__bulk-reconcile input[type=text]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'Diperiksa manual');e.dispatchEvent(new Event('input',{bubbles:true}))})()")
  await evaluate("document.querySelector('.candidate-review__bulk-reconcile input[type=checkbox]').click()")
  await wait(`${button('Tutup operasi setelah pemeriksaan manual')} && !${button('Tutup operasi setelah pemeriksaan manual')}.disabled`)
  await evaluate(`${button('Tutup operasi setelah pemeriksaan manual')}.click()`)
  await wait("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('Ditinjau UJI')")
  assert.equal(recoveryCount, 1)
  assert.equal(postCount, 1, 'manual reconciliation does not repeat approval')
  assert.equal(await evaluate(`${button('Pratinjau kandidat yang memenuhi syarat')}.disabled`), false)
  console.log('synthetic browser: preview 21 across pages, 20 excluded, one confirmed, readback displayed')
} finally {
  if (ws) ws.close()
  chrome.kill()
  await app.close()
  await delay(250)
  await rm(profile, { recursive: true, force: true, maxRetries: 8, retryDelay: 200 })
}
