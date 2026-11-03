import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { mkdtemp, mkdir, readFile, writeFile, rm, access } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH || process.env.TMPDIR
assert(scratch, 'Set HERMES_TEST_SCRATCH or TMPDIR to an approved scratch directory')
const output = process.env.DEKSI_AUTH_ARTIFACTS || await mkdtemp(path.join(scratch, 'deksi-login-e2e-evidence-'))
const backend = process.env.DEKSI_AUTH_BACKEND_URL
if (!backend) {
  const backendRoot = process.env.DEKSI_AUTH_BACKEND_ROOT
  assert(backendRoot, 'Set DEKSI_AUTH_BACKEND_ROOT to the approved Django backend worktree')
  await access(path.join(backendRoot, 'admin_auth/views.py'))
  const python = process.env.DEKSI_AUTH_PYTHON || path.join(backendRoot, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
  const environment = { ...process.env, PYTHONNOUSERSITE:'1', PYTHONDONTWRITEBYTECODE:'1', DEBUG:'False', SECRET_KEY:'test-only-react-login-integration-key', BPS_API_KEY:'', BPS_API_BASE_URL:'', DEKSI_AUTH_NODE:process.execPath, DEKSI_AUTH_ARTIFACTS:output }
  delete environment.PYTHONPATH; delete environment.PYTHONHOME
  const result = spawnSync(python, [path.join(root, 'tests/login_integration.py')], { cwd:backendRoot, env:environment, encoding:'utf8', timeout:240000 })
  process.stdout.write(result.stdout || ''); process.stderr.write(result.stderr || '')
  if (result.error) console.error(result.error.message)
  process.exit(result.status ?? 1)
}

const scenario = process.env.DEKSI_AUTH_SCENARIO
const profile = await mkdtemp(path.join(scratch, 'deksi-login-e2e-chrome-'))
const checks = [], requests = [], responses = [], errors = []
let app, chrome, ws, send, failure, profileRemoved = false
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
try {
  await mkdir(output, {recursive:true})
  app = await createServer({ root, define:{'import.meta.env.VITE_AUTH_API_ORIGIN':JSON.stringify(backend)}, cacheDir:path.join(root,'node_modules/.vite-login-integration'), server:{host:'127.0.0.1',port:Number(process.env.DEKSI_AUTH_FE_PORT),strictPort:true} })
  await app.listen()
  const origin = `http://127.0.0.1:${app.httpServer.address().port}`
  chrome = spawn(process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'], {stdio:'ignore'})
  let port
  for(let i=0;i<100;i++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);if(port)break}catch{}await delay(100)}
  assert(port,'Isolated Chrome startup')
  const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws=new WebSocket(targets.find(item=>item.type==='page').webSocketDebuggerUrl)
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})})
  let sequence=0;const pending=new Map()
  ws.addEventListener('message',event=>{
    const result=JSON.parse(event.data)
    if(result.method==='Network.requestWillBeSent')requests.push({id:result.params.requestId,url:result.params.request.url,method:result.params.request.method})
    if(result.method==='Network.responseReceived')responses.push({url:result.params.response.url,status:result.params.response.status,mimeType:result.params.response.mimeType,method:requests.find(item=>item.id===result.params.requestId)?.method})
    if(result.method==='Runtime.exceptionThrown')errors.push(result.params.exceptionDetails.text)
    if(!result.id)return
    const item=pending.get(result.id);if(!item)return
    pending.delete(result.id);clearTimeout(item.timer)
    if(result.error)item.reject(new Error(result.error.message));else item.resolve(result.result)
  })
  send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method))},15000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})
  const js=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error('Browser evaluation failed');return result.result.value}
  const wait=async(expression,label)=>{for(let i=0;i<100;i++){if(await js(`Boolean(${expression})`))return;await delay(100)}throw new Error(label || 'Browser condition timed out')}
  const click=async selector=>{const point=await js(`(()=>{const element=document.querySelector(${JSON.stringify(selector)});if(!element)throw new Error('Missing control');element.scrollIntoView({block:'center'});const r=element.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);await send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1})}
  const fill=async(identifier,password)=>js(`(()=>{for(const[id,value]of Object.entries(${JSON.stringify({identifier,password})})){const field=document.getElementById(id);field.value=value;field.dispatchEvent(new Event('input',{bubbles:true}));}})()`)
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable')
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false})
  await send('Page.navigate',{url:origin+'/admin/login'})
  await wait('document.querySelector("#login-submit") && !document.querySelector("#login-submit").disabled','Form must become ready')
  const loginResponses=()=>responses.filter(item=>item.method==='POST'&&item.url.endsWith('/api/auth/login/'))
  const rejectedLogin=async(identifier,password,code,status)=>{
    const before=loginResponses().length
    await fill(identifier,password);await click('#login-submit')
    for(let i=0;i<100&&loginResponses().length===before;i++)await delay(100)
    assert.equal(loginResponses().length,before+1)
    assert.equal(loginResponses().at(-1).status,status)
    await wait(`document.querySelector('#form-status').textContent.includes(${JSON.stringify(code)}) && !document.querySelector('#login-submit').disabled`,'Auth rejection must be visible and usable')
    assert.equal(await js('Boolean(document.querySelector("#session-user"))'),false)
    return js('document.querySelector("#form-status").textContent')
  }
  if(scenario==='denials'){
    const messages=[]
    for(const [id,pw]of [['integration-admin','SYNTHETIC-wrong'],['integration-member','SYNTHETIC-integration-fixture-only-731!'],['integration-inactive','SYNTHETIC-integration-fixture-only-731!']])messages.push(await rejectedLogin(id,pw,'tidak valid',401))
    assert.equal(new Set(messages).size,1)
    checks.push('Wrong password, inactive and nonstaff accounts are denied through the real form with the same safe message')
    await send('Network.setCookie',{name:'csrftoken',value:'X'.repeat(32),url:backend,path:'/',httpOnly:true,sameSite:'Lax'})
    await rejectedLogin('integration-admin','SYNTHETIC-integration-fixture-only-731!','Pemeriksaan keamanan gagal',403)
    checks.push('A stale CSRF is rejected without automatic credential replay; the next deliberate submit can refresh it')
  }
  await fill(scenario==='denials'?' ADMIN@example.test ':'integration-admin','SYNTHETIC-integration-fixture-only-731!')
  if(scenario==='duplicate')await js('document.querySelector("#login-form").requestSubmit();document.querySelector("#login-form").requestSubmit()')
  else await click('#login-submit')
  for(let i=0;i<100&&!requests.some(item=>item.method==='POST'&&item.url.endsWith('/api/auth/login/'));i++)await delay(100)
  assert(requests.some(item=>item.method==='POST'&&item.url.endsWith('/api/auth/login/')),'Real Login button must send an auth POST; disconnected submit is not login')
  await wait('document.querySelector("#session-user")?.textContent === "integration-admin"','Form must show the server-confirmed Admin session')
  assert(requests.some(item=>item.url.endsWith('/api/auth/csrf/')),'CSRF bootstrap must be performed by application')
  const state=await js(`fetch(${JSON.stringify(backend+'/api/auth/session/')},{credentials:'include'}).then(r=>r.json()).then(body=>({authenticated:body.authenticated,isAdmin:body.user?.isAdmin}))`)
  assert.equal(state.authenticated,true);assert.equal(state.isAdmin,true)
  assert.equal(await js('document.getElementById("password").value'), '')
  assert.equal(await js('localStorage.length + sessionStorage.length'),0)
  assert.deepEqual(errors,[])
  checks.push('Actual UI button bootstraps CSRF, submits credentials and creates a server-confirmed Admin session')
  if(scenario==='duplicate'){
    assert.equal(requests.filter(item=>item.method==='POST'&&item.url.endsWith('/api/auth/login/')).length,1)
    checks.push('Two immediate form submissions create only one login request')
  }
  if(scenario==='denials'){
    await click('#auth-logout')
    await wait('!document.querySelector("#session-user") && !document.querySelector("#login-submit").disabled','Logout after CSRF recovery')
    await rejectedLogin('integration-admin','SYNTHETIC-wrong','tidak valid',401)
    await rejectedLogin('integration-admin','SYNTHETIC-wrong','Terlalu banyak',429)
    await rejectedLogin('integration-admin','SYNTHETIC-integration-fixture-only-731!','Terlalu banyak',429)
    checks.push('Actual form displays the fifth-failure lockout and cannot bypass it with a correct password')
  }
  if (scenario === 'logout') {
    for(let reload=0;reload<3;reload++){
      await js('window.__qaPreviousDocument = true')
      await send('Page.reload')
      await wait('window.__qaPreviousDocument !== true && performance.getEntriesByType("navigation")[0]?.type === "reload" && document.querySelector("#session-user")?.textContent === "integration-admin"','Reload must restore server session')
    }
    checks.push('Page reload restores the authenticated identity from the server')
    assert(await js('Boolean(document.querySelector("#auth-logout"))'),'Authenticated session must expose logout control')
    const cookies = await send('Network.getCookies',{urls:[backend]})
    const session = cookies.cookies.find(cookie=>cookie.name==='sessionid')
    assert(session?.httpOnly)
    await click('#auth-logout')
    await wait('!document.querySelector("#session-user") && !document.querySelector("#login-submit").disabled','Logout must restore anonymous form')
    assert(requests.some(item=>item.method==='POST'&&item.url.endsWith('/api/auth/logout/')))
    assert.equal(await js(`fetch(${JSON.stringify(backend+'/api/auth/session/')},{credentials:'include'}).then(r=>r.json()).then(body=>body.authenticated)`),false)
    await send('Network.setCookie',{name:'sessionid',value:session.value,url:backend,path:'/',httpOnly:true,sameSite:'Lax'})
    assert.equal(await js(`fetch(${JSON.stringify(backend+'/api/auth/session/')},{credentials:'include'}).then(r=>r.json()).then(body=>body.authenticated)`),false)
    checks.push('Actual logout button uses fresh CSRF and invalidates the old cookie on the backend')
  }
} catch(error) { failure={name:error.name,message:error.message};process.exitCode=1 }
finally {
  if(send){try{const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});await writeFile(path.join(output,scenario+'.png'),Buffer.from(shot.data,'base64'))}catch{}await send('Browser.close').catch(()=>{})}
  ws?.close();chrome?.kill();if(app)await app.close();await delay(500)
  try{await rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:300});profileRemoved=true}catch{}
  const receipt={scope:'Actual application form against real Django; synthetic accounts/in-memory DB',scenario,checks,failure,runtimeErrors:errors,authResponses:responses.filter(item=>item.url.includes('/api/auth/')),authRequestCount:requests.filter(item=>item.url.includes('/api/auth/')).length,interception:false,profileRemoved}
  await writeFile(path.join(output,scenario+'-receipt.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt,null,2))
}
