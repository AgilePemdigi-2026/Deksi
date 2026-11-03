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
const checks = [], screenshots = [], errors = [], apiRequests = [], authRequests = [], networkRequests = []
let authMode = 'credentials'
const cancelledRequests = new Set()
let cancelledInterceptions = 0
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
 ws.addEventListener('message',event=>{const r=JSON.parse(event.data);if(r.method==='Network.requestWillBeSent')networkRequests.push({url:r.params.request.url,method:r.params.request.method});if(r.method==='Network.loadingFailed'&&r.params.canceled)cancelledRequests.add(r.params.requestId);if(r.method==='Runtime.exceptionThrown')errors.push(r.params.exceptionDetails.exception?.description??r.params.exceptionDetails.text);if(r.method==='Fetch.requestPaused')void fulfill(r.params);if(!r.id)return;const p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);if(r.error)p.reject(new Error(JSON.stringify(r.error)));else p.resolve(r.result)})
 const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id,timer=setTimeout(()=>{pending.delete(n);reject(new Error('CDP timeout: '+method))},30000);pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params}))})
 async function fulfill(event){
  try {
   const requestURL=new URL(event.request.url)
   if(requestURL.pathname.startsWith('/api/auth/')){
    authRequests.push({url:event.request.url,method:event.request.method})
    const route=requestURL.pathname.split('/').filter(Boolean).at(-1)
    if(route==='logout'&&event.request.method==='POST')authMode='credentials'
    const status=event.request.method==='OPTIONS'?204:route==='login'?(authMode==='uncertain'?500:401):route==='session'&&authMode==='forbidden'?403:200
    const payload=route==='csrf'?{csrfToken:'SYNTHETIC-UI-CONTROL-TOKEN'}:route==='login'?{code:'invalid_credentials'}:route==='session'&&authMode==='forbidden'?{code:'forbidden'}:{authenticated:false,user:null}
    await send('Fetch.fulfillRequest',{requestId:event.requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:authMode==='uncertain'&&route==='login'?'text/html':'application/json'},{name:'Access-Control-Allow-Origin',value:url},{name:'Access-Control-Allow-Credentials',value:'true'},{name:'Access-Control-Allow-Headers',value:'Content-Type, X-CSRFToken'},{name:'Access-Control-Allow-Methods',value:'GET, POST, OPTIONS'}],body:event.request.method==='OPTIONS'?'':Buffer.from(authMode==='uncertain'&&route==='login'?'<h1>Synthetic upstream failure</h1>':JSON.stringify(payload)).toString('base64')})
    return
   }
   apiRequests.push(event.request.url)
   const parsed=new URL(event.request.url);const code=parsed.pathname.match(/\/indicators\/([^/]+)\/trend\//)?.[1]
   const body=code?{id:code,available:true,granularities:['Kuartalan','Tahunan'],granularity:'Kuartalan',unit:'Persen uji',points:[{label:'Q1 2000',value:code==='inflasi'?0:1,year:2000},{label:'Q2 2000',value:2,year:2000},{label:'Q1 2001',value:3,year:2001}],latestAvailable:'Q1 2001',hasCurrentYearData:false,dataAvailableUntil:'Q1 2001',historicalAverage:2,note:'Data tren uji sintetis.'}:mode==='empty'?{...summary,indicators:[]}:summary
   await send('Fetch.fulfillRequest',{requestId:event.requestId,responseCode:mode==='error'?503:200,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from(JSON.stringify(body)).toString('base64')})
  }catch(error){
   await delay(0)
   if(String(error).includes('Invalid InterceptionId')&&cancelledRequests.has(event.networkId))cancelledInterceptions++
   else errors.push(String(error))
  }
 }
 const js=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value}
 const wait=async expression=>{for(let i=0;i<150;i++){if(await js(`Boolean(${expression})`))return;await delay(80)}throw new Error('Page condition failed: '+expression)}
 const go=async(width=1440,route='/')=>{await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await send('Page.navigate',{url:url+route});await wait('document.querySelector(".hero-photo")?.complete && document.fonts.status === "loaded"');await delay(150)}
 const click=async selector=>{await js(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center',behavior:'instant'})`);const p=await js(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);await send('Input.dispatchMouseEvent',{type:'mousePressed',...p,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',...p,button:'left',clickCount:1})}
 const key=async(name,code)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code});await send('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code})}
 const screenshot=async name=>{await js('scrollTo({top:0,behavior:"instant"})');const size=await js('({width:innerWidth,height:document.documentElement.scrollHeight})');await send('Emulation.setDeviceMetricsOverride',{...size,deviceScaleFactor:1,mobile:false});await wait('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)');await js('Promise.all(Array.from(document.images).map(i=>i.decode())).then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))');await delay(200);const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,...size,scale:1}});const png=Buffer.from(shot.data,'base64');await writeFile(path.join(output,name),png);screenshots.push({file:name,width:png.readUInt32BE(16),height:png.readUInt32BE(20)})}
 closeOwned=()=>send('Browser.close').catch(()=>{})
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://localhost:8000/api/*',requestStage:'Request'},{urlPattern:'http://127.0.0.1:8000/api/auth/*',requestStage:'Request'}]})

 const setSynthetic=async(selector,value)=>js(`(()=>{const field=document.querySelector(${JSON.stringify(selector)});field.value=${JSON.stringify(value)};field.dispatchEvent(new Event('input',{bubbles:true}))})()`)
 await go(1440,'/admin/login');await wait('document.querySelector(".login-form-panel") && !document.querySelector("#login-submit").disabled')
 assert.equal(await js('document.querySelectorAll(".summary").length'),0)
 assert.equal(apiRequests.length,0,'Login must not mount dashboard API hooks')
 assert.equal(await js('getComputedStyle(document.querySelector(".login-page")).backgroundColor'),'rgb(218, 218, 218)')
 assert.equal(await js('document.querySelector(".hero-photo").naturalWidth'),1920)
 assert.equal(await js('document.documentElement.scrollWidth'),1440)
 await screenshot('login-desktop.png')
 checks.push('Canonical React login route renders the approved image/style without mounting dashboard API requests')
 await click('#login-submit');await wait('document.querySelectorAll("input[aria-invalid=true]").length===2')
 assert.equal(await js('document.activeElement.id'),'identifier')
 await setSynthetic('#identifier','pengelola.contoh');await click('#login-submit')
 assert.equal(await js('document.activeElement.id'),'password')
 await setSynthetic('#password','SYNTHETIC-FIXTURE-NOT-AN-ACCOUNT')
 await click('#password-toggle');await wait('document.getElementById("password").type==="text"')
 assert.equal(await js('document.getElementById("password").value === "SYNTHETIC-FIXTURE-NOT-AN-ACCOUNT"'),true)
 assert.equal(await js('document.getElementById("password-toggle").getAttribute("aria-pressed")'),'true')
 await click('#password-toggle');await wait('document.getElementById("password").type==="password"')
 checks.push('Required-field focus/errors and actual React show/hide behavior preserve synthetic input')
 await click('#login-submit');await wait('document.getElementById("form-status").textContent.includes("tidak valid") && !document.getElementById("login-submit").disabled')
 assert(authRequests.some(request=>request.method==='POST'&&request.url.endsWith('/api/auth/login/')))
 assert.equal(apiRequests.length,0)
 assert.equal(await js('localStorage.length+sessionStorage.length'),0)
 assert.equal(await js('location.pathname'),'/admin/login')
 assert.equal(await js('Boolean(document.getElementById("session-user"))'),false)
 checks.push('Synthetic auth rejection is shown honestly; no dashboard hooks, token storage or fake successful session')
 authMode='uncertain'
 await click('#login-submit');await wait('document.getElementById("form-status").textContent.includes("belum dapat dipastikan")')
 assert.equal(await js('document.getElementById("login-submit").disabled'),true)
 assert.equal(await js('document.getElementById("password").value === "SYNTHETIC-FIXTURE-NOT-AN-ACCOUNT"'),true)
 authMode='credentials'
 await click('#session-refresh');await wait('!document.getElementById("login-submit").disabled')
 checks.push('Ambiguous upstream failure keeps password local and requires session reconciliation before another submit')
 await click('#login-submit');await wait('document.getElementById("form-status").textContent.includes("tidak valid")')
 authMode='forbidden'
 await click('#session-refresh');await wait('document.getElementById("form-status").textContent.includes("tidak lagi memiliki akses")')
 assert.equal(await js('Boolean(document.getElementById("session-user"))'),false)
 await click('#auth-logout');await wait('document.getElementById("form-status").textContent.includes("telah keluar")')
 authMode='credentials'
 checks.push('Revoked Admin permission clears the visible identity and still permits explicit logout')
 await click('#recovery-help summary');assert(await js('document.getElementById("recovery-help").open'))
 assert(await js('document.getElementById("recovery-help").textContent.includes("belum tersedia")'))
 await click('#recovery-help summary')
 await js('document.getElementById("identifier").focus()');await key('Tab',9)
 assert.equal(await js('document.activeElement.id'),'password')
 await key('Tab',9);assert.equal(await js('document.activeElement.id'),'password-toggle')
 assert.equal(await js('getComputedStyle(document.activeElement).outlineStyle'),'solid')
 await click('.footer-links button');assert(await js('document.getElementById("prototype-info").open'))
 assert.equal(await js('document.querySelectorAll("#prototype-info a").length'),3)
 await key('Escape',27);assert.equal(await js('document.getElementById("prototype-info").open'),false)
 assert(await js('document.activeElement.matches(".footer-links button")'))
 checks.push('Recovery help, actual keyboard focus and source-dialog Escape/return focus work')
 for(const width of[390,760,1024]){await go(width,'/admin/login');assert.equal(await js('document.documentElement.scrollWidth'),width);await screenshot(`login-${width}.png`)}
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});await go(390,'/admin/login')
 assert.equal(await js('getComputedStyle(document.querySelector(".submit-button")).transitionDuration'),'0s')
 checks.push('390, 760 and 1024px captures retain layout without overflow; reduced motion respected')
 await send('Emulation.setEmulatedMedia',{features:[]})
 await click('.return-link');await wait('document.querySelector(".editorial-footer .admin-entry")')
 assert.equal(await js('location.pathname'),'/')
 assert.equal(await js('document.querySelector(".admin-entry").getAttribute("href")'),'/admin/login')
 await click('.admin-entry');await wait('document.querySelector(".login-page")')
 assert.equal(await js('location.pathname'),'/admin/login')
 assert.deepEqual(errors,[])
 checks.push('Real navigation works both ways: public dashboard -> Admin login -> public, without public account gate')
 const sha=bytes=>createHash('sha256').update(bytes).digest('hex')
 const receipt={scope:'Mocked-auth UI regression only; real Django integration is a separate suite',checks,screenshots,runtimeErrors:errors,expectedCancelledInterceptions:cancelledInterceptions,credentialsSentOnlyToSyntheticAuthHarness:true,appSourceSha256:sha(await readFile(path.join(root,'src/App.tsx'))),loginSourceSha256:sha(await readFile(path.join(root,'src/features/admin/LoginPage.tsx'))),imageSha256:sha(await readFile(path.join(root,'src/assets/editorial/login-economic.webp'))),visualAcceptance:'Existing design retained; new authenticated state awaits human review'}
 await writeFile(path.join(output,'verification.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt,null,2))
}catch(error){console.error(error);process.exitCode=1}
finally{await closeOwned();ws?.close();chrome.kill();await app.close();await delay(500);await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:300}).catch(e=>console.error('Owned profile cleanup:',e.message))}
