import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'

export async function openIsolatedBrowser(scratch) {
  assert(scratch,'Approved scratch path required')
  const profile=await mkdtemp(path.join(scratch,'deksi-reset-browser-'))
  const chrome=spawn(process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'})
  const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms))
  let ws,send
  const runtimeErrors=[],requests=[]
  async function close(){
    if(send)await send('Browser.close').catch(()=>{})
    ws?.close();chrome.kill();await delay(400)
    await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:300})
  }
  try{
    let port
    for(let i=0;i<100;i++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port)break}catch{}await delay(100)}
    assert(port,'Owned Chrome startup failed')
    const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
    ws=new WebSocket(targets.find(item=>item.type==='page').webSocketDebuggerUrl)
    await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})})
    let sequence=0;const pending=new Map()
    ws.addEventListener('message',event=>{
      const result=JSON.parse(event.data)
      if(result.method==='Runtime.exceptionThrown')runtimeErrors.push(result.params.exceptionDetails.text)
      if(result.method==='Network.requestWillBeSent')requests.push({url:result.params.request.url,method:result.params.request.method})
      if(!result.id)return
      const item=pending.get(result.id);if(!item)return
      pending.delete(result.id);clearTimeout(item.timer)
      if(result.error)item.reject(new Error(result.error.message));else item.resolve(result.result)
    })
    send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method))},15000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})
    const js=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error('Browser expression failed');return r.result.value}
    const wait=async(expression,label)=>{for(let i=0;i<100;i++){if(await js(`Boolean(${expression})`))return;await delay(80)}throw new Error(label||'Browser condition did not become true')}
    const click=async selector=>{const p=await js(`(()=>{const element=document.querySelector(${JSON.stringify(selector)});if(!element)throw new Error('Missing control');element.scrollIntoView({block:'center',behavior:'instant'});const r=element.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);await send('Input.dispatchMouseEvent',{type:'mousePressed',...p,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',...p,button:'left',clickCount:1})}
    const fill=async(selector,value)=>{await js(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`)}
    const key=async(name,code)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code,...(name==='Enter'?{text:'\r',unmodifiedText:'\r'}:{})});await send('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code})}
    const navigate=async(url,width=1440)=>{await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await send('Page.navigate',{url});await wait('document.querySelector(".login-page") && document.fonts.status === "loaded" && document.querySelector(".hero-photo")?.complete','Recovery page failed to render')}
    const screenshot=async file=>{
      await js('window.scrollTo({top:0,behavior:"instant"})')
      await wait('Array.from(document.images).every(image=>image.complete&&image.naturalWidth>0)')
      await js('Promise.all(Array.from(document.images).map(image=>image.decode()))')
      await delay(120)
      const size=await js('({width:innerWidth,height:document.documentElement.scrollHeight})')
      const image=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,...size,scale:1}})
      await writeFile(file,Buffer.from(image.data,'base64'))
    }
    await send('Page.enable');await send('Runtime.enable');await send('Network.enable')
    return{send,js,wait,click,fill,key,navigate,screenshot,close,runtimeErrors,requests,delay}
  }catch(error){await close();throw error}
}
