import assert from 'node:assert/strict'
import {spawn,spawnSync} from 'node:child_process'
import {readFile,writeFile,mkdtemp,rm} from 'node:fs/promises'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
const frontend=process.env.DEKSI_QA_FRONTEND,output=process.env.DEKSI_QA_OUTPUT,scratch=process.env.HERMES_TEST_SCRATCH
assert(frontend&&output&&scratch,'Use frontend-owned Python runner')
const fixture=JSON.parse(await readFile(process.env.DEKSI_QA_FIXTURE,'utf8'))
const profile=await mkdtemp(path.join(scratch,'deksi-b2-browser-'))
const checks=[],errors=[],consoleErrors=[],requests=[],responses=[],shots=[]
const pause=ms=>new Promise(r=>setTimeout(r,ms))
let server,chrome,ws,send
let failure=null
try {
 server=await createServer({root:frontend,configLoader:'runner',cacheDir:path.join(output,'vite-cache'),server:{host:'127.0.0.1',port:56120,strictPort:true}})
 await server.listen()
 const origin='http://127.0.0.1:56120'
 chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'})
 let port
 for(let n=0;n<120;n++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port)break}catch{}await pause(100)}
 assert(port)
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
 ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl)
 await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true})})
 let sequence=0
 const pending=new Map()
 send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method))},15000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})
 ws.addEventListener('message',event=>{
  const d=JSON.parse(event.data)
  if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.exception?.description??d.params.exceptionDetails.text)
  if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')consoleErrors.push(d.params.args.map(x=>x.value??x.description).join(' '))
  if(d.method==='Network.requestWillBeSent')requests.push({url:d.params.request.url,method:d.params.request.method})
  if(d.method==='Network.responseReceived'&&d.params.response.url.includes('/api/'))responses.push({url:d.params.response.url,status:d.params.response.status})
  if(!d.id)return
  const p=pending.get(d.id);if(!p)return;pending.delete(d.id);clearTimeout(p.timer);d.error?p.reject(new Error(JSON.stringify(d.error))):p.resolve(d.result)
 })
 const js=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value}
 const wait=async expression=>{for(let i=0;i<160;i++){if(await js(`Boolean(${expression})`))return;await pause(70)}throw new Error('Condition timed out: '+expression)}
 const go=async(route,width=1440)=>{await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await js('window.__qaMarker=true');await send('Page.navigate',{url:origin+route});await wait('!window.__qaMarker&&document.readyState==="complete"&&document.fonts.status==="loaded"')}
 const check=async(name,fn)=>{await fn();checks.push(name);console.log('PASS '+name)}
 const shot=async(name,full=false)=>{const params={format:'png',captureBeyondViewport:true};if(full){const layout=await send('Page.getLayoutMetrics');params.clip={x:0,y:0,width:layout.cssContentSize.width,height:layout.cssContentSize.height,scale:1}}const image=await send('Page.captureScreenshot',params);await writeFile(path.join(output,name),Buffer.from(image.data,'base64'));shots.push(name)}
 const key=async(name,code)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code,...(name==='Enter'?{text:'\r',unmodifiedText:'\r'}:{})});await send('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code})}
 const input=async(selector,value)=>{await js(`document.querySelector(${JSON.stringify(selector)}).focus()`);await send('Input.insertText',{text:value})}
 const select=async(selector,value)=>js(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`)
 const dashboardReady=()=>wait('document.querySelectorAll(".dash-indicator").length===6&&!document.querySelector(".dash-overview").textContent.includes("Memuat…")')
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable')
 // No Fetch.enable, API interception, mocked success, source requests or provider calls.
 await check('Full Prototype2 composition uses actual public API; zero, exact strings and missing data stay distinct',async()=>{
  await go('/');await dashboardReady();await wait('document.querySelector("#trend-svg .dash-point")')
  assert.equal(await js('document.querySelector("[data-indicator=inflasi] .dash-card-value").textContent'),'0')
  assert.equal(await js('document.querySelector("[data-indicator=tpt] .dash-card-value").textContent'),'Belum tersedia')
  assert.equal(await js('document.querySelector("[data-indicator=pdb] .dash-card-value").textContent'),'999.999.999.999.999.999,999999')
  assert.equal(await js('[...document.querySelectorAll("#hero,#statement,#economic-overview,#economic-indicators,#economic-trend,#economic-insights,#economic-sources,#trust,#feedback-section")].length'),9)
  assert.equal(await js('document.querySelector(".hero-photo").naturalWidth>0'),true)
  assert((await js('document.querySelector(".hero").getBoundingClientRect().height'))>800,'Desktop hero must retain the locked donor composition')
  assert((await js('document.querySelector(".hero-photo-wrap").getBoundingClientRect().width'))>600,'Hero media cannot collapse when donor CSS is scoped')
  await shot('dashboard-desktop-synthetic.png');await shot('dashboard-full-desktop-synthetic.png',true)
 })
 await check('Real search, no-result reset and category filter drive visible cards and trend choices',async()=>{
  await input('#indicator-search','NO_SUCH_INDICATOR');await wait('document.querySelector(".dash-empty")')
  assert.equal(await js('document.querySelectorAll(".dash-indicator").length'),0)
  await js('document.querySelector(".dash-empty button").click()');await dashboardReady()
  await js('document.querySelector("#filter-cat-inflasi").click()');await wait('document.querySelectorAll(".dash-indicator").length===1')
  await wait('document.querySelector("#chart-series-name")||document.querySelector("#economic-trend .dash-selected-value p").textContent==="Inflasi"')
  assert.equal(await js('document.querySelector(".dash-indicator").dataset.indicator'),'inflasi')
 })
 await check('Selected-year summary/history agree; native gap splitting, point keyboard and JSON export retain exact values',async()=>{
  await select('#filter-year','2024')
  await wait('document.querySelector(".dash-card-period")?.textContent.includes("UJI 2024-03")')
  await wait('document.querySelectorAll("#trend-svg .dash-point").length===2')
  assert.equal(await js('document.querySelector(".dash-card-value").textContent'),'3,123456')
  assert.equal(await js('document.querySelectorAll("#trend-svg .dash-line").length'),2)
  await js('document.querySelector("#trend-svg circle[tabindex]").focus()');await key('Home',36)
  await wait('document.querySelector("#chart-current-period").textContent.includes("UJI 2024-01")')
  assert.equal(await js('document.querySelector("#chart-current-value").textContent'),'2,123456')
  await key('End',35);await wait('document.querySelector("#chart-current-period").textContent.includes("UJI 2024-03")')
  await js('window.__downloadText=null;window.__originalBlob=URL.createObjectURL;URL.createObjectURL=b=>{b.text().then(t=>window.__downloadText=t);return window.__originalBlob(b)}')
  // Capture the actual Blob passed to the native download; this does not intercept API data.
  await js('document.querySelector(".dash-chart-toolbar button").click()');await wait('window.__downloadText')
  const downloaded=JSON.parse(await js('window.__downloadText'));assert.equal(downloaded.points.length,2);assert.deepEqual(downloaded.points.map(p=>p.value),['2.123456','3.123456']);assert.equal(downloaded.year,'2024')
  await writeFile(path.join(output,'export-inflasi-synthetic.json'),JSON.stringify(downloaded,null,2))
  await shot('dashboard-filtered-chart-synthetic.png')
 })
 let traceURL
 await check('Filtered-year card opens same exact Detail, Source Trace and RAW; no latest-value substitution',async()=>{
  await js('document.querySelector(".dash-card-bottom button").click()');await wait('location.pathname==="/indikator/inflasi"&&document.querySelector("#feature-content")?.getAttribute("aria-busy")==="false"')
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'3,123456')
  assert((await js('location.search')).includes('tanggal=2024-03-31'))
  traceURL=await js('document.querySelector(".fd-source-panel a").getAttribute("href")')
  await go(traceURL);await wait('document.querySelector("#feature-content")?.getAttribute("aria-busy")==="false"')
  assert.equal(await js('document.querySelector(".ft-value").textContent'),'3,123456')
  const raw=await js(`(async()=>{const r=await fetch(${JSON.stringify(fixture.raw_url)});const bytes=await r.arrayBuffer();return {status:r.status,hash:[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('')}})()`)
  assert.equal(raw.status,200);assert.equal(raw.hash,fixture.raw_checksum)
  await shot('source-trace-synthetic.png')
  await go(traceURL.replace('/sumber?','?'));await wait('document.querySelector(".fd-metric")?.textContent==="3,123456"')
 })
 await check('Anonymous feedback keeps CSRF enabled: missing-token request is 403; form saves pending with cookie/token',async()=>{
  await go('/');await dashboardReady();await wait('document.querySelector("#fb-category option[value=data_error]")')
  assert.equal(await js('fetch("/api/feedback/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({category:"data_error",description:"UJI missing csrf"})}).then(r=>r.status)'),403)
  await select('#fb-category','data_error');await input('#fb-description','UJI SINTETIS browser feedback, not real user report.')
  await js('document.querySelector("#feedback-form button[type=submit]").click()');await wait('document.querySelector(".feedback-success")')
  assert((await js('document.querySelector(".feedback-success").textContent')).includes('Umpan Balik'))
  const inspect=spawnSync(process.env.DEKSI_QA_PYTHON,['-B',fileURLToPath(new URL('./dashboard_integration.py',import.meta.url)),'--inspect-feedback'],{env:process.env,encoding:'utf8'})
  assert.equal(inspect.status,0,inspect.stderr);const saved=JSON.parse(inspect.stdout);assert.equal(saved.rows.length,1);assert.equal(saved.rows[0].status,'pending');assert.equal(saved.rows[0].admin_notes,'');assert.equal(saved.rows[0].sender_name,'');assert.equal(saved.rows[0].sender_email,'')
  assert.equal(await js('localStorage.length+sessionStorage.length'),0)
  await shot('feedback-pending-synthetic.png')
 })
 await check('Login, forgot and reset routes preserve original forms, public navigation and honest unavailable auth',async()=>{
  await go('/admin/login');await wait('document.querySelector("#form-status")?.textContent.includes("belum")||document.querySelector("#session-refresh")')
  assert.equal(await js('!!document.querySelector("#economic-overview")'),false)
  assert.equal(await js('document.querySelector("#login-submit").disabled'),true)
  await shot('login-auth-unavailable.png')
  await js('document.querySelector("#recovery-help").click()');await wait('location.pathname==="/admin/forgot-password"&&document.querySelector("form")')
  await shot('forgot-password.png')
  await go('/admin/reset-password');assert.equal(await js('document.querySelectorAll("input[type=password]").length'),0)
  await shot('reset-without-capability.png')
  await go('/sumber-data');assert((await js('document.body.textContent')).includes('Halaman tidak ditemukan'))
 })
 await check('Empty year never falls back to current data; offline error recovers with explicit retry',async()=>{
  await go('/');await dashboardReady();await select('#filter-year','2026');await wait('document.querySelectorAll(".dash-indicator").length===6&&document.querySelector("[data-indicator=inflasi] .dash-card-value").textContent==="Belum tersedia"')
  await wait('document.querySelector(".dash-chart-empty")');assert.equal(await js('document.querySelector("#chart-current-value").textContent'),'Belum tersedia')
  await send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0})
  await select('#filter-year','2024');await wait('document.querySelector(".dash-empty[role=alert]")')
  await send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1})
  await js('document.querySelector(".dash-empty button").click()');await wait('document.querySelector("[data-indicator=inflasi] .dash-card-value")?.textContent==="3,123456"')
 })
 await check('Responsive desktop, tablet and narrow website retains content and accessible focus without page overflow',async()=>{
  for(const width of [1440,768,390]){
   await go('/',width);await dashboardReady()
   assert.equal(await js('document.documentElement.scrollWidth>innerWidth+1'),false,'overflow '+width)
   assert.equal(await js('document.querySelectorAll("img").length'),12)
   await js('document.querySelector(".plate-menu").focus();document.querySelector(".plate-menu").click()');await wait('document.querySelector(".p2-info").open')
   await key('Escape',27);assert.equal(await js('document.activeElement===document.querySelector(".plate-menu")'),true)
   await shot(`dashboard-${width}-synthetic.png`,width===390)
  }
  await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});await go('/',390);await dashboardReady();await js('scrollTo(0,500)');await pause(150)
  assert.equal(await js('getComputedStyle(document.querySelector(".hero-photo-wrap")).transform'),'none')
 })
 assert.equal(errors.length,0,errors.join('\n'))
 assert(!requests.some(r=>/bps-status|\/api\/status\/|sync|ingest/.test(r.url)),'No provider probe')
 assert(!requests.some(r=>/^https?:/.test(r.url)&&!r.url.startsWith(origin)),'Unexpected non-proxy external request')
} catch(error){failure=String(error.stack??error);console.error(failure);if(send){try{const image=await send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(output,'failure.png'),Buffer.from(image.data,'base64'))}catch{}}}
finally {
 if(send){try{await send('Browser.close')}catch{}}
 ws?.close()
 if(chrome&&chrome.exitCode===null){chrome.kill();await pause(300)}
 await server?.close()
 for(let i=0;i<15;i++){try{await rm(profile,{recursive:true,force:true});break}catch{await pause(200)}}
 const receipt={synthetic:true,api_interception:false,checks,errors,consoleErrors,requests,responses,screenshots:shots,failure,owned_browser_profile_removed:!await import('node:fs').then(fs=>fs.existsSync(profile))}
 await writeFile(path.join(output,'browser.json'),JSON.stringify(receipt,null,2)+'\n')
 console.log(JSON.stringify({checks:checks.length,errors,failure,profileRemoved:receipt.owned_browser_profile_removed}))
}
if(failure)process.exitCode=1
