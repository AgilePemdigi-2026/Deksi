import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-admin-race-'))
const app = await createServer({root, server:{host:'127.0.0.1',port:0,strictPort:true}})
await app.listen()
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'], {stdio:'ignore'})
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send
try {
  let port
  for (let i=0;i<100;i++) { try {port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port) break} catch {} await delay(100) }
  assert(port, 'Chrome did not start')
  const pages=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl)
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})})
  let id=0;const pending=new Map()
  ws.addEventListener('message',e=>{const r=JSON.parse(e.data);if(!r.id)return;const p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);r.error?p.reject(new Error(JSON.stringify(r.error))):p.resolve(r.result)})
  send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id,timer=setTimeout(()=>reject(new Error(`CDP timeout ${method}`)),30000);pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params}))})
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value}
  const wait=async expression=>{for(let i=0;i<150;i++){if(await evaluate(`Boolean(${expression})`))return;await delay(60)}throw new Error(`Timeout: ${expression}`)}
  await send('Page.enable');await send('Runtime.enable')
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    const realFetch = window.fetch.bind(window);
    const item = id => ({sourceId:id,sourceName:'Source '+id,institution:'Fixture',primaryUrl:'https://example.test/',description:'',acquisitionMethod:'file_xlsx',acquisitionMethodLabel:'File',endpointUrl:'',dataFormat:'xlsx',frequency:'monthly',updateSchedule:'',status:'active',revisionVersion:0,lastFetch:{retrievedAt:null,documentName:null,parseStatus:null}});
    const json = x => new Response(JSON.stringify(x),{status:200,headers:{'Content-Type':'application/json'}});
    window.fetch = (input,init) => {const url=String(input);if(!url.startsWith('/api/'))return realFetch(input,init);
      if(url.endsWith('/admin/session/'))return Promise.resolve(json({authenticated:true,username:'fixture',isStaff:true}));
      if(url.endsWith('/admin/sources/'))return Promise.resolve(json({sources:[item('A'),item('B')]}));
      if(url.endsWith('/acquisition-methods/'))return Promise.resolve(json({methods:[],frequencies:[]}));
      if(url.includes('/revisions/'))return Promise.resolve(json({revisions:[]}));
      if(init?.method==='PATCH'){window.writes=(window.writes||0)+1;return Promise.resolve(json({}));}
      if(url.endsWith('/sources/A/'))return new Promise(resolve=>{window.resolveA=(status='active')=>resolve(json({...item('A'),status}))});
      if(url.endsWith('/sources/B/'))return Promise.resolve(json(item('B')));
      throw new Error('Unexpected API '+url);
    };`})
  await send('Page.navigate',{url:`http://127.0.0.1:${app.httpServer.address().port}/admin/sumber-data`})
  await wait('document.querySelectorAll(".source-card").length===2')
  await evaluate('document.querySelectorAll(".source-card")[0].querySelector("button").click()')
  await wait('typeof window.resolveA === "function"')
  await evaluate('document.querySelectorAll(".source-card")[1].querySelector("button").click()')
  await wait('document.querySelector(".trace-panel input")?.value === "B"')
  await evaluate('window.resolveA()')
  await delay(200)
  assert.equal(await evaluate('document.querySelector(".trace-panel input")?.value'),'B','late A response replaced B form')
  assert.match(await evaluate('document.querySelector(".trace-panel h3")?.textContent'),/Edit Sumber B/)
  console.log('PASS: stale detail response does not replace the currently selected source')
  await evaluate(`Array.from(document.querySelectorAll('.trace-panel button')).find(x=>x.textContent==='Batal').click()`)
  await evaluate(`Array.from(document.querySelectorAll('.source-card button')).find(x=>x.getAttribute('aria-label')==='Nonaktifkan Source A').click()`)
  await wait('document.querySelector(".source-card button[aria-label]").disabled')
  await evaluate(`window.resolveA('inactive')`)
  await wait('document.querySelector("[role=alert]")?.textContent.includes("Status sumber berubah")')
  assert.equal(await evaluate('window.writes||0'),0,'stale status should never submit an update')
  console.log('PASS: stale direct status action does not submit an update')
} catch(e) {console.error(e);process.exitCode=1}
finally {if(send)await send('Browser.close').catch(()=>{});ws?.close();chrome.kill();await app.close();await delay(500);await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:300})}
