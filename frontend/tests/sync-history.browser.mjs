import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'vite'

const scratch = 'C:/Users/Pongo/AppData/Local/hermes/cache/scratch'
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
const profile = await mkdtemp(path.join(scratch, 'deksi13-test-'))
const vite = await createServer({ configLoader: 'runner', cacheDir: path.join(profile, 'vite'), server: { host: '127.0.0.1', port: 0, hmr: false, ws: false } })
let chrome, ws
try {
  await vite.listen()
  const origin = `http://127.0.0.1:${vite.httpServer.address().port}`
  chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let port
  for (let i = 0; i < 100; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await pause(100) }
  assert.ok(port, 'Chrome tidak tersedia')
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => ws.addEventListener('open', resolve, { once: true }))
  let seq = 0
  const pending = new Map(), exceptions = [], apiRequests = []
  const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++seq; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })) })
  ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.method === 'Runtime.exceptionThrown') exceptions.push(data.params.exceptionDetails.text); if (data.method === 'Network.requestWillBeSent' && data.params.request.url.includes('/api/')) apiRequests.push(data.params.request.url); if (!data.id) return; const p = pending.get(data.id); if (!p) return; pending.delete(data.id); if (data.error) p.reject(Error(JSON.stringify(data.error))); else p.resolve(data.result) })
  const js = async expression => { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails)); return result.result.value }
  const wait = async expr => { for (let i = 0; i < 120; i++) { if (await js(`Boolean(${expr})`)) return; await pause(50) } throw Error(`Timeout: ${expr}`) }
  const key = async (name, code) => { await send('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code: name, windowsVirtualKeyCode: code, ...(name === 'Enter' ? { text: '\r', unmodifiedText: '\r' } : {}) }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code: name, windowsVirtualKeyCode: code }) }
  const change = (selector, value) => js(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`)
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  await send('Page.navigate', { url: origin + '/preview-sync-history.html' }); await wait('document.body.innerText.includes("Riwayat belum terhubung")')
  assert.deepEqual(apiRequests, []); console.log('PASS disconnected preview has no API request')
  await send('Page.navigate', { url: origin + '/tests/sync-history-fixture.html' }); await wait('window.fixture?.calls.length===1')
  assert.deepEqual(await js('window.fixture.calls[0].query'), { page: 1, pageSize: 20 }); assert.match(await js('document.body.innerText'), /Memuat riwayat/)
  console.log('PASS loading and default query')
  await js(`window.fixture.calls[0].resolve({items:[{id:'a',sourceId:'BPS',sourceName:'Sumber uji',status:'running',startedAt:'2026-11-10T08:00:00Z',finishedAt:null,actor:null,itemCount:0,message:'<img src=x onerror=alert(1)>'},{id:'b',sourceId:'BI',sourceName:'Sumber kedua',status:'success',startedAt:'2026-02-30T00:00:00Z',finishedAt:null,actor:null,itemCount:null,message:null},{id:'c',sourceId:'D',sourceName:'Ketiga',status:'failed',startedAt:'2026-11-10T09:00:00Z',finishedAt:null,actor:null,itemCount:null,message:'Pengambilan data gagal pada satu atau lebih seri.'}],pagination:{page:1,pageSize:20,total:25,hasNext:true}})`)
  await wait('document.querySelectorAll("tbody tr").length===3')
  let rows = await js('[...document.querySelectorAll("tbody tr")].map(r=>[...r.cells].map(c=>c.textContent))')
  assert.equal(rows[0][5], '0'); assert.equal(rows[1][5], 'Tidak tersedia'); assert.equal(rows[1][0], 'Tidak tersedia'); assert.match(rows[0][2], /hasil akhir belum tercatat/i); assert.equal(rows[0][6], '<img src=x onerror=alert(1)>'); assert.equal(await js('document.querySelector("tbody img")===null'), true)
  assert.equal(await js('document.querySelectorAll("tbody tr")[2].querySelector("details summary")?.textContent'), 'Detail kegagalan')
  await js('document.querySelectorAll("tbody tr")[2].querySelector("details summary").click()')
  assert.equal(await js('document.querySelectorAll("tbody tr")[2].querySelector("details").open'), true)
  assert.match(await js('document.querySelectorAll("tbody tr")[2].innerText'), /Pengambilan data gagal/)
  console.log('PASS status, null vs zero, invalid date and escaped message')
  await js('[...document.querySelectorAll("button")].find(x=>x.textContent==="Berikutnya").click()'); await wait('window.fixture.calls.length===2'); assert.equal(await js('window.fixture.calls[1].query.page'), 2)
  await js('window.fixture.calls[1].resolve({items:[],pagination:{page:2,pageSize:20,total:25,hasNext:false}})'); await wait('document.body.innerText.includes("Belum ada riwayat")'); console.log('PASS pagination and empty')
  await change('#sync-status', 'failed'); await wait('window.fixture.calls.length===3'); assert.deepEqual(await js('window.fixture.calls[2].query'), { page: 1, pageSize: 20, status: 'failed' })
  await change('#sync-status', 'success'); await wait('window.fixture.calls.length===4'); assert.equal(await js('window.fixture.calls[2].signal.aborted'), true)
  await js('window.fixture.calls[3].resolve({items:[],pagination:{page:1,pageSize:20,total:0,hasNext:false}})'); await wait('document.body.innerText.includes("Belum ada riwayat")')
  await js(`window.fixture.calls[2].resolve({items:[{id:'stale',sourceId:'X',sourceName:'STALE',status:'failed',startedAt:'2026-01-01T00:00:00Z',finishedAt:null,actor:null,itemCount:null,message:null}],pagination:{page:1,pageSize:20,total:1,hasNext:false}})`); await pause(150); assert.doesNotMatch(await js('document.body.innerText'), /STALE/); console.log('PASS filters reset page, abort and stale response')
  await change('#sync-status', 'running'); await wait('window.fixture.calls.length===5'); await js('window.fixture.calls[4].reject(new Error("secret server text"))'); await wait('document.body.innerText.includes("Riwayat tidak dapat dimuat")'); assert.doesNotMatch(await js('document.body.innerText'), /secret server text/)
  await js('[...document.querySelectorAll("button")].find(x=>x.textContent==="Coba lagi").focus()'); assert.equal(await js('document.activeElement.textContent'), 'Coba lagi'); await key('Enter',13); await wait('window.fixture.calls.length===6'); console.log('PASS error and keyboard retry')
  await js('window.fixture.calls[5].resolve({items:[],pagination:{page:1,pageSize:20,total:0,hasNext:false}})'); await wait('document.body.innerText.includes("Belum ada riwayat")')
  await js(`(()=>{const e=document.querySelector('#sync-source');const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(e,' BPS ');e.dispatchEvent(new Event('input',{bubbles:true}))})()`); await js('document.querySelector("form").requestSubmit()'); await wait('window.fixture.calls.length===7'); assert.deepEqual(await js('window.fixture.calls[6].query'), { page:1, pageSize:20, status:'running', sourceId:'BPS' }); console.log('PASS source filter')
  for (const width of [1440, 760, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
    const layout = await js('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    assert.ok(layout.document <= layout.viewport, JSON.stringify(layout))
  }
  console.log('PASS responsive page widths')
  assert.deepEqual(apiRequests, []); assert.deepEqual(exceptions, []); console.log('PASS no backend API calls or runtime exceptions')
} finally {
  ws?.close(); chrome?.kill(); await vite.close(); await pause(500)
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 })
}
