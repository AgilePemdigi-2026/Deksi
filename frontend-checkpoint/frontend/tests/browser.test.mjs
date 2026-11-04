import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, writeFile, mkdir, rm } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'
import os from 'node:os'
import path from 'node:path'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const output = process.env.DEKSI_BROWSER_ARTIFACTS || path.join(root, '.artifacts/browser')
const scratch = process.env.HERMES_TEST_SCRATCH || process.env.TMPDIR || os.tmpdir()
const profile = await mkdtemp(path.join(scratch, 'deksi-react-browser-'))
await mkdir(output, { recursive: true })
const app = await createServer({ root, cacheDir: path.join(root, 'node_modules/.vite-browser-tests'), server: { host: '127.0.0.1', port: 0, strictPort: true } })
await app.listen()
const url = `http://127.0.0.1:${app.httpServer.address().port}`
const chromePath = process.env.CHROME_BIN || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : 'google-chrome')
const chrome = spawn(chromePath, ['--headless=new','--disable-gpu','--hide-scrollbars','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'], { stdio: 'ignore' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, closeOwned = async () => {}, mode = 'ready'
const checks = [], screenshots = [], errors = [], apiRequests = []
const cards = ['pdb','inflasi','fiskal','investasi','birate','tpt'].map((id,index) => ({id,available:index<2,name:`${id.toUpperCase()} · UJI SINTETIS`,category:'Data uji',value:index===0?'4.21':index===1?'0':null,unit:'Persen uji',period:'Q1 2000',latestPeriod:'Q1 2000',latestYear:2000,hasCurrentYearData:false,note:'Respons sintetis untuk pengujian, bukan data resmi.',source:index===0?'Instansi uji':'',delta:null,deltaDirection:'flat',deltaPositive:false,sparkline:index===0?[1,2,3,4.21]:index===1?[0]:[],observationDate:'2000-01-01'}))
const summary = {updatedAt:'2000-01-01',updatedAtFormatted:'DATA UJI SINTETIS',lastUpdate:{formatted:'DATA UJI SINTETIS · 1 Januari 2000',source:'test',status:'test',message:'Respons browser test, bukan backend aktual.'},indicators:cards}
try {
 let port
 for(let i=0;i<100;i++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port)break}catch{}await delay(100)}
 assert(port, 'Isolated Chrome did not start')
 const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
 ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl)
 await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})})
 let id=0;const pending=new Map()
 ws.addEventListener('message',event=>{const r=JSON.parse(event.data);if(r.method==='Runtime.exceptionThrown')errors.push(r.params.exceptionDetails.exception?.description??r.params.exceptionDetails.text);if(r.method==='Fetch.requestPaused')void fulfill(r.params);if(!r.id)return;const p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);if(r.error)p.reject(new Error(JSON.stringify(r.error)));else p.resolve(r.result)})
 const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id,timer=setTimeout(()=>{pending.delete(n);reject(new Error('CDP timeout: '+method))},30000);pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params}))})
 async function fulfill(event){
  try {
   apiRequests.push(event.request.url)
   const parsed=new URL(event.request.url);const code=parsed.pathname.match(/\/indicators\/([^/]+)\/trend\//)?.[1]
   const body=code?{id:code,available:true,granularities:['Kuartalan','Tahunan'],granularity:'Kuartalan',unit:'Persen uji',points:[{label:'Q1 2000',value:code==='inflasi'?0:1,year:2000},{label:'Q2 2000',value:2,year:2000},{label:'Q1 2001',value:3,year:2001}],latestAvailable:'Q1 2001',hasCurrentYearData:false,dataAvailableUntil:'Q1 2001',historicalAverage:2,note:'Data tren uji sintetis.'}:mode==='empty'?{...summary,indicators:[]}:summary
   await send('Fetch.fulfillRequest',{requestId:event.requestId,responseCode:mode==='error'?503:200,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from(JSON.stringify(body)).toString('base64')})
  }catch(error){errors.push(String(error))}
 }
 const js=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value}
 const wait=async expression=>{for(let i=0;i<150;i++){if(await js(`Boolean(${expression})`))return;await delay(80)}throw new Error('Page condition failed: '+expression)}
 const go=async(width=1440,route='/')=>{await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await send('Page.navigate',{url:url+route});await wait('document.querySelector(".hero-photo")?.complete && document.fonts.status === "loaded"');await delay(150)}
 const click=async selector=>{await js(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center',behavior:'instant'})`);const p=await js(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);await send('Input.dispatchMouseEvent',{type:'mousePressed',...p,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',...p,button:'left',clickCount:1})}
 const key=async(name,code)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code});await send('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code})}
 const screenshot=async name=>{await js('document.querySelector(".trend").scrollIntoView({block:"center",behavior:"instant"})');await wait('document.querySelector(".recharts-line-curve")?.getAttribute("d")');await wait('document.querySelector(".recharts-line-curve")?.getBBox().width > 100');await js('scrollTo({top:0,behavior:"instant"})');const size=await js('({width:innerWidth,height:document.documentElement.scrollHeight})');await send('Emulation.setDeviceMetricsOverride',{...size,deviceScaleFactor:1,mobile:false});await wait('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)');await js('Promise.all(Array.from(document.images).map(i=>i.decode())).then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))');await delay(200);const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,...size,scale:1}});const png=Buffer.from(shot.data,'base64');await writeFile(path.join(output,name),png);screenshots.push({file:name,width:png.readUInt32BE(16),height:png.readUInt32BE(20)})}
 closeOwned=()=>send('Browser.close').catch(()=>{})
 await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://localhost:8000/api/*',requestStage:'Request'}]})
 await go();await wait('document.querySelectorAll(".indicator-card").length===6')
 assert.equal(await js('document.documentElement.scrollWidth'),1440)
 assert.equal(await js('document.querySelector(".hero-photo-wrap").getBoundingClientRect().width'),764)
 assert.equal(await js('getComputedStyle(document.querySelector(".hero")).backgroundColor'),'rgb(218, 218, 218)')
 assert(await js('document.querySelector(".indicator-value").textContent.includes("4.21")'))
 assert(await js('Array.from(document.querySelectorAll(".indicator-value")).some(e=>e.textContent.startsWith("0"))'))
 assert.equal(await js('Array.from(document.querySelectorAll(".sparkline")).some(e=>/NaN|Infinity/.test(e.outerHTML))'),false)
 await screenshot('dashboard-desktop.png')
 checks.push('Real React landing retains selected 764px hero geometry and paper palette; six synthetic API cards preserve zero/missing/history semantics')
 await js('document.querySelector(".trend").scrollIntoView()');await wait('document.querySelector(".recharts-line-curve")')
 await click('.trend-tabs button:nth-child(2)');await delay(150)
 assert(apiRequests.some(u=>u.endsWith('/inflasi/trend/')))
 await click('.trend-tabs button:first-child');await delay(150)
 checks.push('Existing API-backed trend chart renders and indicator selection requests the correct endpoint; no ingestion/backend was started')
 await click('.contact');assert(await js('document.querySelector(".presentation-dialog").open'))
 assert(await js('document.querySelector(".presentation-dialog").textContent.includes("belum dikonfirmasi")'))
 assert.equal(await js('Array.from(document.querySelectorAll(".media-credit-list a")).some(a=>a.getAttribute("href")==="null")'),false)
 await key('Escape',27);assert.equal(await js('document.querySelector(".presentation-dialog").open'),false)
 assert(await js('document.activeElement.matches(".contact")'))
 checks.push('Sources/rights disclosure opens; Escape closes and restores focus; no fabricated source links or verification claim')
 for(const width of[390,760,1024]){await go(width);await wait('document.querySelectorAll(".indicator-card").length===6');assert.equal(await js('document.documentElement.scrollWidth'),width);await screenshot(`dashboard-${width}.png`)}
 checks.push('390, 760 and 1024px responsive renders have no horizontal overflow')
 mode='empty';await go(1440);await wait('document.querySelector(".summary-empty")');assert.equal(await js('document.querySelectorAll(".indicator-card").length'),0)
 mode='error';await go();await wait('document.querySelector(".summary-error")');assert.equal(await js('document.querySelectorAll(".indicator-card").length'),0)
 assert(await js('document.querySelector(".hero-date").textContent.includes("API BELUM TERHUBUNG")'))
 checks.push('Empty and failed backend responses remain explicit; no prototype fixture is silently substituted')
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});await go(390)
 assert.equal(await js('getComputedStyle(document.documentElement).scrollBehavior'),'auto')
 assert.deepEqual(errors,[])
 const sha=bytes=>createHash('sha256').update(bytes).digest('hex')
 const receipt={scope:'React presentation and synthetic API browser regression; not a live Django/provider/data-accuracy test',checks,screenshots,runtimeErrors:errors,apiRequests,apiSourceSha256:sha(await readFile(path.join(root,'src/api.ts'))),visualAcceptance:'pending integrated-page review'}
 await writeFile(path.join(output,'verification.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt,null,2))
}catch(error){console.error(error);process.exitCode=1}
finally{await closeOwned();ws?.close();chrome.kill();await app.close();await delay(500);await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:300}).catch(e=>console.error('Owned profile cleanup:',e.message))}
