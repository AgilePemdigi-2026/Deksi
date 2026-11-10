import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises'
import {existsSync} from 'node:fs'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {createServer} from 'vite'
import {dto,reading} from './indicator-fixtures.mjs'

const root=fileURLToPath(new URL('../',import.meta.url))
const scratch=process.env.HERMES_TEST_SCRATCH
assert(scratch && path.isAbsolute(scratch),'Set HERMES_TEST_SCRATCH to the permitted scratch directory')
const executable=process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
assert(existsSync(executable),'Installed browser required; do not install or close the user browser')
const sourceTrace=process.argv.includes('--source-trace')
const output=path.join(root,sourceTrace?'.artifacts/feature7-browser':'.artifacts/feature6-browser')
await mkdir(output,{recursive:true})
await mkdir(scratch,{recursive:true})
const profile=await mkdtemp(path.join(scratch,sourceTrace?'deksi-f7-browser-':'deksi-f6-browser-'))
const checks=[],errors=[],requests=[],screenshots=[]
const cancelledNetworks=new Set(),interceptionErrors=[]
let server,chrome,ws,send,mode='ready',held=[]
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const check=async(name,action)=>{await action();checks.push(name);console.log('PASS '+name)}
function payloadFor(url){
 const code=url.pathname.match(/\/indicators\/([^/]+)\//)?.[1] || url.searchParams.get('code') || 'inflasi'
 const payload=dto()
 const base=reading({indicatorCode:code,indicatorName:code.toUpperCase()+' UJI SINTETIS'})
 base.rawFile.downloadUrl=`/api/indicators/${code}/raw-file/1/`
 const past={...structuredClone(base),value:'2',period:'Desember 1999',observationDate:'1999-12-31',rawFile:null}
 payload.trace={...base,history:[structuredClone(base),past]}
 payload.summary.indicators[0]={...payload.summary.indicators[0],id:code,name:base.indicatorName,deltaDirection:'flat',deltaPositive:false,sparkline:[0]}
 if(!url.searchParams.get('code'))payload.summary.indicators=['pdb','inflasi','fiskal','investasi','birate','tpt'].map(id=>({...payload.summary.indicators[0],id,name:id.toUpperCase()+' UJI SINTETIS'}))
 payload.trend={...payload.trend,id:code,points:[{label:'Desember 1999',observationDate:'1999-12-31',value:2,unit:base.unit},{label:'Gap uji',observationDate:'2000-01-15',value:null,unit:base.unit},{label:'Januari 2000',observationDate:'2000-01-31',value:0,unit:base.unit}]}
 payload.trend.points=payload.trend.points.map(point=>({...point,frequency:'monthly',dataType:'yoy'}))
 if(mode==='mixed-type')payload.trend.points[0].dataType='level'
 if(mode==='mixed-frequency')payload.trend.points[0].frequency='quarterly'
 if(mode==='empty')return {summary:{indicators:[]},trend:{id:code,available:false},trace:{indicatorCode:code,available:false}}
 if(mode==='changed'){payload.trace.publicationDate='2000-02-01';payload.trace.history=payload.trace.history.map(row=>({...row,publicationDate:'2000-02-01'}))}
 if(mode==='wrong')payload.trace.indicatorCode='wrong-code'
 if(mode==='missing')payload.trace.history=payload.trace.history.filter(row=>row.observationDate!=='1999-12-31')
 if(mode==='ambiguous')payload.trace.history.push({...structuredClone(past),value:'3'})
 if(['value','unit','source','raw'].includes(mode))for(const row of [payload.trace,...payload.trace.history]){
  if(mode==='value')row.value='9'
  if(mode==='unit')row.unit='Unit berubah'
  if(mode==='source')row.source.institution='INSTANSI BERUBAH'
  if(mode==='raw'&&row.rawFile)row.rawFile.checksumSha256='b'.repeat(64)
 }
 return payload
}
try{
 server=await createServer({root,cacheDir:path.join(root,'.artifacts/vite-browser'),server:{host:'127.0.0.1',port:0,strictPort:true}})
 await server.listen()
 const origin=`http://127.0.0.1:${server.httpServer.address().port}`
 chrome=spawn(executable,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'})
 let port
 for(let i=0;i<120;i++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port)break}catch{}await delay(100)}
 assert(port,'Owned disposable browser did not start')
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
 ws=new WebSocket(tabs.find(tab=>tab.type==='page').webSocketDebuggerUrl)
 await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})})
 let sequence=0
 const pending=new Map()
 send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method))},15000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})
 async function fulfill(event){
  if(mode==='held'){held.push(event);return}
  const url=new URL(event.request.url)
  const kind=url.pathname.endsWith('/trend/')?'trend':url.pathname.endsWith('/source-trace/')?'trace':'summary'
  if(mode==='timeout'&&kind==='trace'){held.push(event);return}
  const payload=payloadFor(url)
  await send('Fetch.fulfillRequest',{requestId:event.requestId,responseCode:mode==='error'||(mode==='partial'&&kind==='trace')?503:200,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from(JSON.stringify(payload[kind])).toString('base64')})
 }
 ws.addEventListener('message',event=>{
  const result=JSON.parse(event.data)
  if(result.method==='Runtime.exceptionThrown')errors.push(result.params.exceptionDetails.exception?.description??result.params.exceptionDetails.text)
  if(result.method==='Network.loadingFailed' && result.params.canceled)cancelledNetworks.add(result.params.requestId)
  if(result.method==='Fetch.requestPaused'){requests.push(result.params.request.url);void fulfill(result.params).catch(error=>interceptionErrors.push({networkId:result.params.networkId,error:String(error)}))}
  if(!result.id)return
  const entry=pending.get(result.id);if(!entry)return
  pending.delete(result.id);clearTimeout(entry.timer)
  if(result.error)entry.reject(new Error(JSON.stringify(result.error)));else entry.resolve(result.result)
 })
 const js=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value}
 const wait=async expression=>{for(let i=0;i<180;i++){if(await js(`Boolean(${expression})`))return;await delay(70)}throw new Error('Page condition timed out: '+expression)}
 const mark=()=>js('window.__deksiQaDocumentMarker = true')
 const go=async(route,width=1440)=>{await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await mark();await send('Page.navigate',{url:origin+route});await wait('!window.__deksiQaDocumentMarker && document.readyState === "complete" && document.fonts.status === "loaded"')}
 const ready=()=>wait('!window.__deksiQaDocumentMarker && document.querySelector("#feature-content")?.getAttribute("aria-busy") === "false"')
 const key=async(name,code)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code,...(name==='Enter'?{text:'\r',unmodifiedText:'\r'}:{})});await send('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code})}
 const shot=async name=>{const screenshot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});await writeFile(path.join(output,name),Buffer.from(screenshot.data,'base64'));screenshots.push(name)}
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://localhost:8000/api/*',requestStage:'Request'}]})
 await check('Deep link loads public detail, preserves zero, chart gap and source controls without dashboard requests',async()=>{
  await go('/indikator/inflasi');await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'0')
  assert.equal(await js('document.querySelectorAll(".fd-point").length'),2)
  assert.equal(await js('document.querySelectorAll(".fd-line").length'),2)
  assert.deepEqual(await js('[...document.querySelectorAll(".fd-axis-label")].map(e=>e.textContent)'),['2','1','0'])
  assert.equal(await js('new URL(document.querySelector(".fd-source-panel a").href).pathname'),'/indikator/inflasi/sumber')
  assert(!requests.some(url=>new URL(url).pathname==='/api/indicators/'&&!new URL(url).searchParams.has('code')))
  assert(!requests.some(url=>url.includes('/pdb/trend/')))
  await shot('detail-desktop-synthetic.png')
 })
 let historical
 await check('Native keyboard period selection and reload retain exact historical guard and value',async()=>{
  await js('document.querySelector("#fd-period").focus()');await mark();await key('End',35)
  await wait('new URLSearchParams(location.search).get("tanggal") === "1999-12-31"');await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'2')
  historical=await js('location.pathname+location.search')
  await mark();await send('Page.reload');await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'2')
  assert.equal(await js('location.pathname+location.search'),historical)
 })
 await check('Changed release metadata refuses historical context without latest fallback',async()=>{
  mode='changed';await go(historical);await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'Belum tersedia')
  assert(await js('document.querySelector(".fd-status").textContent.includes("berubah")'))
  assert.equal(await js('document.querySelector("#fd-period").value'),'')
 })
 await check('Malformed revision routes do not mount any API loader',async()=>{
  const before=requests.length
  await go('/indikator/inflasi?revisi=demo-v1')
  await wait('document.querySelector("h1")?.textContent === "Halaman tidak ditemukan."')
  assert.equal(requests.length,before)
 })
 await check('Source failure preserves summary/history, whereas all errors expose empty value and keyboard retry',async()=>{
  mode='partial';await go('/indikator/inflasi');await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'0')
  assert.equal(await js('document.querySelectorAll(".fd-point").length'),2)
  mode='error';await go('/indikator/inflasi');await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'Belum tersedia')
  assert.equal(await js('document.querySelectorAll(".fd-point").length'),0)
  mode='held';await js('document.querySelector(".fd-status button").focus()')
  assert(await js('document.activeElement.matches(".fd-status button")'))
  await key('Enter',13)
  await wait('document.querySelector("#feature-content").getAttribute("aria-busy") === "true"')
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'Belum tersedia')
  await wait('document.querySelector("#fd-period").disabled')
  for(let i=0;i<60&&held.length<3;i++)await delay(50)
  assert(held.length>=3)
  mode='ready';const queued=held;held=[];for(const event of queued)await fulfill(event)
  await ready();assert.equal(await js('document.querySelector(".fd-metric").textContent'),'0')
 })
 await check('Empty API stays empty; responsive desktop and narrow layouts retain local scrolling',async()=>{
  for(const width of [390,768,1440]){
   await go('/indikator/inflasi',width);await ready()
   const bounds=await js('({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,viewport:innerWidth})')
   assert.equal(bounds.viewport,width)
   assert(bounds.scroll<=bounds.client,JSON.stringify(bounds))
   assert(await js('document.querySelector("#fd-period").getBoundingClientRect().height >= 44'))
  }
  mode='empty';await go('/indikator/inflasi',390);await ready()
  assert.equal(await js('document.querySelector(".fd-metric").textContent'),'Belum tersedia')
  assert.equal(await js('document.querySelector("#fd-period").disabled'),true)
  await shot('detail-empty-mobile-synthetic.png')
 })
 await check('Actual dashboard → Detail → dashboard links work without login',async()=>{
  const card = `document.querySelector(${JSON.stringify('.indicator-card a[href="/indikator/inflasi"]')})`
  const back = `document.querySelector(${JSON.stringify('.fd-top a[href="/#indikator"]')})`
  mode='ready';await go('/');await wait(card)
  await js(card+'.click()');await ready()
  assert.equal(await js('location.pathname'),'/indikator/inflasi')
  await js(back+'.click()')
  await wait('document.querySelector(".hero-photo-wrap")')
  assert.equal(await js('location.pathname'),'/')
 })
 await check('Request deadline recovers both screens from a stalled source and keyboard retry restores data',async()=>{
  for(const route of ['/indikator/inflasi','/indikator/inflasi/sumber']){
   mode='timeout';held=[];await go(route);await ready()
   assert(await js('document.querySelector(".fd-status").textContent.includes("Batas waktu")'))
   const metric=route.endsWith('/sumber')?'.ft-value':'.fd-metric'
   assert.equal(await js(`document.querySelector(${JSON.stringify(metric)}).textContent`),route.endsWith('/sumber')?'Belum tersedia':'0')
   mode='ready';held=[];await js('document.querySelector(".fd-status button").focus()');await key('Enter',13)
   await ready();await wait(`document.querySelector(${JSON.stringify(metric)})?.textContent==="0"`)
  }
 })
 await check('Mixed frequency or measurement type hides graph while labelled table preserves original rows',async()=>{
  for(const scenario of ['mixed-type','mixed-frequency']){
   mode=scenario;await go('/indikator/inflasi');await ready()
   assert.equal(await js('document.querySelectorAll(".fd-line").length'),0)
   assert(await js('document.querySelector(".fd-history").textContent.includes("Jenis data atau frekuensi histori tidak konsisten")'))
   await js('document.querySelector(".fd-history details").open=true')
   assert(await js(`document.querySelector('.fd-history table').textContent.includes(${JSON.stringify(scenario==='mixed-type'?'level':'quarterly')})`))
  }
 })
 if(sourceTrace){
  let sourceCurrent,sourceHistorical,selectedQuery
  const value=()=>js('document.querySelector(".ft-value").textContent')
  const assertNoReturn=async()=>assert.equal(await js(`!!document.querySelector(${JSON.stringify('.ft-actions a[href*="tanggal="]')})`),false)
  await check('F7: keyboard Detail → Source Trace retains zero, source, unit and complete context',async()=>{
   mode='ready';await go('/indikator/inflasi');await ready()
   const target=await js('document.querySelector(".fd-source-panel a").getAttribute("href")')
   selectedQuery=new URL(target,origin).search
   await js('document.querySelector(".fd-source-panel a").focus()');await mark();await key('Enter',13);await ready()
   sourceCurrent=await js('location.pathname+location.search')
   assert.equal(sourceCurrent,target);assert.equal(await value(),'0')
   assert.equal(await js('document.querySelector("h1").textContent'),'Source Trace Data.')
   assert.equal(await js('document.querySelector(".ft-value-unit").textContent'),'Persen uji')
   assert.equal(await js('document.querySelector(".ft-value-period").textContent'),'Januari 2000')
   assert(await js('document.querySelector(".ft-summary").textContent.includes("INSTANSI UJI SINTETIS")'))
   assert(await js('document.body.textContent.includes("Formula belum tersedia")&&document.body.textContent.includes("Riwayat revisi belum tersedia")'))
   const raw=await js('[...document.querySelectorAll("a")].find(a=>a.textContent.includes("Unduh RAW"))?.href')
   assert.equal(raw,'http://localhost:8000/api/indicators/inflasi/raw-file/1/')
  })
  await check('F7: keyboard return retains all selector parameters rather than the latest URL',async()=>{
   await js('document.querySelector(".ft-actions a").focus()');await mark();await key('Enter',13);await ready()
   assert.equal(await js('location.pathname'),'/indikator/inflasi')
   assert.equal(await js('location.search'),selectedQuery)
   assert.equal(await js('document.querySelector(".fd-metric").textContent'),'0')
  })
  await check('F7: historical selection, source reload and return preserve value 2 without borrowing current RAW',async()=>{
   await js('document.querySelector("#fd-period").focus()');await mark();await key('End',35)
   await wait('new URLSearchParams(location.search).get("tanggal")==="1999-12-31"');await ready()
   const detail=await js('location.pathname+location.search')
   await mark();await js('document.querySelector(".fd-source-panel a").click()');await ready()
   sourceHistorical=await js('location.pathname+location.search')
   assert.equal(await value(),'2')
   assert.equal(await js('document.querySelector(".ft-value-period").textContent'),'Desember 1999')
   assert.equal(new URL(sourceHistorical,origin).search,new URL(detail,origin).search)
   assert.equal(await js('[...document.querySelectorAll("a")].some(a=>a.textContent.includes("Unduh RAW"))'),false)
   await mark();await send('Page.reload');await ready();assert.equal(await value(),'2')
   assert.equal(await js('location.pathname+location.search'),sourceHistorical)
   await mark();await js('document.querySelector(".ft-actions a").click()');await ready()
   assert.equal(await js('location.pathname+location.search'),detail)
   assert.equal(await js('document.querySelector(".fd-metric").textContent'),'2')
  })
  await check('F7: changed value/unit/source/release/RAW and missing/ambiguous/wrong identity refuse fallback',async()=>{
   for(const scenario of ['value','unit','source','changed','raw','missing','ambiguous','wrong']){
    mode=scenario;await go(scenario==='raw'?sourceCurrent:sourceHistorical);await ready()
    assert.equal(await value(),'Belum tersedia',scenario)
    assert(await js('!!document.querySelector(".fd-status[role=alert]")'),scenario)
    await assertNoReturn()
   }
  })
  await check('F7: partial/empty/error stay missing and native keyboard retry clears stale context while loading',async()=>{
   for(const scenario of ['partial','empty','error']){
    mode=scenario;await go(sourceCurrent);await ready()
    assert.equal(await value(),'Belum tersedia',scenario);await assertNoReturn()
   }
   mode='held';await js('document.querySelector(".fd-status button").focus()');await key('Enter',13)
   await wait('document.querySelector("#feature-content").getAttribute("aria-busy")==="true"')
   assert.equal(await value(),'Belum tersedia');await assertNoReturn()
   for(let i=0;i<60&&held.length<3;i++)await delay(50)
   assert(held.length>=3);mode='ready';const queued=held;held=[];for(const event of queued)await fulfill(event)
   await ready();assert.equal(await value(),'0')
  })
  await check('F7: unsupported revision, duplicate and incomplete selector URLs make no API requests',async()=>{
   for(const route of ['/indikator/inflasi/sumber?revisi=demo-v1','/indikator/inflasi/sumber?tanggal=2000-01-31','/indikator/inflasi/sumber'+selectedQuery+'&tanggal=2000-01-31']){
    const before=requests.length;await go(route)
    await wait('document.querySelector("h1")?.textContent==="Halaman tidak ditemukan."')
    assert.equal(requests.length,before)
   }
  })
  await check('F7: rapid navigation discards held source responses instead of leaking previous indicator data',async()=>{
   mode='held';await go(sourceCurrent)
   await wait('document.querySelector("#feature-content")?.getAttribute("aria-busy")==="true"')
   for(let i=0;i<60&&held.length<3;i++)await delay(50)
   assert(held.length>=3);const obsolete=held;held=[]
   mode='ready';await go('/indikator/pdb/sumber');await ready()
   for(const event of obsolete)try{await fulfill(event)}catch(error){assert(String(error).includes('Invalid InterceptionId'))}
   assert(await js('document.querySelector(".ft-summary").textContent.includes("PDB UJI SINTETIS")'))
   assert.equal(await js('location.pathname'),'/indikator/pdb/sumber')
   assert(await js('new URL(document.querySelector(".ft-actions a").href).pathname==="/indikator/pdb"'))
  })
  await check('F7: responsive 390/768/1440 layouts keep tables local and public controls usable',async()=>{
   for(const width of [390,768,1440]){
    await go(sourceCurrent,width);await ready()
    const bounds=await js('({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,viewport:innerWidth})')
    assert.equal(bounds.viewport,width);assert(bounds.scroll<=bounds.client,JSON.stringify(bounds))
    assert.equal(await js('document.querySelectorAll(".ft-flow li").length'),6)
    assert(await js('[...document.querySelectorAll(".source-trace-feature caption")].every(e=>getComputedStyle(e).color==="rgb(85, 85, 85)")'))
    assert(await js('[...document.querySelectorAll(".fd-table-scroll")].every(e=>getComputedStyle(e).overflowX==="auto"&&e.tabIndex===0)'))
    assert(await js('document.querySelector(".ft-actions a").getBoundingClientRect().height>=44'))
    if(width===390||width===1440){
     await js(`(()=>{const label=document.createElement('aside');label.id='qa-synthetic-label';label.style.cssText='padding:12px 24px;background:#111;color:#fff;font:12px sans-serif';label.textContent='UJI SINTETIS — bukan data ekonomi resmi. Formula dan revisi belum tersedia.';document.body.prepend(label)})()`)
     await shot(width===390?'source-mobile-synthetic.png':'source-desktop-synthetic.png')
     await js('document.querySelector("#qa-synthetic-label").remove()')
    }
   }
  })
 }
 await check('No runtime exceptions or runtime fixture requests',async()=>{
  assert.deepEqual(errors,[]);assert(requests.every(url=>!url.includes('/fixtures/')))
  await delay(100)
  for(const failure of interceptionErrors)assert(failure.error.includes('Invalid InterceptionId')&&cancelledNetworks.has(failure.networkId),'Unexplained interception error: '+JSON.stringify(failure))
 })
 const receipt={scope:sourceTrace?'F7 source functionality plus F6 regression; synthetic API only, not backend integration or aesthetic approval':'F6 regression on F7 branch; synthetic API only',checks,feature7Checks:checks.filter(name=>name.startsWith('F7:')),feature6AndSharedChecks:checks.filter(name=>!name.startsWith('F7:')),screenshots,errors,requests,expectedAbortedInterceptions:interceptionErrors,visualAcceptance:'PENDING',apiLive:'NOT_PROVEN'}
 await writeFile(path.join(output,'verification.json'),JSON.stringify(receipt,null,2))
 console.log(JSON.stringify({checks:checks.length,output,screenshots,runtimeErrors:errors.length},null,2))
}catch(error){console.error(error);await writeFile(path.join(output,`failure-${Date.now()}.json`),JSON.stringify({checks,errors,requests,failure:String(error)},null,2));process.exitCode=1}
finally{
 if(send)await send('Browser.close').catch(()=>{})
 ws?.close();chrome?.kill();await server?.close();await delay(500)
 await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:250})
}
