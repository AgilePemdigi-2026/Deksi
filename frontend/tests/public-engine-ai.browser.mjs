// Real browser interactions with the shipped component; API responses are synthetic, no Gemini calls.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { engineFixture } from './economic-engine-fixtures.mjs'

const scratch = process.env.HERMES_TEST_SCRATCH
const chromePath = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
assert(scratch && path.isAbsolute(scratch) && existsSync(chromePath), 'Existing Chrome and absolute permitted scratch required')
const root = fileURLToPath(new URL('../', import.meta.url))
const owned = await mkdtemp(path.join(scratch, 'deksi-public-ai-browser-'))
const profile = path.join(owned, 'profile')
const packet = engineFixture()
const available = Object.entries(packet.metrics).filter(([, metric]) => metric.available)
const bindings = Object.fromEntries(available.map(([id, metric]) => [id, { inputDigest: metric.inputDigest, resultDigest: metric.resultDigest }]))
const sharedKey = 'deff8cb8-4a5c-4f8f-8e23-5b277165f9c0'
const narrative = { summary: 'SYNTHETIC QA: <img src=x onerror=alert(1)>', meaning: 'Porsi terhadap total PDB, bukan pertumbuhan.', limitations: 'SYNTHETIC QA: belum ada verifikasi independen.', comparison: null, factRefs: available.map(([id]) => `metrics.${id}`) }
const counts = { csrf: 0, post: 0, get: 0 }
const checks = [], errors = [], external = []
let status = 'queued', mismatched = false, completed = false
let chrome, ws, send, vite
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
function respond(res, body, code = 200) { res.statusCode = code; res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(body)) }
try {
  vite = await createServer({ root, configFile: false, plugins: [react(), {
    name: 'synthetic-public-ai-api',
    resolveId(id) { if (id === 'virtual:public-ai-qa') return '\0virtual:public-ai-qa' },
    load(id) {
      if (id === '\0virtual:public-ai-qa') return `import React from 'react';import {createRoot} from 'react-dom/client';import {PublicEngineAIRequest} from '/src/features/dashboard/PublicEngineAIRequest.tsx';import {parseGdp} from '/src/features/dashboard/economicEngineClient.ts';createRoot(document.getElementById('root')).render(React.createElement(PublicEngineAIRequest,{data:parseGdp(${JSON.stringify(packet)})}));`
    },
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const route = req.url?.split('?')[0]
        if (route === '/__qa') {
          res.setHeader('Content-Type', 'text/html')
          const html = '<!doctype html><html><body><div id="root"></div><script type="module" src="/@id/__x00__virtual:public-ai-qa"></script></body></html>'
          res.end(await server.transformIndexHtml('/__qa', html)); return
        }

        if (route === '/api/auth/csrf/') { counts.csrf++; respond(res, { csrfToken: 'synthetic-token' }); return }
        if (route === '/api/public-engine-ai/requests/' && req.method === 'POST') {
          counts.post++
          assert.equal(req.headers['x-csrftoken'], 'synthetic-token')
          let raw = ''; for await (const chunk of req) raw += chunk
          const body = JSON.parse(raw); assert.equal(body.quarter, '2025-03-31')
          assert.match(body.requestKey, /^[a-f0-9-]{36}$/)
          respond(res, { request: { requestKey: sharedKey, status, period: 'Q1 2025' } }); return
        }
        if (route === `/api/public-engine-ai/requests/${sharedKey}/`) {
          counts.get++
          const metricsBinding = structuredClone(bindings)
          if (mismatched) metricsBinding.pmtb_share.resultDigest = 'f'.repeat(64)
          respond(res, { request: { requestKey: sharedKey, status, period: 'Q1 2025',
            ...(status === 'approved' ? { resultDigest: 'a'.repeat(64), metricsBinding, narrative } : {}) } }); return
        }
        if (route?.startsWith('/api/')) { respond(res, { code: 'unhandled_test_route' }, 404); return }
        next()
      })
    },
  }], cacheDir: path.join(owned, 'vite'), optimizeDeps: { include: ['react', 'react-dom/client', 'react/jsx-dev-runtime'] },
    server: { host: '127.0.0.1', port: 0, strictPort: true, proxy: undefined } })
  await vite.listen()
  const origin = `http://127.0.0.1:${vite.httpServer.address().port}`
  chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let port
  for (let i = 0; i < 100; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await delay(100) }
  assert(port, 'Disposable Chrome did not start')
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0; const pending = new Map()
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const sequence = ++id, timer = setTimeout(() => { pending.delete(sequence); reject(new Error('CDP timeout ' + method)) }, 10000)
    pending.set(sequence, { resolve, reject, timer }); ws.send(JSON.stringify({ id: sequence, method, params }))
  })
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text)
    if (message.method === 'Fetch.requestPaused') {
      const request = message.params, allowed = new URL(request.request.url).origin === origin
      if (!allowed) external.push(request.request.url)
      void send(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', { requestId: request.requestId, ...(!allowed ? { errorReason: 'BlockedByClient' } : {}) }).catch(() => {})
    }
    const item = pending.get(message.id); if (!item) return
    clearTimeout(item.timer); pending.delete(message.id)
    if (message.error) item.reject(new Error(JSON.stringify(message.error))); else item.resolve(message.result)
  })
  const js = async expression => { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value }
  const wait = async expression => { for (let i = 0; i < 100; i++) { if (await js(`Boolean(${expression})`)) return; await delay(75) } throw new Error('Condition timed out: ' + expression) }
  const click = async text => {
    const box = await js(`(() => {const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)}));if(!b)throw Error('Missing button');b.scrollIntoView();const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`)
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...box, button: 'left', clickCount: 1 }); await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...box, button: 'left', clickCount: 1 })
  }
  await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: 'http*' }] })
  await send('Page.navigate', { url: origin + '/__qa' })
  await wait('document.body.innerText.includes("Lihat penjelasan sederhana")')
  assert.deepEqual(counts, { csrf: 0, post: 0, get: 0 }); checks.push('No API or generation on mount')
  await click('Lihat penjelasan sederhana'); await wait('document.body.innerText.includes("Menunggu antrean")')
  assert.equal(counts.post, 1); checks.push('Pointer click queues once and accepts canonical shared UUID')
  status = 'ready'; await click('Periksa status tersimpan'); await wait('document.body.innerText.includes("Menunggu review Admin")')
  assert(!await js('document.body.innerText.includes("SYNTHETIC QA:")')); checks.push('Pending human review hides draft text')
  status = 'approved'; await click('Periksa status tersimpan'); await wait('document.body.innerText.includes("SYNTHETIC QA:")')
  assert.equal(await js('document.querySelectorAll("img,script[src=x]").length'), 0)
  assert.equal(counts.post, 1); checks.push('Approved matching response displayed as escaped text; retries only GET')
  await send('Page.navigate', { url: origin + '/__qa' }); await wait('document.body.innerText.includes("Lihat penjelasan sederhana")')
  await click('Lihat penjelasan sederhana'); await wait('document.body.innerText.includes("SYNTHETIC QA:")')
  assert.equal(counts.post, 2); checks.push('Second reader opens approved shared content with one click')
  mismatched = true
  await send('Page.navigate', { url: origin + '/__qa' }); await wait('document.body.innerText.includes("Lihat penjelasan sederhana")')
  await click('Lihat penjelasan sederhana'); await wait('document.body.innerText.includes("Status persetujuan diterima")')
  assert(!await js('document.body.innerText.includes("SYNTHETIC QA:")')); checks.push('Same-period mismatched result identity fails closed')
  assert.deepEqual(errors, []); assert.deepEqual(external, []); completed = true
  console.log(JSON.stringify({ completed, syntheticApi: true, checks, counts, providerCalls: 0 }))
} finally {
  await writeFile(path.join(owned, 'receipt.json'), JSON.stringify({ completed, syntheticApi: true, checks, counts, errors, external, providerCalls: 0 }, null, 2))
  if (ws?.readyState === WebSocket.OPEN) { try { await send('Browser.close') } catch {} ws.close() }
  if (chrome && chrome.exitCode === null) { await Promise.race([new Promise(resolve => chrome.once('exit', resolve)), delay(2000)]); if (chrome.exitCode === null) chrome.kill() }
  if (vite) await vite.close()
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 250 })
  console.log('Browser receipt: ' + path.join(owned, 'receipt.json'))
}
