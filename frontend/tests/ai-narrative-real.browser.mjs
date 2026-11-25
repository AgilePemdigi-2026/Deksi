import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const scratch = process.env.HERMES_TEST_SCRATCH
const backend = process.env.DEKSI_AI_TEST_BACKEND
assert(scratch && /^http:\/\/127\.0\.0\.1:\d+$/.test(backend || ''), 'Owned backend and scratch required')
const profile = await mkdtemp(path.join(scratch, 'deksi-ai-real-browser-'))
const app = await createServer({ configFile: false, root: process.cwd(), envDir: profile,
  cacheDir: path.join(profile, 'vite'), plugins: [react()], server: { host: '127.0.0.1', port: 0,
    strictPort: true, hmr: false, ws: false, proxy: { '/api/': { target: backend, changeOrigin: false } } } })
await app.listen()
const origin = `http://127.0.0.1:${app.httpServer.address().port}`
const chrome = spawn(process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  ['--headless=new', '--no-first-run', '--disable-background-networking', '--disable-component-update',
    '--disable-sync', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send, holdReview = false, holdDetail = false, heldReview, heldDetail
let failReview = false, failNextDetail = false, failedDetail = false
const responses = [], blocked = [], exceptions = [], writes = []
try {
  let port
  for (let i = 0; i < 100; i++) {
    try { const lines = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n'); if (lines[1]?.startsWith('/devtools/')) { port = Number(lines[0]); break } } catch {}
    await delay(80)
  }
  assert(port, 'Owned Chrome did not become ready')
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map()
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id, timer = setTimeout(() => { pending.delete(n); reject(new Error(`CDP deadline ${method}`)) }, 25000)
    pending.set(n, { resolve, reject, timer }); ws.send(JSON.stringify({ id: n, method, params }))
  })
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text)
    if (message.method === 'Network.responseReceived' && new URL(message.params.response.url).pathname.startsWith('/api/')) responses.push(message.params.response.status)
    if (message.method === 'Fetch.requestPaused') {
      const { requestId, request, responseStatusCode } = message.params
      const url = new URL(request.url)
      if (responseStatusCode) {
        if (holdReview && url.pathname.endsWith('/review/')) { heldReview = requestId; return }
        send('Fetch.continueResponse', { requestId }).catch(() => {}); return
      }
      const allowedWrite = /^\/api\/(auth\/login\/|admin\/ai-narratives\/(?:\d+\/(?:review|reconcile)\/)?)$/.test(url.pathname) || url.pathname === '/api/__ai-fixture/control/'
      const allowed = url.origin === origin && (['GET', 'HEAD'].includes(request.method) || (request.method === 'POST' && allowedWrite))
      if (!allowed) blocked.push({ path: url.pathname, method: request.method })
      if (allowed && request.method === 'POST') writes.push(url.pathname)
      if (allowed && failReview && url.pathname.endsWith('/review/')) {
        failReview = false; failNextDetail = true
        send('Fetch.failRequest', { requestId, errorReason: 'ConnectionClosed' }).catch(() => {}); return
      }
      if (allowed && failNextDetail && /^\/api\/admin\/ai-narratives\/\d+\/$/.test(url.pathname)) {
        failNextDetail = false; failedDetail = true
        send('Fetch.failRequest', { requestId, errorReason: 'ConnectionClosed' }).catch(() => {}); return
      }
      if (allowed && holdDetail && /^\/api\/admin\/ai-narratives\/\d+\/$/.test(url.pathname)) { heldDetail = requestId; return }
      send(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', allowed ? { requestId } : { requestId, errorReason: 'BlockedByClient' }).catch(() => {})
      return
    }
    if (!message.id) return
    const task = pending.get(message.id)
    if (!task) return
    pending.delete(message.id); clearTimeout(task.timer)
    if (message.error) task.reject(new Error(JSON.stringify(message.error))); else task.resolve(message.result)
  })
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text)
    return result.result.value
  }
  const wait = async (expression, label) => {
    for (let i = 0; i < 180; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(80) }
    throw new Error(`UI deadline: ${label}`)
  }
  const click = label => evaluate(`(()=>{const b=Array.from(document.querySelectorAll('.ai-narratives button')).find(x=>x.textContent===${JSON.stringify(label)});if(!b||b.disabled)throw new Error('Button unavailable');b.click()})()`)
  const control = mode => evaluate(`(async()=>{const token=(await(await fetch('/api/auth/csrf/')).json()).csrfToken;const r=await fetch('/api/__ai-fixture/control/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({mode:${JSON.stringify(mode)}})});if(!r.ok)throw new Error('Fixture operation failed');return r.json()})()`)
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  await send('Fetch.enable', { patterns: [{ urlPattern: '*', requestStage: 'Request' }, { urlPattern: origin + '/api/admin/ai-narratives/*/review/', requestStage: 'Response' }] })
  await send('Page.navigate', { url: origin + '/admin/login' })
  await wait('document.querySelector("main")', 'frontend mount')
  const authenticated = await evaluate(`(async()=>{const token=(await(await fetch('/api/auth/csrf/')).json()).csrfToken;const r=await fetch('/api/auth/login/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({identifier:'ai-browser-synthetic',password:${JSON.stringify(process.env.DEKSI_AI_BROWSER_PASSWORD)}})});return r.ok})()`)
  assert(authenticated, 'Synthetic account real session login failed')
  await send('Page.navigate', { url: origin + '/admin/analisis' })
  await wait('document.querySelector(".ai-narratives select")?.options.length>1', 'real observation options')
  assert.equal((await control('counts')).drafts, 0, 'opening page must not generate a request')
  await evaluate(`(()=>{const s=document.querySelector('.ai-narratives select');s.value=s.options[1].value;s.dispatchEvent(new Event('change',{bubbles:true}))})()`)
  await click('Minta draft')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Dalam antrean")', 'queued snapshot readback')
  let counts = await control('counts')
  assert.equal(counts.calls, 0); assert.equal(counts.drafts, 1); assert.equal(counts.value, '5.123456')
  await control('process'); await click('Muat ulang')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Draft siap")', 'refresh must update selected detail')
  assert.match(await evaluate('document.querySelector(".ai-narratives__detail").textContent'), /belum diperiksa secara independen/)
  await click('Setujui draft — belum tampil publik')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Disetujui — belum tampil publik")', 'exact review readback')
  counts = await control('counts')
  assert.equal(counts.calls, 1); assert.equal(counts.reviews, 1); assert.equal(counts.value, '5.123456')
  const before = await evaluate('performance.timeOrigin')
  await send('Page.reload')
  await wait(`performance.timeOrigin!==${before} && document.querySelector('.ai-narratives__list button')`, 'persisted history after reload')
  await evaluate(`document.querySelector('.ai-narratives__list button').click()`)
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Disetujui — belum tampil publik")', 'stored decision remains')
  await click('Gunakan ID fakta ini untuk revisi baru'); await click('Minta draft')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Dalam antrean")', 'new revision queued')
  await control('process'); await click('Muat ulang')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Draft siap") && document.querySelector(".ai-narratives__detail")?.textContent.includes("Menunggu review")', 'new revision needs its own review')
  holdReview = true
  await click('Setujui draft — belum tampil publik')
  for (let i = 0; i < 150 && !heldReview; i++) await delay(60)
  assert(heldReview, 'Review response must actually be held after server execution')
  assert.equal(await evaluate('Boolean(document.querySelector(".admin-analysis nav")?.closest("[inert]"))'), true, 'navigation blocked during review mutation')
  holdDetail = true; holdReview = false
  await send('Fetch.failRequest', { requestId: heldReview, errorReason: 'ConnectionClosed' })
  for (let i = 0; i < 150 && !heldDetail; i++) await delay(60)
  assert(heldDetail, 'UI must read back the exact committed draft after the response is lost')
  assert.equal(await evaluate('Boolean(document.querySelector(".admin-analysis nav")?.closest("[inert]"))'), true, 'navigation stays blocked during decision readback')
  holdDetail = false
  await send('Fetch.continueRequest', { requestId: heldDetail })
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Disetujui — belum tampil publik")', 'lost-response decision confirmed')
  counts = await control('counts')
  assert.equal(counts.reviews, 2); assert.equal(counts.calls, 2); assert.equal(counts.value, '5.123456')
  assert.equal(writes.filter(route => route.endsWith('/review/')).length, 2, 'no automatic review replay')
  await click('Gunakan ID fakta ini untuk revisi baru'); await click('Minta draft')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Dalam antrean")', 'third revision queued')
  await control('process'); await click('Muat ulang')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Draft siap") && document.querySelector(".ai-narratives__detail")?.textContent.includes("Menunggu review")', 'third draft ready')
  failReview = true
  await click('Setujui draft — belum tampil publik')
  for (let i = 0; i < 150 && !failedDetail; i++) await delay(60)
  assert(failedDetail, 'Both mutation and outcome readback must actually fail')
  await wait('document.querySelector(".ai-narratives__message")?.textContent.includes("belum dapat dipastikan")', 'uncertain decision warning')
  await delay(100)
  assert.equal(await evaluate('Boolean(document.querySelector(".admin-analysis nav")?.closest("[inert]"))'), true, 'uncertain review keeps related navigation locked')
  await click('Periksa keputusan lagi')
  assert.equal(await evaluate('Boolean(document.querySelector(".admin-analysis nav")?.closest("[inert]"))'), true, 'pending readback is not proof the server stopped')
  await evaluate(`(async()=>{const d=(await(await fetch('/api/admin/ai-narratives/3/')).json()).draft;const token=(await(await fetch('/api/auth/csrf/')).json()).csrfToken;const r=await fetch('/api/admin/ai-narratives/3/review/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({contentDigest:d.contentDigest,decision:'approved',notes:''})});if(!r.ok)throw new Error('Synthetic operator decision failed')})()`)
  await click('Periksa keputusan lagi')
  await wait('document.querySelector(".ai-narratives__detail")?.textContent.includes("Disetujui — belum tampil publik")', 'uncertain decision recovered by exact readback')
  counts = await control('counts')
  assert.equal(counts.reviews, 3); assert.equal(counts.calls, 3); assert.equal(counts.value, '5.123456')
  assert.equal(exceptions.length, 0, JSON.stringify(exceptions))
  assert.equal(responses.filter(status => status >= 500).length, 0, 'unexpected backend 5xx')
  assert.deepEqual(blocked, [], 'unexpected network or mutation')
  console.log('PASS: real browser + Django + disposable database; queued -> synthetic HTTP completion -> exact review; reload; new revision; lost response readback; protected navigation; no public value change. No live LLM or human language acceptance.')
} catch (error) { console.error(error); process.exitCode = 1 }
finally {
  if (send) await send('Browser.close').catch(() => {})
  ws?.close(); chrome.kill(); await app.close(); await delay(400)
  await rm(profile, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 })
}
