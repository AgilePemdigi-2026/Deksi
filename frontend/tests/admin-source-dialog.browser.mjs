import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH || os.tmpdir(), 'deksi-source-dialog-'))
const denyApi = { name: 'deny-real-api', configureServer(server) { server.middlewares.use((req, res, next) => { if (new URL(req.url, 'http://127.0.0.1').pathname.startsWith('/api/')) { res.writeHead(403); res.end('Blocked by test'); return } next() }) } }
const app = await createServer({ configFile: false, plugins: [denyApi, react()], root, envDir: profile, cacheDir: path.join(profile, 'vite'), server: { host: '127.0.0.1', port: 0, strictPort: true } })
assert.deepEqual(app.config.server.proxy ?? {}, {}, 'tes tidak boleh mengaktifkan proxy backend')
await app.listen()
const chromePath = process.env.CHROME_PATH || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'google-chrome')
const chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0', '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
let chromeError
chrome.on('error', error => { chromeError = error })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send
try {
  let port
  for (let i = 0; i < 100; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await delay(100) }
  assert(port, `Chrome did not start: ${chromeError?.message || 'set CHROME_PATH to a Chrome executable'}`)
  assert.equal((await fetch(`http://127.0.0.1:${app.httpServer.address().port}/api/unexpected/`)).status, 403, 'direct API request must be blocked')
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0; const pending = new Map(); const networkBlocked = []
  const testOrigin = `http://127.0.0.1:${app.httpServer.address().port}`
  ws.addEventListener('message', e => {
    const r = JSON.parse(e.data)
    if (r.method === 'Fetch.requestPaused') {
      const { requestId, request } = r.params
      const allowed = new URL(request.url).origin === testOrigin && ['GET', 'HEAD'].includes(request.method)
      if (!allowed) networkBlocked.push({ url: request.url, method: request.method })
      send(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', allowed ? { requestId } : { requestId, errorReason: 'BlockedByClient' }).catch(() => {})
      return
    }
    if (!r.id) return; const p = pending.get(r.id); if (!p) return; pending.delete(r.id); clearTimeout(p.timer); if (r.error) p.reject(new Error(JSON.stringify(r.error))); else p.resolve(r.result)
  })
  send = (method, params = {}) => new Promise((resolve, reject) => { const n = ++id; const timer = setTimeout(() => reject(new Error(`CDP timeout ${method}`)), 30000); pending.set(n, { resolve, reject, timer }); ws.send(JSON.stringify({ id: n, method, params })) })
  const evaluate = async expression => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value }
  const wait = async expression => { for (let i = 0; i < 150; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(60) } throw new Error(`Timeout: ${expression}`) }
  const key = async (name, code, vk) => { await send('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code, windowsVirtualKeyCode: vk }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code, windowsVirtualKeyCode: vk }) }
  await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*', requestStage: 'Request' }] })
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `
    (()=>{const real=window.fetch.bind(window);window.__confirm=false;window.confirm=()=>window.__confirm;window.__requests=[];window.__blocked=[];window.__successAction=null;let deleted=false;
    const row={sourceId:'SYNTH',sourceName:'Sumber Sintetis',institution:'Contoh',primaryUrl:'https://example.test/',description:'',acquisitionMethod:'file_xlsx',acquisitionMethodLabel:'File',endpointUrl:'',dataFormat:'xlsx',frequency:'monthly',updateSchedule:'',status:'active',revisionVersion:1,lastFetch:{retrievedAt:null,documentName:null,parseStatus:null}};
    const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
    window.fetch=(input,init={})=>{const parsed=new URL(input instanceof Request ? input.url : String(input),location.href);const method=init.method||(input instanceof Request ? input.method : 'GET');if(parsed.origin!==location.origin){window.__blocked.push('external');return Promise.reject(new Error('external request blocked'))}if(!parsed.pathname.startsWith('/api/')){if(method!=='GET'){window.__blocked.push('mutation');return Promise.reject(new Error('unexpected mutation blocked'))}return real(input,init)}const url=parsed.pathname+parsed.search;window.__requests.push({url,method,body:init.body||null});
      if(url.endsWith('/admin/session/'))return Promise.resolve(json({authenticated:true,canReviewCandidates:true}));
      if(url.endsWith('/auth/csrf/'))return Promise.resolve(json({csrfToken:'fixture'}));
      const action=['update','archive','delete'].find(a=>url.endsWith('/SYNTH/'+a+'/'));
      if(action){const expected=action==='update'?'PUT':'POST';const body=JSON.parse(init.body||'{}');if(method!==expected||body.expectedRevision!==row.revisionVersion)return Promise.resolve(json({error:'invalid revision or method'},400));if(window.__successAction!==action)return Promise.resolve(json({error:'konflik '+action},409));if(action==='update'){row.sourceName=body.sourceName;row.revisionVersion++;return Promise.resolve(json({changedFields:['sourceName'],revision:{version:row.revisionVersion}}))}if(action==='archive'){row.status='archived';row.revisionVersion++}if(action==='delete')deleted=true;return Promise.resolve(json({}))}
      if(url.endsWith('/admin/sources/'))return Promise.resolve(json({sources:deleted?[]:[row]}));
      if(url.endsWith('/acquisition-methods/'))return Promise.resolve(json({methods:[{value:'file_xlsx',label:'File',formats:['xlsx'],endpointRequired:false}],frequencies:['monthly']}));
      if(url.endsWith('/SYNTH/revisions/'))return Promise.resolve(json({revisions:[]}));
      if(url.endsWith('/SYNTH/'))return Promise.resolve(json({...row,revisionCount:1}));
      if(url.includes('/bulk-preview/')&&init.method==='POST')return new Promise(resolve=>window.__releasePreview=()=>resolve(json({error:'fixture conflict'},409)));
      if(url.includes('/bulk-review/active/'))return Promise.resolve(json({batch:null}));
      if(url.includes('/candidates/'))return Promise.resolve(json({items:[],total:0,page:1,hasNext:false}));
      window.__blocked.push('unknown API');return Promise.resolve(json({error:'unexpected fixture request'},404));
    };})();` })
  await send('Page.navigate', { url: `http://127.0.0.1:${app.httpServer.address().port}/admin/sumber-data` })
  try { await wait(`Array.from(document.querySelectorAll('.source-card button')).some(x=>x.textContent.includes('Edit'))`) }
  catch (error) { console.error('Fixture state:', await evaluate(`({text:document.body.innerText.slice(0,500),requests:window.__requests,blocked:window.__blocked})`)); throw error }
  assert.deepEqual(await evaluate(`(async()=>{const external=await fetch('http://192.0.2.1/test').then(()=>false,()=>true);const unknown=await fetch('/api/unexpected/').then(r=>r.status);const blocked=window.__blocked.splice(0);return {external,unknown,blocked}})()`), { external: true, unknown: 404, blocked: ['external', 'unknown API'] })
  assert.equal(await evaluate(`new Promise(resolve=>{const x=new XMLHttpRequest();x.open('GET','http://127.0.0.1:9/blocked-test');x.onerror=()=>resolve('blocked');x.onload=()=>resolve('allowed');x.send()})`), 'blocked')
  assert.equal(networkBlocked.length, 1, 'CDP guard must intercept an XHR bypass')
  networkBlocked.length = 0
  await evaluate(`Array.from(document.querySelectorAll('.source-card button')).find(x=>x.textContent.includes('Edit')).click()`)
  await wait(`document.querySelector('dialog[open] input[value="Sumber Sintetis"]')`)
  assert.equal(await evaluate(`document.querySelector('dialog').matches(':modal')`), true)
  assert.equal(await evaluate(`document.querySelector('dialog').contains(document.activeElement)`), true)
  await evaluate(`Array.from(document.querySelectorAll('dialog input')).find(x=>x.value==='Sumber Sintetis').focus()`)
  await send('Input.insertText', { text: 'X' }); await delay(100)
  await key('Escape', 'Escape', 27)
  assert.equal(await evaluate(`document.querySelector('dialog')?.open`), true, 'cancelled confirmation must preserve form')
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('dialog input')).some(x=>x.value==='Sumber SintetisX')`), true)
  await evaluate('window.__confirm=true')
  for (const [button, action] of [['Simpan Perubahan','update'],['Arsipkan Sumber','archive'],['Hapus Permanen','delete']]) {
    await evaluate(`Array.from(document.querySelectorAll('dialog button')).find(x=>x.textContent===${JSON.stringify(button)}).click()`)
    await wait(`window.__requests.some(x=>x.url.includes('/SYNTH/${action}/'))`)
    await wait(`document.querySelector('dialog .summary-error')?.textContent.includes('konflik ${action}')`)
    assert.equal(await evaluate(`document.querySelector('dialog')?.open`), true, `${action} error stays visible`)
  }
  await key('Escape', 'Escape', 27)
  await wait(`!document.querySelector('dialog')`)
  assert.match(await evaluate('document.activeElement.textContent'), /Edit/, 'focus returns to Edit')
  await evaluate(`Array.from(document.querySelectorAll('.source-card button')).find(x=>x.textContent==='Lihat Kandidat').click()`)
  await wait(`document.querySelector('dialog[open] .candidate-review')`)
  await wait(`Array.from(document.querySelectorAll('dialog button')).some(x=>x.textContent.startsWith('Pratinjau kandidat')&&!x.disabled)`)
  assert.equal(await evaluate(`document.querySelector('dialog').matches(':modal')`), true)
  for (const width of [390, 768, 1440]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
    assert.equal(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'), true, `overflow at ${width}`)
    assert.equal(await evaluate(`(()=>{const r=document.querySelector('dialog').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()`), true)
  }
  await send('Emulation.clearDeviceMetricsOverride')
  await evaluate(`Array.from(document.querySelectorAll('dialog button')).find(x=>x.textContent.startsWith('Pratinjau kandidat')).click()`)
  await wait('typeof window.__releasePreview === "function"')
  await wait(`Array.from(document.querySelectorAll('dialog button')).find(x=>x.textContent==='Tutup kandidat').disabled`)
  await key('Escape', 'Escape', 27)
  assert.equal(await evaluate(`document.querySelector('dialog')?.open`), true, 'Escape must not close pending review')
  await evaluate('window.__releasePreview()')
  await wait(`document.querySelector('dialog [role="alert"]')`)
  await evaluate(`Array.from(document.querySelectorAll('dialog button')).find(x=>x.textContent==='Tutup kandidat').click()`)
  await wait(`!document.querySelector('dialog')`)
  assert.equal(await evaluate('document.activeElement.textContent'), 'Lihat Kandidat')
  for (const [button, action] of [['Simpan Perubahan','update'],['Arsipkan Sumber','archive'],['Hapus Permanen','delete']]) {
    await evaluate(`window.__successAction=${JSON.stringify(action)}`)
    await evaluate(`Array.from(document.querySelectorAll('.source-card button')).find(x=>x.textContent.includes('Edit')).click()`)
    await wait(`document.querySelector('dialog[open] input[value]') && !document.querySelector('dialog .summary-loading')`)
    if (action === 'update') {
      await evaluate(`Array.from(document.querySelectorAll('dialog input')).find(x=>x.value==='Sumber Sintetis').focus()`)
      await send('Input.insertText', { text: 'X' }); await delay(100)
    }
    await evaluate(`Array.from(document.querySelectorAll('dialog button')).find(x=>x.textContent===${JSON.stringify(button)}).click()`)
    await wait(`!document.querySelector('dialog')`)
    await wait(`document.body.innerText.includes(${JSON.stringify(action==='update'?'direvisi':action==='archive'?'berhasil diarsipkan':'berhasil dihapus')})`)
    if (action === 'delete') {
      await wait(`!document.querySelector('.source-card')`)
      assert.equal(await evaluate('document.activeElement.id'), 'admin-sources-title')
    } else {
      await wait(`document.body.innerText.includes(${JSON.stringify(action==='update'?'Sumber SintetisX':'Diarsipkan')})`)
    }
  }
  assert.equal(await evaluate(`window.__requests.filter(x=>x.method==='POST' && !x.url.includes('/bulk-preview/') && !x.url.includes('/SYNTH/archive/') && !x.url.includes('/SYNTH/delete/')).length`), 0, 'unexpected write')
  assert.deepEqual(await evaluate('window.__blocked'), [], 'unexpected requests during test')
  assert.deepEqual(networkBlocked, [], 'unexpected browser network requests')
  console.log('PASS: dialogs, distinct errors and successful edit/archive/delete, network guard, focus, responsive widths')
} catch (error) { console.error(error); process.exitCode = 1 }
finally { if (send) await send('Browser.close').catch(() => {}); ws?.close(); chrome.kill(); await app.close(); await delay(500); await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 300 }) }
