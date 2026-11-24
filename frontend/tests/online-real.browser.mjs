import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const backend = process.env.DEKSI_DISPOSABLE_BACKEND
assert.match(backend || '', /^http:\/\/127\.0\.0\.1:\d+$/)
assert(process.env.HERMES_TEST_SCRATCH)
assert(process.env.DEKSI_SYNTHETIC_PASSWORD, 'Synthetic password must be generated at runtime by the runner')
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-online-real-'))
const fixture = { name: 'empty-integration-fixture', configureServer(server) { server.middlewares.use((req, res, next) => {
  if (req.url === '/online-integration') { res.setHeader('Content-Type', 'text/html'); res.end('<div id="root"></div>'); return }
  next()
}) } }
const app = await createServer({ root, configFile: false, envDir: profile, cacheDir: path.join(profile, 'vite'),
  plugins: [fixture], server: { host: '127.0.0.1', port: 0, strictPort: true,
    proxy: { '/api': { target: backend, changeOrigin: false } } } })
let chrome, ws, send
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
try {
  await app.listen()
  const origin = `http://127.0.0.1:${app.httpServer.address().port}`
  chrome = spawn(process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
      '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1',
      `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let port
  for (let i = 0; i < 100; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await delay(100) }
  assert(port, 'Chrome startup failed')
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  const pending = new Map(), failures = []
  let id = 0
  ws.addEventListener('message', event => {
    const result = JSON.parse(event.data)
    if (result.method === 'Network.responseReceived' && result.params.response.status >= 500) failures.push(result.params.response.status)
    if (!result.id) return
    const entry = pending.get(result.id)
    if (!entry) return
    clearTimeout(entry.timer); pending.delete(result.id)
    if (result.error) entry.reject(new Error(result.error.message))
    else entry.resolve(result.result)
  })
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id
    const timer = setTimeout(() => { pending.delete(n); reject(new Error(`CDP timeout ${method}`)) }, 20000)
    pending.set(n, { resolve, reject, timer }); ws.send(JSON.stringify({ id: n, method, params }))
  })
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  const wait = async expression => { for (let i = 0; i < 200; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(100) } throw new Error('Timeout: ' + expression) }
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  await send('Page.navigate', { url: `${origin}/online-integration` })
  await wait('document.getElementById("root")')
  const login = await evaluate(`(async()=>{
    const bootstrap=await fetch('/api/auth/csrf/',{credentials:'include'});
    if(!bootstrap.ok) return {status:bootstrap.status,stage:'csrf',type:bootstrap.headers.get('content-type')};
    const token=(await bootstrap.json()).csrfToken;
    const r=await fetch('/api/admin/login/',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({username:'online-browser-synthetic',password:${JSON.stringify(process.env.DEKSI_SYNTHETIC_PASSWORD)}})});
    return {status:r.status};})()`)
  assert.equal(login.status, 200, 'Actual disposable backend login failed')
  await evaluate(`import('/tests/online-admin-page.jsx')`)
  await wait(`Array.from(document.querySelectorAll('.admin-source-card')).some(card => card.textContent.includes('APBN KiTa'))`)
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('.admin-source-card')).find(card => card.textContent.includes('APBN KiTa'))?.querySelectorAll('.resync-action').length`), 1, 'Kemenkeu must mount the actual Admin action')
  const kitaCard = `Array.from(document.querySelectorAll('.admin-source-card')).find(card => card.textContent.includes('APBN KiTa'))`
  await wait(`${kitaCard}.querySelector('.resync-action input') && !${kitaCard}.textContent.includes('Memeriksa antrean')`)
  await evaluate(`window.confirm=()=>true; ${kitaCard}.querySelector('.resync-action input').click()`)
  await wait(`!${kitaCard}.querySelector('.resync-action button').disabled`)
  await evaluate(`${kitaCard}.querySelector('.resync-action button').click()`)
  await wait(`${kitaCard}.textContent.includes('Status server:')`)
  for (let i = 0; i < 30; i++) {
    if (await evaluate(`${kitaCard}.textContent.includes('Berhasil')`)) break
    await evaluate(`Array.from(${kitaCard}.querySelectorAll('button')).find(b=>b.textContent==='Perbarui status').click()`)
    await delay(200)
  }
  assert.equal(await evaluate(`${kitaCard}.textContent.includes('Berhasil')`), true, 'Kemenkeu actual Admin page')
  const kita = await evaluate(`(async()=>{const r=await fetch('/api/admin/sources/KEMENKEU/candidates/',{credentials:'include'}); const b=await r.json();return {status:r.status,count:b.items?.length,statuses:b.items?.map(x=>x.status)}})()`)
  assert.equal(kita.status, 200)
  assert.equal(kita.count, 4)
  assert(kita.statuses.every(status => status === 'pending'))
  await send('Page.navigate', { url: `${origin}/online-integration` })
  await wait('document.getElementById("root")')
  await evaluate(`window.confirm=()=>true; import('/tests/online-real-fixture.jsx')`)
  await wait('document.querySelectorAll(".resync-action input").length === 4 && !document.body.innerText.includes("Memeriksa antrean")')
  assert.equal(await evaluate(`document.querySelectorAll('.resync-action')[2].textContent.includes('Bank Indonesia melalui BIS')`), true)
  for (const [index, source] of [[0, 'BI'], [1, 'BKPM'], [2, 'BIS']]) {
    await evaluate(`document.querySelectorAll('.resync-action')[${index}].querySelector('input').click()`)
    await evaluate(`document.querySelectorAll('.resync-action')[${index}].querySelector('button').click()`)
    await wait(`document.querySelectorAll('.resync-action')[${index}].textContent.includes('Status server:')`)
    for (let i = 0; i < 30; i++) {
      if (await evaluate(`document.querySelectorAll('.resync-action')[${index}].textContent.includes('Berhasil')`)) break
      await evaluate(`Array.from(document.querySelectorAll('.resync-action')[${index}].querySelectorAll('button')).find(b=>b.textContent==='Perbarui status').click()`)
      await delay(200)
    }
    assert.equal(await evaluate(`document.querySelectorAll('.resync-action')[${index}].textContent.includes('Berhasil')`), true, source)
    const result = await evaluate(`(async()=>{const r=await fetch('/api/admin/sources/${source}/candidates/',{credentials:'include'}); const b=await r.json();return {status:r.status,count:b.items?.length,statuses:b.items?.map(x=>x.status)}})()`)
    assert.equal(result.status, 200)
    assert.equal(result.count, ['BI', 'KEMENKEU'].includes(source) ? 3 : 1)
    assert(result.statuses.every(status => status === 'pending'))
  }
  const logout = await evaluate(`(async()=>{const token=(await (await fetch('/api/auth/csrf/',{credentials:'include'})).json()).csrfToken; const r=await fetch('/api/admin/logout/',{method:'POST',credentials:'include',headers:{'X-CSRFToken':token}});return r.status;})()`)
  assert.equal(logout, 200)
  await send('Page.navigate', { url: `${origin}/online-integration` })
  await wait('document.getElementById("root")')
  await evaluate(`window.__historyRequests=[]; window.fetch=async (url)=>{
    const path=String(url); window.__historyRequests.push(path);
    if(path.startsWith('/api/indicators/birate/trend/')) {
      const year=new URL(path,location.origin).searchParams.get('year');
      const granularity=new URL(path,location.origin).searchParams.get('granularity');
      const isBI=year==='2025';
      if(isBI && granularity==='Bulanan') return new Response('{}',{status:400});
      return new Response(JSON.stringify({id:'birate',available:true,granularities:isBI?['Peristiwa','Tahunan']:['Harian','Bulanan','Tahunan'],points:[{
        label:isBI?'BI 2025':'BIS 2026',year:isBI?2025:2026,observationDate:isBI?'2025-01-01':'2026-01-01',
        value:isBI?5:6,exactValue:isBI?'5':'6',unit:'%',sourceId:isBI?'BI':'BIS',frequency:isBI?'adhoc':'daily',dataType:isBI?'event':'level'}]}),
        {status:200,headers:{'Content-Type':'application/json'}});
    }
    return new Response('{}',{status:404,headers:{'Content-Type':'application/json'}});
  }; import('/tests/dashboard-year-fixture.jsx')`)
  await wait(`document.querySelector('#economic-trend .dash-point-panel')?.textContent.includes('BIS 2026')`)
  await evaluate(`Array.from(document.querySelectorAll('[aria-labelledby="frequency-label"] button')).find(b=>b.textContent==='Bulanan').click()`)
  await wait(`window.__historyRequests.some(path=>path.includes('granularity=Bulanan'))`)
  await evaluate(`document.querySelector('#select-2025').click()`)
  await wait(`document.querySelector('#economic-trend .dash-point-panel')?.textContent.includes('BI 2025')`)
  assert(await evaluate(`window.__historyRequests.some(path=>path==='/api/indicators/birate/trend/?year=2025')`), 'BI-Rate request must carry selected year')
  assert(await evaluate(`document.querySelector('#economic-trend .dash-point-panel').textContent.includes('BI')`), 'filtered chart must show BI source')
  assert.deepEqual(failures, [])
  console.log('PASS real browser -> Vite -> Django session/CSRF -> queue -> worker -> pending candidate readback -> logout; offline providers, disposable PostgreSQL')
} finally {
  ws?.close(); chrome?.kill(); await app.close(); await delay(300)
  await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 250 })
}
