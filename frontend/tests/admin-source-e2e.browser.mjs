import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const root = fileURLToPath(new URL('../', import.meta.url))
const profile = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-admin-e2e-'))
const trace = []
const app = await createServer({root, configFile:false, plugins:[react()], server:{host:'127.0.0.1',port:0,strictPort:true,proxy:{'/api':{target:process.env.DEKSI_TEST_BACKEND,changeOrigin:false,configure(proxy){
  proxy.on('proxyRes',(response,request)=>trace.push({method:request.method,path:request.url.split('?')[0],status:response.statusCode,hasCookie:Boolean(request.headers.cookie)}))
}}}}})
await app.listen()
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'], {stdio:'ignore'})
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
let ws, send
try {
  let port
  for(let i=0;i<100;i++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port)break}catch{}await delay(100)}
  assert(port,'Chrome did not start')
  const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl)
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})})
  let id=0;const pending=new Map()
  ws.addEventListener('message',e=>{const r=JSON.parse(e.data);if(!r.id)return;const p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);r.error?p.reject(new Error(JSON.stringify(r.error))):p.resolve(r.result)})
  send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id,timer=setTimeout(()=>reject(new Error('CDP timeout '+method)),30000);pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params}))})
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value}
  const wait=async expression=>{for(let i=0;i<200;i++){if(await evaluate(`Boolean(${expression})`))return;await delay(60)}throw new Error('Timeout: '+expression+'; page='+await evaluate('document.body.innerText'))}
  await send('Page.enable');await send('Runtime.enable')
  await send('Page.navigate',{url:`http://127.0.0.1:${app.httpServer.address().port}/admin/sumber-data`})
  await wait('document.querySelector("input[autocomplete=username]")')
  const set=(selector,value)=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`)
  await set('input[autocomplete=username]',process.env.DEKSI_TEST_USER)
  await set('input[type=password]',process.env.DEKSI_TEST_PASS)
  await wait('Array.from(document.querySelectorAll("button")).some(x=>x.textContent.trim()==="Masuk"&&!x.disabled)')
  await evaluate('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="Masuk").click()')
  await wait('Array.from(document.querySelectorAll(".source-card")).some(x=>x.textContent.includes("Browser Fixture"))')
  await evaluate('Array.from(document.querySelectorAll(".source-card")).find(x=>x.textContent.includes("Browser Fixture")).querySelector("button").click()')
  await wait('document.querySelector(".trace-panel select") && document.querySelector(".trace-panel input")?.value === "BROWSER_FIXTURE"')
  await evaluate(`(()=>{const e=Array.from(document.querySelectorAll('.trace-panel select')).find(x=>Array.from(x.options).some(o=>o.value==='inactive'));e.value='inactive';e.dispatchEvent(new Event('change',{bubbles:true}));})()`)
  await evaluate('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="Simpan Perubahan").click()')
  await wait('Array.from(document.querySelectorAll(".source-card")).some(x=>x.textContent.includes("Browser Fixture")&&x.textContent.includes("inactive"))')
  await evaluate('Array.from(document.querySelectorAll(".source-card")).find(x=>x.textContent.includes("Browser Fixture")).querySelector("button").click()')
  await wait('document.querySelector(".trace-panel input")?.value === "BROWSER_FIXTURE"')
  await evaluate(`(()=>{const e=Array.from(document.querySelectorAll('.trace-panel select')).find(x=>Array.from(x.options).some(o=>o.value==='inactive'));e.value='active';e.dispatchEvent(new Event('change',{bubbles:true}));})()`)
  await evaluate('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="Simpan Perubahan").click()')
  await wait('Array.from(document.querySelectorAll(".source-card")).some(x=>x.textContent.includes("Browser Fixture")&&x.textContent.includes("· active"))')
  await evaluate(`Array.from(document.querySelectorAll('.source-card button')).find(x=>x.getAttribute('aria-label')==='Nonaktifkan Browser Fixture').click()`)
  await wait('Array.from(document.querySelectorAll(".source-card")).some(x=>x.textContent.includes("Browser Fixture")&&x.textContent.includes("· inactive"))')
  await evaluate(`Array.from(document.querySelectorAll('.source-card button')).find(x=>x.getAttribute('aria-label')==='Aktifkan Browser Fixture').click()`)
  await wait('Array.from(document.querySelectorAll(".source-card")).some(x=>x.textContent.includes("Browser Fixture")&&x.textContent.includes("· active"))')
  await evaluate('Array.from(document.querySelectorAll("a")).find(x=>x.textContent.trim()==="Riwayat Sinkronisasi").click()')
  await wait('document.body.innerText.includes("Browser Fixture") && document.body.innerText.includes("Berhasil")')
  assert(await evaluate('document.querySelector("tbody")?.innerText.includes("BROWSER_FIXTURE")'))
  await send('Page.navigate',{url:`http://127.0.0.1:${app.httpServer.address().port}/admin/sumber-data`})
  await wait('Array.from(document.querySelectorAll("button")).some(x=>x.textContent.trim()==="Keluar")')
  await evaluate('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="Keluar").click()')
  await wait('document.querySelector("input[autocomplete=username]")')
  console.log('PASS: browser login, deactivate, reactivate, reload and logout with real isolated Django')
} catch(e) {console.error(e);console.error('Sanitized API trace:',JSON.stringify(trace));process.exitCode=1}
finally {if(send)await send('Browser.close').catch(()=>{});ws?.close();chrome.kill();await app.close();await delay(500);await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:300})}
