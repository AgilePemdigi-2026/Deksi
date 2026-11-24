import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch && process.env.DEKSI_TEST_BACKEND, 'Explicit owned scratch and Django LiveServer are required')
const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(scratch, 'deksi-bulk-real-e2e-'))
let dropped = false
const trace = []
const app = await createServer({ root, configFile: false, plugins: [react()],
  cacheDir: path.join(profile, 'vite'),
  server: { host: '127.0.0.1', port: 0, strictPort: true, hmr: false, ws: false, proxy: {
    '/api': { target: process.env.DEKSI_TEST_BACKEND, changeOrigin: false, configure(proxy) {
      proxy.on('proxyRes', (response, request, downstream) => {
        const route = request.url.split('?')[0]
        trace.push({ method: request.method, path: route, status: response.statusCode })
        if (!dropped && route.endsWith('/confirm/') && request.method === 'POST' && response.statusCode === 200) {
          dropped = true
          response.resume()
          downstream.destroy()
        }
      })
    } },
  } } })
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new',
  '--disable-gpu', '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'],
{ stdio: 'ignore' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send
try {
  await app.listen()
  let port
  for (let i = 0; i < 100; i++) {
    try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {}
    await delay(100)
  }
  assert(port, 'Disposable Chrome did not start')
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let seq = 0
  const pending = new Map()
  ws.addEventListener('message', event => {
    const result = JSON.parse(event.data), entry = pending.get(result.id)
    if (!entry) return
    pending.delete(result.id); clearTimeout(entry.timer)
    if (result.error) entry.reject(new Error(JSON.stringify(result.error))); else entry.resolve(result.result)
  })
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq, timer = setTimeout(() => reject(new Error(`CDP timeout: ${method}`)), 30000)
    pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params }))
  })
  const evaluate = async expression => {
    const response = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails))
    return response.result.value
  }
  const wait = async expression => {
    for (let i = 0; i < 180; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(100) }
    throw new Error(`Timed out waiting for ${expression}; page=${await evaluate('document.body.innerText.slice(0,900)')}`)
  }
  const button = label => `Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===${JSON.stringify(label)})`
  const fill = (selector, value) => evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  await send('Page.enable'); await send('Runtime.enable')
  const frontend = `http://127.0.0.1:${app.httpServer.address().port}`
  await send('Page.navigate', { url: `${frontend}/admin/sumber-data` })
  await wait('document.querySelector("input[autocomplete=username]")')
  await fill('input[autocomplete=username]', process.env.DEKSI_TEST_USER)
  await fill('input[type=password]', process.env.DEKSI_TEST_PASS)
  await wait(`${button('Masuk')} && !${button('Masuk')}.disabled`)
  await evaluate(`${button('Masuk')}.click()`)
  await wait("Array.from(document.querySelectorAll('.source-card')).some(e=>e.textContent.includes('Synthetic Bulk Source'))")
  await evaluate("Array.from(document.querySelectorAll('.source-card')).find(e=>e.textContent.includes('Synthetic Bulk Source')).querySelector('button[aria-label^=\"Lihat kandidat\"]').click()")
  await wait(`${button('Pratinjau kandidat yang memenuhi syarat')} && !${button('Pratinjau kandidat yang memenuhi syarat')}.disabled`)
  await evaluate(`${button('Pratinjau kandidat yang memenuhi syarat')}.click()`)
  await wait("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Total pending: 22')")
  assert.equal(await evaluate("document.querySelectorAll('.candidate-review__bulk-preview li').length"), 22)
  assert(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('Memenuhi syarat: 1. Dikecualikan: 21')"))
  assert(await evaluate("document.querySelector('.candidate-review__bulk-preview')?.textContent.includes('RAW UJI 21')"))
  assert.equal(await evaluate(`${button('Setujui semua kandidat yang memenuhi syarat')}.disabled`), true)
  const noCsrf = await evaluate("(async()=>{const r=await fetch('/api/admin/sources/BULK_TEST/candidates/bulk-preview/',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});return r.status})()")
  assert.equal(noCsrf, 403)
  await evaluate("document.querySelector('.candidate-review__bulk-preview input[type=checkbox]').click()")
  await evaluate("(()=>{const real=window.fetch;window.__bulkWrites=0;window.fetch=(url,init)=>{if(String(url).endsWith('/confirm/')&&init?.method==='POST')window.__bulkWrites++;return real(url,init)}})()")
  await evaluate(`${button('Setujui semua kandidat yang memenuhi syarat')}.click()`)
  await wait('window.__bulkWrites===1')
  for (let i = 0; i < 100 && !dropped; i++) await delay(50)
  assert(dropped, 'synthetic proxy response drop did not occur')
  if (await evaluate("!document.querySelector('.candidate-review__bulk-result')")) {
    await wait("Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()==='Periksa status operasi')")
    await evaluate(`${button('Periksa status operasi')}.click()`)
  }
  await wait("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('berhasil 1')")
  assert.equal(await evaluate('window.__bulkWrites'), 1, 'application must not replay confirmation')
  assert(dropped, 'synthetic proxy response drop did not occur')
  assert(await evaluate("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('dikecualikan 21')"))
  await send('Page.reload', { ignoreCache: true })
  await wait("Array.from(document.querySelectorAll('.source-card')).some(e=>e.textContent.includes('Synthetic Bulk Source'))")
  await evaluate("Array.from(document.querySelectorAll('.source-card')).find(e=>e.textContent.includes('Synthetic Bulk Source')).querySelector('button[aria-label^=\"Lihat kandidat\"]').click()")
  await wait("document.querySelector('.candidate-review__bulk-result')?.textContent.includes('berhasil 1')")
  assert.equal(trace.filter(x => x.path.endsWith('/confirm/') && x.status === 200).length >= 1, true)
  assert.equal(trace.filter(x => x.status >= 500).length, 0, 'unexpected backend 5xx')
  console.log('PASS: real browser bulk review; 22 pending, 21 excluded, lost response readback and reload')
} finally {
  const exited = new Promise(resolve => chrome.once('exit', resolve))
  if (send) await send('Browser.close').catch(() => {})
  ws?.close()
  await Promise.race([exited, delay(3000)])
  chrome.kill()
  await app.close()
  await delay(300)
  await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 200 })
}
