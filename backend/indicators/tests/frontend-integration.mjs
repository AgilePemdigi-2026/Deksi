import assert from 'node:assert/strict'
import {spawn, spawnSync} from 'node:child_process'
import {readFile, writeFile, mkdtemp, rm} from 'node:fs/promises'
import {existsSync} from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
import {fileURLToPath, pathToFileURL} from 'node:url'

const frontend = process.env.DEKSI_QA_FRONTEND
const output = process.env.DEKSI_QA_OUTPUT
const scratch = process.env.HERMES_TEST_SCRATCH
assert(frontend && output && scratch, 'Use the Python-owned integration runner')
const fixture = JSON.parse(await readFile(process.env.DEKSI_QA_FIXTURE, 'utf8'))
assert.equal(fixture.synthetic, true)
const require = createRequire(path.join(frontend, 'package.json'))
const {createServer} = await import(pathToFileURL(require.resolve('vite')).href)
const browser = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
assert(existsSync(browser), 'Use an existing browser, do not install or close the user browser')
const profile = await mkdtemp(path.join(scratch, 'deksi-be-live-browser-'))
const checks = [], errors = [], requests = [], responses = [], screenshots = []
let server, chrome, ws, send
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
const check = async (name, action) => { await action(); checks.push(name); console.log('PASS ' + name) }
try {
  server = await createServer({root:frontend, cacheDir:path.join(output, 'vite-cache'),
    server:{host:'127.0.0.1', port:5196, strictPort:true}})
  await server.listen()
  const origin = 'http://127.0.0.1:5196'
  chrome = spawn(browser, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {stdio:'ignore'})
  let port
  for (let i=0; i<120; i++) {
    try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if(port) break } catch {}
    await pause(100)
  }
  assert(port, 'Owned Chrome did not become ready')
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, {once:true}); ws.addEventListener('error', reject, {once:true}) })
  let sequence=0
  const pending = new Map()
  send = (method, params={}) => new Promise((resolve, reject) => {
    const id=++sequence
    const timer=setTimeout(() => {pending.delete(id); reject(new Error('CDP timeout: '+method))}, 15000)
    pending.set(id, {resolve, reject, timer}); ws.send(JSON.stringify({id, method, params}))
  })
  ws.addEventListener('message', event => {
    const result=JSON.parse(event.data)
    if(result.method==='Runtime.exceptionThrown') errors.push(result.params.exceptionDetails.exception?.description ?? result.params.exceptionDetails.text)
    if(result.method==='Network.requestWillBeSent') requests.push({url:result.params.request.url,method:result.params.request.method})
    if(result.method==='Network.responseReceived' && result.params.response.url.includes('localhost:8000/api/')) {
      responses.push({url:result.params.response.url, status:result.params.response.status})
    }
    if(!result.id) return
    const entry=pending.get(result.id); if(!entry) return
    pending.delete(result.id); clearTimeout(entry.timer)
    if(result.error) entry.reject(new Error(JSON.stringify(result.error))); else entry.resolve(result.result)
  })
  const js = async expression => {
    const result = await send('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true})
    if(result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  const wait = async expression => {
    for(let i=0; i<180; i++) { if(await js(`Boolean(${expression})`)) return; await pause(70) }
    throw new Error('Browser condition timed out: '+expression)
  }
  const ready = () => wait('!window.__qaMarker && document.querySelector("#feature-content")?.getAttribute("aria-busy") === "false"')
  const go = async (route, width=1440) => {
    await send('Emulation.setDeviceMetricsOverride', {width, height:1000, deviceScaleFactor:1, mobile:false})
    await js('window.__qaMarker=true'); await send('Page.navigate', {url:origin+route})
    await wait('!window.__qaMarker && document.readyState === "complete" && document.fonts.status === "loaded"')
  }
  const key = async (name, code) => {
    await send('Input.dispatchKeyEvent', {type:'keyDown', key:name, code:name, windowsVirtualKeyCode:code,
      ...(name==='Enter'?{text:'\r',unmodifiedText:'\r'}:{})})
    await send('Input.dispatchKeyEvent', {type:'keyUp', key:name, code:name, windowsVirtualKeyCode:code})
  }
  const shot = async name => {
    const image = await send('Page.captureScreenshot', {format:'png', captureBeyondViewport:true})
    await writeFile(path.join(output,name), Buffer.from(image.data,'base64')); screenshots.push(name)
  }
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  // Intentionally NO Fetch.enable/fulfillRequest, proxy substitution or API payload interception.
  await check('Real Django GETs return reviewed zero, exact values and all 24 shared-RAW observations', async () => {
    const summary = await (await fetch('http://localhost:8000/api/indicators/?code=inflasi')).json()
    const source = await (await fetch('http://localhost:8000/api/indicators/inflasi/source-trace/')).json()
    assert.equal(summary.indicators[0].value, '0'); assert.equal(source.value, '0')
    assert.equal(source.history.length, fixture.rows)
    assert(source.history.every(row=>row.rawFile?.checksumSha256===fixture.rawSha256))
    assert(source.history.some(row=>row.value==='2.123456'))
    assert.equal(source.revisionId, null); assert.equal(source.immutableSnapshot, false)
  })
  let currentURL, oldURL, sourceURL
  await check('Actual Dashboard → Detail uses public API without login or synthetic interception', async () => {
    await go('/'); await wait('document.querySelector(\'.indicator-card a[href="/indikator/inflasi"]\')')
    await js('document.querySelector(\'.indicator-card a[href="/indikator/inflasi"]\').click()'); await ready()
    assert.equal(await js('location.pathname'), '/indikator/inflasi')
    assert.equal(await js('document.querySelector(".fd-metric").textContent'), '0')
    assert.equal(await js('document.querySelectorAll("#fd-period option:not([disabled])").length'), fixture.rows)
    assert.equal(await js('document.querySelectorAll(".fd-point").length'), fixture.rows)
    assert.equal(await js('!!document.querySelector(".fd-status[role=alert]")'), false)
    currentURL=await js('document.querySelector(".fd-source-panel a").getAttribute("href")')
    await shot('f6-real-api-desktop-synthetic.png')
  })
  await check('Keyboard Detail → Source Trace → return retains zero, source, period, RAW and selector', async () => {
    await js('document.querySelector(".fd-source-panel a").focus()'); await js('window.__qaMarker=true')
    await key('Enter',13); await ready()
    sourceURL=await js('location.pathname+location.search'); assert.equal(sourceURL,currentURL)
    assert.equal(await js('document.querySelector(".ft-value").textContent'),'0')
    assert.equal(await js('document.querySelector(".ft-value-period").textContent'),'Januari 2000')
    assert(await js('document.body.textContent.includes("INSTANSI UJI SINTETIS")'))
    assert(await js('document.body.textContent.includes("Formula belum tersedia")'))
    assert.equal(await js('!!window.__xss'),false)
    assert.equal(await js('document.querySelectorAll(".source-trace-feature img").length'),0)
    await shot('f7-real-api-desktop-synthetic.png')
    await js('document.querySelector(".ft-actions a").focus()'); await js('window.__qaMarker=true')
    await key('Enter',13); await ready()
    assert.equal(await js('location.pathname+location.search'),sourceURL.replace('/sumber?','?'))
    assert.equal(await js('document.querySelector(".fd-metric").textContent'),'0')
  })
  await check('Native oldest-period selection beyond old 12-row limit survives source navigation and reload', async () => {
    await js('document.querySelector("#fd-period").focus()'); await js('window.__qaMarker=true'); await key('End',35); await ready()
    assert.equal(await js('document.querySelector(".fd-metric").textContent'),fixture.oldestValueDisplay)
    assert(await js(`document.querySelector('.fd-reading').textContent.includes(${JSON.stringify(fixture.oldestPeriod)})`))
    oldURL=await js('location.pathname+location.search')
    const link=await js('document.querySelector(".fd-source-panel a").getAttribute("href")')
    await go(link); await ready()
    assert.equal(await js('document.querySelector(".ft-value").textContent'),fixture.oldestValueDisplay)
    await js('window.__qaMarker=true'); await send('Page.reload'); await ready()
    assert.equal(await js('document.querySelector(".ft-value").textContent'),fixture.oldestValueDisplay)
    assert.equal(await js('document.querySelector(".ft-actions a").getAttribute("href")'),oldURL)
  })
  await check('Cross-origin browser RAW download matches digest; disk corruption is refused with HTTP 503', async () => {
    const result=await js(`(async()=>{const r=await fetch(${JSON.stringify(fixture.rawUrl)},{credentials:'omit'});const b=await r.arrayBuffer();return {status:r.status,digest:[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('')}})()`)
    assert.equal(result.status,200); assert.equal(result.digest,fixture.rawSha256)
    await writeFile(fixture.rawPath,'CORRUPTED SYNTHETIC BYTES')
    try { assert.equal(await js(`fetch(${JSON.stringify(fixture.rawUrl)}).then(r=>r.status)`),503) }
    finally { await writeFile(fixture.rawPath,fixture.rawContent) }
  })
  await check('Real stored-value change refuses an old context instead of silently replacing it', async () => {
    const mutate=value=>{
      const result=spawnSync(process.env.DEKSI_QA_PYTHON,[fileURLToPath(new URL('./run_frontend_integration.py',import.meta.url)),'--set-value',value],{encoding:'utf8',env:process.env})
      assert.equal(result.status,0,result.stderr)
    }
    mutate('9')
    try {
      await go(currentURL); await ready()
      assert.equal(await js('document.querySelector(".ft-value").textContent'),'Belum tersedia')
      assert(await js('document.querySelector(".fd-status").textContent.includes("berubah")'))
      assert.equal(await js('!!document.querySelector(".ft-actions a[href*=tanggal]")'),false)
    } finally { mutate('0') }
    await go(currentURL); await ready(); assert.equal(await js('document.querySelector(".ft-value").textContent'),'0')
  })
  await check('Empty data never becomes zero and malformed revisions trigger no API loader', async () => {
    await go('/indikator/tpt'); await ready()
    assert.equal(await js('document.querySelector(".fd-metric").textContent'),'Belum tersedia')
    assert.equal(await js('document.querySelectorAll(".fd-point").length'),0)
    const before=requests.filter(r=>r.url.includes('localhost:8000/api/')).length
    await go('/indikator/inflasi?revisi=not-a-real-revision')
    await wait('document.querySelector("h1")?.textContent === "Halaman tidak ditemukan."')
    assert.equal(requests.filter(r=>r.url.includes('localhost:8000/api/')).length,before)
  })
  await check('Exact history survives actual Django JSON through table and SVG tooltip without rounding', async () => {
    await go('/indikator/pdb'); await ready()
    assert.equal(await js('document.querySelector(".fd-history tbody tr td:nth-child(3)").textContent'),fixture.exactDisplay)
    assert((await js('document.querySelector(".fd-point title").textContent')).includes(fixture.exactDisplay))
    assert.equal(await js('document.querySelectorAll(".fd-point").length'),1)
  })
  await check('Actual mixed-source rows refuse one chart and retain both source identities', async () => {
    await go('/indikator/fiskal'); await ready()
    assert((await js('document.querySelector(".fd-chart-empty").textContent')).includes('Sumber histori tidak konsisten'))
    assert.equal(await js('document.querySelectorAll(".fd-line").length'),0)
    assert.deepEqual(await js('[...document.querySelectorAll(".fd-history tbody tr td:last-child")].map(e=>e.textContent)'),['TEST_ONLY','ALT_TEST_ONLY'])
  })
  await check('Actual January–March monthly history has two isolated segments and no invented February or zero', async () => {
    await go('/indikator/investasi'); await ready()
    assert.equal(await js('document.querySelectorAll(".fd-point").length'),2)
    assert.deepEqual(await js('[...document.querySelectorAll(".fd-line")].map(e=>e.points.numberOfItems)'),[1,1])
    assert.deepEqual(await js('[...document.querySelectorAll(".fd-history tbody tr td:nth-child(3)")].map(e=>e.textContent)'),['1','3'])
    for(const width of [390,768,1440]) {
      await go('/indikator/investasi',width); await ready()
      await js('document.querySelector(".fd-history details").open=true')
      assert(await js('document.documentElement.scrollWidth <= document.documentElement.clientWidth'))
    }
  })
  await check('Real-API source page remains readable at 390/768/1440; no source-link fetch or console exception', async () => {
    for(const width of [390,768,1440]) {
      await go(currentURL,width); await ready()
      const bounds=await js('({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})')
      assert(bounds.scroll<=bounds.client,JSON.stringify(bounds))
      assert.equal(await js('document.querySelector(".ft-value").textContent'),'0')
      if(width===390) await shot('f7-real-api-mobile-synthetic.png')
    }
    assert(!requests.some(r=>r.url.includes('example.test')))
    assert(!requests.some(r=>new URL(r.url).pathname.startsWith('/admin/')))
    assert(responses.some(r=>r.url.endsWith('/source-trace/')&&r.status===200))
    assert.equal(errors.length,0,JSON.stringify(errors))
  })
} catch(error) {
  errors.push(String(error.stack||error)); console.error(error); process.exitCode=1
} finally {
  if(send) { try{await send('Browser.close')}catch{} }
  if(ws) ws.close()
  if(chrome) {
    for(let i=0;i<40&&chrome.exitCode===null;i++) await pause(50)
    if(chrome.exitCode===null) chrome.kill()
  }
  if(server) await server.close()
  await pause(200)
  await rm(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100})
  await writeFile(path.join(output,'verification.json'),JSON.stringify({synthetic:true,api_interception:false,
    checks,errors,requests,responses,screenshots,owned_browser_profile_removed:!existsSync(profile)},null,2))
}
