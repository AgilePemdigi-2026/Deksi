import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-review-e2e-'))
const trace = [], errors = [], browserRequests = [], browserNetworkEvents = [], proxyIncoming = [], proxyOutgoing = []
const requestIds = new WeakMap()
let requestSequence = 0
const requestIdentity = request => {
  if (!requestIds.has(request)) requestIds.set(request, ++requestSequence)
  return { path: request.url.split('?')[0], request: requestIds.get(request), socketPort: request.socket.remotePort }
}
let dropNextReviewResponse = false
let lostPath = ''
const app = await createServer({ root, configFile: false, plugins: [react(), { name: 'observe-review-ingress', configureServer(server) {
  if (process.env.DEKSI_DIAG_CLOSE === '1') server.middlewares.use((_req, res, next) => { res.setHeader('Connection', 'close'); next() })
  server.middlewares.use((req, _res, next) => { if (req.method === 'POST' && req.url.endsWith('/review/')) proxyIncoming.push(requestIdentity(req)); next() })
} }], cacheDir: path.join(profile, 'vite'),
  server: { host: '127.0.0.1', port: 0, strictPort: true, hmr: false, ws: false, proxy: {
    '/api': { target: process.env.DEKSI_TEST_BACKEND, changeOrigin: false, configure(proxy) {
      proxy.on('proxyReq', (_proxyRequest, request) => { if (request.method === 'POST' && request.url.endsWith('/review/')) proxyOutgoing.push(requestIdentity(request)) })
      proxy.on('proxyRes', (response, request, downstream) => {
        trace.push({ method: request.method, path: request.url.split('?')[0], status: response.statusCode })
        if (dropNextReviewResponse && request.method === 'POST' && request.url.endsWith('/review/')) {
          dropNextReviewResponse = false
          response.resume()
          downstream.destroy()
        }
      })
    } },
  } } })
await app.listen()
const netlogPath = path.join(profile, 'netlog.json')
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu',
  '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
  ...(process.env.DEKSI_DIAG_NETLOG === '1' ? [`--log-net-log=${netlogPath}`] : []), 'about:blank'], { stdio: 'ignore' })
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
    const r = JSON.parse(event.data)
    if (r.method === 'Runtime.exceptionThrown') errors.push('uncaught JavaScript exception')
    if (['Network.requestWillBeSentExtraInfo', 'Network.responseReceivedExtraInfo', 'Network.loadingFailed', 'Network.loadingFinished'].includes(r.method)) {
      browserNetworkEvents.push({ event: r.method, id: r.params.requestId, status: r.params.statusCode, error: r.params.errorText })
    }
    if (r.method === 'Network.requestWillBeSent' && r.params.request.method === 'POST' && r.params.request.url.endsWith('/review/')) {
      browserRequests.push({ id: r.params.requestId, path: new URL(r.params.request.url).pathname })
    }
    const entry = pending.get(r.id)
    if (!entry) return
    pending.delete(r.id); clearTimeout(entry.timer)
    if (r.error) entry.reject(new Error(JSON.stringify(r.error))); else entry.resolve(r.result)
  })
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const number = ++id, timer = setTimeout(() => reject(new Error(`CDP timeout ${method}`)), 30000)
    pending.set(number, { resolve, reject, timer }); ws.send(JSON.stringify({ id: number, method, params }))
  })
  const evaluate = async expression => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails))
    return r.result.value
  }
  const wait = async expression => {
    for (let i = 0; i < 200; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(80) }
    throw new Error(`Timed out: ${expression}; page=${await evaluate('document.body.innerText.slice(0,1200)')}`)
  }
  const click = label => evaluate(`(()=>{const b=Array.from(document.querySelectorAll('button')).find(x=>x.textContent.trim()===${JSON.stringify(label)}); if(!b || b.disabled) throw Error('button unavailable'); b.click()})()`)
  const value = (selector, text) => evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)}); const proto=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(e,${JSON.stringify(text)});e.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  const api = expression => evaluate(`(async()=>{${expression}})()`)
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  await send('Page.navigate', { url: `http://127.0.0.1:${app.httpServer.address().port}/admin/sumber-data` })
  await wait('document.querySelector("input[autocomplete=username]")')
  await value('input[autocomplete=username]', process.env.DEKSI_TEST_USER)
  await value('input[type=password]', process.env.DEKSI_TEST_PASS)
  await wait('Array.from(document.querySelectorAll("button")).some(x=>x.textContent.trim()==="Masuk"&&!x.disabled)')
  await click('Masuk')
  await wait('Array.from(document.querySelectorAll(".source-card")).some(x=>x.textContent.includes("Synthetic Review Source"))')
  const before = await api("const r=await fetch('/api/indicators/?code=inflasi'); return (await r.json()).indicators[0].value")
  assert.equal(before, '1')
  await evaluate("Array.from(document.querySelectorAll('.source-card')).find(x=>x.textContent.includes('Synthetic Review Source')).querySelectorAll('button') && Array.from(Array.from(document.querySelectorAll('.source-card')).find(x=>x.textContent.includes('Synthetic Review Source')).querySelectorAll('button')).find(b=>b.textContent.trim()==='Lihat Kandidat').click()")
  await wait("document.body.innerText.includes('SYNTHETIC 1') && document.body.innerText.includes('SYNTHETIC 2')")
  const original = await api("const p='/api/admin/sources/BROWSER_TEST/candidates/'; const items=(await (await fetch(p)).json()).items; return items.find(x=>x.period==='SYNTHETIC 1')")
  const csrfFailure = await api(`const p='/api/admin/sources/BROWSER_TEST/candidates/'; const r=await fetch(p+${original.id}+'/review/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision:'publish',fingerprint:${JSON.stringify(original.fingerprint)},notes:''})}); return r.status`)
  assert.equal(csrfFailure, 403, 'request without CSRF must be rejected')
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('SYNTHETIC 1')).click()")
  await wait("document.body.innerText.includes('Nilai dan satuan') && document.body.innerText.includes('3.250000')")
  assert.match(await evaluate('document.body.innerText'), /Economic Engine[\s\S]*Belum tersedia/)
  assert.match(await evaluate('document.body.innerText'), /Diagnostic flags[\s\S]*tidak diasumsikan aman atau lolos/)
  assert.match(await evaluate('document.body.innerText'), /Narasi Grounded AI[\s\S]*Tidak ada narasi AI/)
  assert.match(await evaluate('document.body.innerText'), /Source Trace dan bukti RAW/)
  await click('Setujui untuk publikasi')
  await wait("document.body.innerText.includes('Konfirmasi publikasi kandidat')")
  await evaluate("document.querySelector('.candidate-review__source-check input').click()")
  await click('Ya, konfirmasi')
  await wait("document.body.innerText.includes('saat diperiksa: published')")
  const after = await api("const r=await fetch('/api/indicators/?code=inflasi'); return (await r.json()).indicators[0].value")
  assert.equal(after, '3.25')
  const duplicate = await api(`const token=(await (await fetch('/api/auth/csrf/')).json()).csrfToken; const p='/api/admin/sources/BROWSER_TEST/candidates/'; const r=await fetch(p+${original.id}+'/review/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({decision:'publish',fingerprint:${JSON.stringify(original.fingerprint)},notes:''})}); return r.status`)
  assert.equal(duplicate, 409, 'an explicit stale review must conflict')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('SYNTHETIC 2'))")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('SYNTHETIC 2')).click()")
  await click('Tolak kandidat')
  await wait("document.querySelector('textarea')")
  await value('textarea', 'Alasan sintetis: tidak sesuai')
  await click('Ya, konfirmasi')
  await wait("document.body.innerText.includes('saat diperiksa: rejected')")
  const afterReject = await api("const r=await fetch('/api/indicators/?code=inflasi'); return (await r.json()).indicators[0].value")
  assert.equal(afterReject, '3.25')
  await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('SYNTHETIC 3'))")
  const third = await api("const p='/api/admin/sources/BROWSER_TEST/candidates/'; const items=(await (await fetch(p)).json()).items; return items.find(x=>x.period==='SYNTHETIC 3')")
  lostPath = `/api/admin/sources/BROWSER_TEST/candidates/${third.id}/review/`
  await evaluate("(()=>{const real=window.fetch;window.__reviewCalls=0;window.fetch=(input,init)=>{if(String(input).endsWith('/review/')&&init?.method==='POST')window.__reviewCalls++;return real(input,init)}})()")
  await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('SYNTHETIC 3')).click()")
  await click('Setujui untuk publikasi')
  await evaluate("document.querySelector('.candidate-review__source-check input').click()")
  dropNextReviewResponse = true
  await click('Ya, konfirmasi')
  await wait("(document.body.innerText.includes('Hasil review belum dapat dipastikan') || document.body.innerText.includes('Kandidat berubah atau sudah direview')) && document.body.innerText.includes('saat diperiksa: published')")
  assert.equal(dropNextReviewResponse, false, 'the synthetic proxy interruption did not trigger')
  const afterLostResponse = await api("const r=await fetch('/api/indicators/?code=inflasi'); return (await r.json()).indicators[0].value")
  assert.equal(afterLostResponse, '4')
  const reviewRequests = trace.filter(x => x.method === 'POST' && x.path.endsWith('/review/'))
  assert.equal(reviewRequests.filter(x => x.status === 200).length, 3)
  assert.equal(reviewRequests.filter(x => x.status === 403).length, 1)
  const lostRequests = reviewRequests.filter(x => x.path.endsWith(`/${third.id}/review/`))
  assert.equal(lostRequests[0]?.status, 200)
  assert(lostRequests.slice(1).every(x => x.status === 409), 'any transport replay must be refused')
  assert.equal(await evaluate('window.__reviewCalls'), 1, 'application must invoke fetch exactly once for the lost response')
  const networkCount = browserRequests.filter(x => x.path.endsWith(`/${third.id}/review/`)).length
  const inbound = proxyIncoming.filter(x => x.path.endsWith(`/${third.id}/review/`))
  const outbound = proxyOutgoing.filter(x => x.path.endsWith(`/${third.id}/review/`))
  const inboundCount = inbound.length
  const outboundCount = outbound.length
  assert.equal(reviewRequests.filter(x => x.status === 409).length, 1 + lostRequests.length - 1)
  assert.equal(trace.filter(x => x.status >= 500).length, 0, 'unexpected backend 5xx')
  assert.deepEqual(errors, [], 'unexpected JS runtime exception')
  await send('Network.clearBrowserCookies')
  await click('Muat ulang')
  await wait("document.body.innerText.includes('Sesi Admin tidak tersedia')")
  assert(trace.some(x => x.path.endsWith('/candidates/') && x.status === 401))
  console.log(`PASS: real browser candidate review; lost response: 1 fetch, ${networkCount} browser events, ${inboundCount} proxy ingress, ${outboundCount} proxy outbound, backend statuses ${lostRequests.map(x => x.status).join(',')}`)
  console.log('Review transport identities:', JSON.stringify({ inbound, outbound }))
  console.log('Browser request events:', JSON.stringify(browserNetworkEvents.filter(x => browserRequests.some(r => r.path.endsWith(`/${third.id}/review/`) && r.id === x.id))))
} catch (error) {
  console.error(error); console.error('Sanitized API trace:', JSON.stringify(trace)); process.exitCode = 1
} finally {
  const chromeExited = new Promise(resolve => chrome.once('exit', resolve))
  if (send) await send('Browser.close').catch(() => {})
  ws?.close(); await Promise.race([chromeExited, delay(3000)]); chrome.kill(); await app.close(); await delay(500)
  if (process.env.DEKSI_DIAG_NETLOG === '1') try {
    const log = JSON.parse(await readFile(netlogPath, 'utf8'))
    const restart = log.constants.logEventTypes.HTTP_TRANSACTION_RESTART_AFTER_ERROR
    const matches = log.events.filter(e => e.type === restart)
    const urlSources = [...new Set(log.events.filter(e => typeof e.params?.url === 'string' && e.params.url.endsWith(lostPath)).map(e => e.source.id))]
    console.log('Browser network transaction restarts:', JSON.stringify(matches.map(e => ({ source: e.source.id, error: e.params?.net_error }))))
    console.log('Browser lost request correlation:', JSON.stringify({ urlSources, matchingRestarts: matches.filter(e => urlSources.includes(e.source.id)).length }))
  } catch { console.log('Browser network transaction restart evidence unavailable') }
  await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 300 })
}
