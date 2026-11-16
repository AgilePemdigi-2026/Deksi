import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch && path.isAbsolute(scratch))
const profile = await mkdtemp(path.join(scratch, 'deksi-batch2-browser-'))
const app = await createServer({ root, configFile: false, cacheDir: path.join(profile, 'vite'), server: { host: '127.0.0.1', port: 0, strictPort: true, hmr: false, ws: false } })
let chrome, ws, send
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
try {
  await app.listen()
  const origin = `http://127.0.0.1:${app.httpServer.address().port}`
  chrome = spawn(process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let port
  for (let i = 0; i < 120; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await delay(100) }
  assert(port, 'Disposable Chrome did not start')
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let sequence = 0
  const pending = new Map()
  ws.addEventListener('message', event => { const result = JSON.parse(event.data); if (!result.id) return; const entry = pending.get(result.id); if (!entry) return; pending.delete(result.id); clearTimeout(entry.timer); if (result.error) entry.reject(new Error(JSON.stringify(result.error))); else entry.resolve(result.result) })
  send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; const timer = setTimeout(() => reject(new Error(`CDP timeout ${method}`)), 15000); pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params })) })
  const evaluate = async expression => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value }
  const wait = async expression => { for (let i = 0; i < 160; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(50) } throw new Error(`Timeout: ${expression}`) }
  await send('Page.enable'); await send('Runtime.enable')
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `
    const apiMode = new URL(location.href).searchParams.get('fixture') || 'empty';
    const json = (body, status=200) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json'}});
    const item = {sourceId:'BI',sourceName:'Sumber BI',institution:'Fixture',primaryUrl:'https://example.test/',description:'',acquisitionMethod:'file_xlsx',acquisitionMethodLabel:'File',endpointUrl:'',dataFormat:'xlsx',frequency:'monthly',updateSchedule:'',status:'active',revisionVersion:0,lastFetch:{retrievedAt:null,documentName:null,parseStatus:null}};
    window.fetch = (input, init) => {
      const url = String(input);
      if (init?.method && init.method !== 'GET') throw new Error('Mutation blocked by fixture');
      if (url.endsWith('/admin/session/')) return Promise.resolve(json({authenticated:true,username:'fixture',isStaff:true}));
      if (url.endsWith('/admin/sources/')) {
        if(apiMode==='loading') return new Promise(()=>{});
        if(apiMode==='error') return Promise.resolve(json({error:'synthetic failure'},500));
        return Promise.resolve(json({sources:apiMode==='populated'?[item]:[]}));
      }
      if (url.endsWith('/acquisition-methods/')) return Promise.resolve(json({methods:[],frequencies:[]}));
      if (url.includes('/feedback/categories/')) return Promise.resolve(json({categories:[],csrfToken:'synthetic'}));
      if (url.includes('/indicators/categories/')) return Promise.resolve(json({categories:[]}));
      if (url.includes('/indicators/dashboard/')) return Promise.resolve(apiMode==='dashboarderror'?json({error:'synthetic server error'},500):json({indicators:apiMode==='layout'?['pdb','inflasi','fiskal','investasi','birate','tpt'].map(id=>({id,name:id,available:false,value:null,unit:'',period:null,category:id,note:'Data belum tersedia'})):[]}));
      if (url.includes('/trend/')) {
        if(apiMode==='servererror') return Promise.resolve(json({error:'synthetic failure'},500));
        if(apiMode==='route404') return Promise.resolve(new Response('not found',{status:404,headers:{'Content-Type':'text/html'}}));
        if(apiMode==='other404') return Promise.resolve(json({error:"Indikator 'inflasi' tidak ditemukan"},404));
        if(apiMode==='nohistory') return Promise.resolve(json({id:'pdb',available:false,granularities:[],note:null}));
        if(apiMode==='network') return Promise.reject(new TypeError('synthetic network failure'));
        return Promise.resolve(json({error:"Indikator 'pdb' tidak ditemukan"},404));
      }
      if (url.includes('/indicators/')) return Promise.resolve(json({indicators:[{id:'pdb',available:false,value:null}]}));
      throw new Error('Unexpected fetch blocked: '+url);
    };
  ` })
  async function go(route) { await send('Page.navigate', { url: origin + route }); await wait('document.readyState === "complete" && !!document.querySelector("#root")') }
  const mode = process.argv[2] || 'all'
  if (mode === 'hero') {
    for (const width of [390, 1365]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 800, deviceScaleFactor: 1, mobile: false })
      await go('/?fixture=layout')
      await wait('document.querySelector(".hero-photo")?.complete && document.querySelector(".hero-photo").naturalWidth > 0')
      const image = await evaluate(`(()=>{const i=document.querySelector('.hero-photo');return {src:i.currentSrc,width:i.naturalWidth,height:i.naturalHeight,display:i.getBoundingClientRect().width}})()`)
      assert.match(image.src, /jakarta-monument-pexels-35586803\.jpg/)
      assert(image.width >= image.display, 'Hero asset must not be enlarged past its natural width')

      const folder = await mkdtemp(path.join(scratch, 'deksi-batch4-hero-'))
      const shot = await send('Page.captureScreenshot', { format:'png' })
      const file = path.join(folder, `hero-${width}.png`)
      await writeFile(file, Buffer.from(shot.data, 'base64'))
      console.log(`PASS hero ${width}: editorial asset loaded; preview ${file}`)
    }
  }
  // The rejected Batch 3 redesign is archived in the pre-rollback backup, not a visual acceptance target.
  if (mode === 'navigation' || mode === 'all') {
    for (const width of [390, 1365]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 800, deviceScaleFactor: 1, mobile: false })
      await go('/?fixture=layout')
      await wait('!!document.querySelector(".hero .book")')
      assert.equal(await evaluate('document.querySelector(".hero .book").getAttribute("href")'), '#economic-indicators')
      await evaluate('document.querySelector(".hero .book").click()')
      await wait('location.hash === "#economic-indicators"')
      await evaluate('document.querySelector(".dash-summary-grid button").focus(); document.querySelector(".dash-summary-grid button").click()')
      await wait('document.querySelector(".p2-info").open')
      await evaluate('document.querySelector(".p2-info button").click()')
      await wait('!document.querySelector(".p2-info").open && document.activeElement === document.querySelector(".dash-summary-grid button")')
      console.log(`PASS navigation ${width}: data link and dialog focus restoration`)
    }
  }
  if (mode === 'counts' || mode === 'all') {
    await go('/?fixture=dashboarderror')
    await wait('!!document.querySelector(".dash-empty[role=alert]")')
    assert.notEqual(await evaluate('document.querySelector(".inventory-card .mini-value").textContent'), '0', 'API failure must not claim zero indicators')
    assert.notEqual(await evaluate('document.querySelector(".awards-card .trust-value").textContent'), '0', 'API failure must not claim zero indicators in trust section')
    console.log('PASS layout error does not invent zero available indicators')
  }
  if (mode === 'admin' || mode === 'all') {
    await go('/admin/sumber-data?fixture=empty')
    await wait('!document.body.innerText.includes("Memuat registry sumber") && document.body.innerText.includes("Tambah Sumber Data")')
    assert.match(await evaluate('document.body.innerText'), /Belum ada sumber data/i)
    await evaluate('[...document.querySelectorAll("button")].find(b=>b.textContent.includes("Tambah Sumber Data")).click()')
    await wait('!!document.querySelector("article[aria-label]") && document.querySelector("article[aria-label]").getAttribute("aria-label") === "Form tambah sumber"')
    await go('/admin/sumber-data?fixture=populated'); await wait('!!document.querySelector(".source-card")')
    assert.doesNotMatch(await evaluate('document.body.innerText'), /Belum ada sumber data/i)
    await go('/admin/sumber-data?fixture=error'); await wait('!!document.querySelector(".summary-error")')
    assert.doesNotMatch(await evaluate('document.body.innerText'), /Belum ada sumber data/i)
    await go('/admin/sumber-data?fixture=loading'); await wait('document.body.innerText.includes("Memuat registry sumber")')
    assert.doesNotMatch(await evaluate('document.body.innerText'), /Belum ada sumber data/i)
    console.log('PASS admin empty + add form, populated, error and loading')
  }
  if (mode === 'public' || mode === 'all') {
    await go('/?fixture=empty'); await wait('!!document.querySelector(".dash-chart-empty") && !document.querySelector(".dash-chart-empty").textContent.includes("Memuat")')
    const text = await evaluate('document.querySelector(".dash-chart-empty").textContent')
    assert.match(text, /indikator.*belum tersedia/i)
    assert.doesNotMatch(text, /HTTP 404/)
    const selected = await evaluate('document.querySelector("#fb-category").options[0].textContent')
    assert.equal(selected, 'Pilih kategori')
    const values = await evaluate('Array.from(document.querySelectorAll("#feedback-form input,#feedback-form textarea,#feedback-form button")).map(e=>[e.value,e.textContent,e.placeholder].join(" ")).join(" ")')
    assert.doesNotMatch(values, /ΓÇ|Γ£/)
    await go('/?fixture=nohistory'); await wait('document.querySelector(".dash-chart-empty")?.textContent.includes("Belum ada histori")')
    for (const fixture of ['servererror', 'route404', 'other404', 'network']) {
      await go('/?fixture='+fixture); await wait('!!document.querySelector(".dash-chart-empty[role=alert]")')
      const message = await evaluate('document.querySelector(".dash-chart-empty").textContent')
      assert.doesNotMatch(message, /indikator.*belum tersedia/i, fixture)
      assert.match(message, /Coba histori lagi/, fixture)
    }
    console.log('PASS public indicator-not-found, feedback text, server/route/network errors')
  }
} finally {
  if (send) await send('Browser.close').catch(() => {})
  ws?.close(); chrome?.kill(); await app.close(); await delay(400)
  await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 250 })
}
