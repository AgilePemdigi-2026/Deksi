import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-resync-e2e-'))
const trace = []
const app = await createServer({ root, configFile: false, plugins: [react()], cacheDir: process.env.DEKSI_TEST_CACHE,
  server: { host: '127.0.0.1', port: 0, strictPort: true, proxy: { '/api': { target: process.env.DEKSI_TEST_BACKEND, changeOrigin: false,
    configure(proxy) { proxy.on('proxyRes', (response, request) => trace.push({ method: request.method, path: request.url.split('?')[0], status: response.statusCode })) } } } } })
await app.listen()
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send
try {
  let port
  for (let i = 0; i < 100; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await delay(100) }
  assert(port, 'Chrome did not start')
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let sequence = 0; const pending = new Map()
  ws.addEventListener('message', event => { const r = JSON.parse(event.data); if (!r.id) return; const p = pending.get(r.id); if (!p) return; pending.delete(r.id); clearTimeout(p.timer); r.error ? p.reject(new Error(JSON.stringify(r.error))) : p.resolve(r.result) })
  send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; const timer = setTimeout(() => reject(new Error('CDP timeout ' + method)), 30000); pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params })) })
  const evaluate = async expression => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value }
  const wait = async expression => { for (let i = 0; i < 300; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(100) } throw new Error('Timeout: ' + expression + '; page=' + await evaluate('document.body.innerText')) }
  const origin = `http://127.0.0.1:${app.httpServer.address().port}`
  await send('Page.enable'); await send('Runtime.enable')
  await send('Page.addScriptToEvaluateOnNewDocument', { source: 'window.confirm = () => true' })
  await send('Page.navigate', { url: `${origin}/admin/sumber-data` })
  await wait('document.querySelector("input[autocomplete=username]")')
  const setInput = (selector, value) => evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`)
  await setInput('input[autocomplete=username]', process.env.DEKSI_TEST_USER)
  await setInput('input[type=password]', process.env.DEKSI_TEST_PASS)
  await wait('Array.from(document.querySelectorAll("button")).some(x=>x.textContent.trim()==="Masuk"&&!x.disabled)')
  await evaluate('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="Masuk").click()')
  const submit = async () => {
    await wait('document.querySelector(".resync-action input[type=checkbox]") && !document.body.innerText.includes("Memeriksa antrean")')
    await evaluate('document.querySelector(".resync-action input[type=checkbox]").click()')
    await wait('document.querySelector(".resync-action__button") && !document.querySelector(".resync-action__button").disabled')
    await evaluate('document.querySelector(".resync-action__button").click()')
    await wait('document.querySelector(".resync-action__message button")')
  }
  const awaitStatus = async status => { for (let i = 0; i < 150; i++) { if (await evaluate(`document.querySelector('.resync-action')?.textContent.includes(${JSON.stringify(status)})`)) return; await evaluate('document.querySelector(".resync-action__message button")?.click()'); await delay(100) } throw new Error('status unavailable: ' + status) }
  await submit(); await awaitStatus('Berhasil')
  await send('Page.navigate', { url: `${origin}/admin/sumber-data` })
  await submit(); await awaitStatus('Berlangsung')
  await send('Page.navigate', { url: `${origin}/admin/riwayat-sinkronisasi` })
  await wait('document.querySelector("details.sync-history__reconcile summary")')
  await evaluate('document.querySelector("details.sync-history__reconcile summary").click()')
  await evaluate('document.querySelector(".sync-history__reconcile input[type=checkbox]").click()')
  await evaluate(`(()=>{const e=document.querySelector('.sync-history__reconcile textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,'Pemeriksaan manual dengan fixture sintetis');e.dispatchEvent(new Event('input',{bubbles:true}));})()`)
  await wait('document.querySelector(".sync-history__reconcile button") && !document.querySelector(".sync-history__reconcile button").disabled')
  await evaluate('document.querySelector(".sync-history__reconcile button").click()')
  await wait('document.querySelector("tbody")?.textContent.includes("Tidak diketahui")')
  assert.equal(trace.filter(x => x.method === 'POST' && x.path.endsWith('/resync/')).length, 2)
  assert.equal(trace.filter(x => x.method === 'POST' && x.path.endsWith('/reconcile/')).length, 1)
  assert(!trace.some(x => x.status >= 500), 'unexpected backend HTTP 5xx')
  console.log('PASS: real browser login, two BPS requests, synthetic success, interrupted worker and manual reconciliation')
} catch (error) { console.error(error); console.error('Sanitized API trace:', JSON.stringify(trace)); process.exitCode = 1 }
finally { if (send) await send('Browser.close').catch(() => {}); ws?.close(); chrome.kill(); await app.close(); await delay(500); await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 300 }) }
