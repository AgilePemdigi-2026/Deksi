import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtemp, mkdir, access, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createInterface } from 'node:readline'
import { createServer } from 'vite'
import { openIsolatedBrowser } from './recovery-preview/browser.mjs'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH || process.env.TMPDIR
assert(scratch, 'An approved scratch directory is required')
const output = process.env.DEKSI_RESET_ARTIFACTS || await mkdtemp(path.join(scratch, 'deksi-reset-integration-'))
await mkdir(output, { recursive:true })
const backend = process.env.DEKSI_AUTH_BACKEND_URL
if (!backend) {
  const backendRoot = process.env.DEKSI_AUTH_BACKEND_ROOT
  const python = process.env.DEKSI_AUTH_PYTHON
  assert(backendRoot && python, 'Set the approved backend root and Python interpreter')
  await access(path.join(backendRoot, 'admin_auth/password_reset.py'))
  const env = { ...process.env, PYTHONNOUSERSITE:'1', PYTHONDONTWRITEBYTECODE:'1', DEBUG:'False', SECRET_KEY:'test-only-reset-browser-key', BPS_API_KEY:'', BPS_API_BASE_URL:'', DEKSI_AUTH_NODE:process.execPath, DEKSI_RESET_ARTIFACTS:output }
  delete env.PYTHONPATH; delete env.PYTHONHOME
  const result = spawnSync(python, [path.join(root, 'tests/reset_integration.py')], { cwd:backendRoot, env, encoding:'utf8', timeout:240000 })
  process.stdout.write(result.stdout || ''); process.stderr.write(result.stderr || '')
  if (result.error) console.error(result.error.message)
  process.exit(result.status ?? 1)
}

const scenario = process.env.DEKSI_RESET_SCENARIO
const checks = []
let app, browser, input, failure, profileRemoved = false
const oldPassword = 'SYNTHETIC-before-reset-fixture-731!'
const newPassword = '  SYNTHETIC-after-reset-fixture-947!  '
try {
  app = await createServer({ root, define:{'import.meta.env.VITE_AUTH_API_ORIGIN':JSON.stringify(backend)}, cacheDir:path.join(root,'node_modules/.vite-reset-integration'), server:{host:'127.0.0.1',port:Number(process.env.DEKSI_AUTH_FE_PORT),strictPort:true,headers:{'Referrer-Policy':'no-referrer','Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'}} })
  await app.listen()
  const origin = `http://127.0.0.1:${app.httpServer.address().port}`
  browser = await openIsolatedBrowser(scratch)
  const { js, wait, click, fill, navigate, send } = browser
  const posts = route => browser.requests.filter(item => item.method === 'POST' && new URL(item.url).pathname === `/api/auth/${route}/`)
  const outbox = async () => {
    input ??= createInterface({input:process.stdin})
    const iterator = input[Symbol.asyncIterator]()
    console.log('{"command":"outbox"}')
    let timer
    try {
      const next = await Promise.race([iterator.next(), new Promise((_, reject) => { timer=setTimeout(()=>reject(new Error('In-process outbox IPC timeout')),10000) })])
      assert(!next.done, 'Outbox parent closed')
      return JSON.parse(next.value)
    } finally { clearTimeout(timer) }
  }
  const loginReady = () => wait('document.querySelector("#login-submit") && !document.querySelector("#login-submit").disabled', 'Login form ready')
  const login = async password => {
    await fill('#identifier','integration-admin'); await fill('#password',password); await click('#login-submit')
  }
  await navigate(origin+'/admin/login'); await loginReady()
  if (scenario === 'flow') {
    await login(oldPassword)
    await wait('document.querySelector("#session-user")?.textContent === "integration-admin"', 'Initial Admin session')
  }
  const cookies = await send('Network.getCookies',{urls:[backend]})
  const oldSession = cookies.cookies.find(cookie=>cookie.name==='sessionid')
  if (scenario === 'flow') await navigate(origin+'/admin/forgot-password')
  else await click('a[href="/admin/forgot-password"]')
  await wait('document.querySelector("#recovery-request-submit")','Actual Login link opens recovery')
  await fill('#recovery-email',scenario==='disabled'?'admin@example.test':'unknown@example.test')
  await click('#recovery-request-submit')
  if (scenario === 'disabled') {
    await wait('document.querySelector("#recovery-status").textContent.includes("belum dapat dipastikan") && !document.querySelector("#recovery-request-submit").disabled','Disabled reset must fail visibly')
    assert.equal(posts('password-reset/request').length,1,'The actual form must contact Django, not the preview service')
    assert.equal(browser.responses.filter(item=>item.method==='POST'&&item.path.endsWith('/password-reset/request/')).at(-1)?.status,503)
    assert.equal(await js('Boolean(document.querySelector("#recovery-accepted"))'),false)
    assert.equal((await outbox()).count,0)
    checks.push('Actual form calls Django and fails closed when backend reset is disabled; no mail or fake accepted state')
  } else {
    await wait('document.querySelector("#recovery-accepted")','Actual request form must receive generic 202 from Django')
    assert.equal(posts('password-reset/request').length,1,'Application handler must send a reset POST')
    assert.equal((await outbox()).count,0)
    checks.push('Unknown email gets the generic accepted state through the actual form without sending email')
    await click('#recovery-edit-email'); await fill('#recovery-email','admin@example.test')
    await send('Network.setCookie',{name:'csrftoken',value:'X'.repeat(32),url:backend,path:'/',httpOnly:true,sameSite:'Lax'})
    await click('#recovery-request-submit')
    await wait('document.querySelector("#recovery-status").textContent.includes("Pemeriksaan keamanan gagal") && !document.querySelector("#recovery-request-submit").disabled','Real stale CSRF must be rejected')
    assert.equal(posts('password-reset/request').length,2,'CSRF rejection must not auto-replay')
    const beforeRequest = posts('password-reset/request').length
    await js('document.querySelector("#recovery-request-form").requestSubmit();document.querySelector("#recovery-request-form").requestSubmit()')
    await wait('document.querySelector("#recovery-accepted")','Explicit retry should refresh CSRF and reach Django')
    assert.equal(posts('password-reset/request').length,beforeRequest+1)
    const email = await outbox()
    assert.equal(email.count,1); assert(email.link,'Locmem must produce the real reset link')
    checks.push('Stale CSRF is denied; deliberate retry bootstraps fresh CSRF and duplicate submit sends one real request')
    await browser.screenshot(path.join(output,'accepted.png'))
    await navigate(email.link)
    await wait('document.querySelector("#recovery-new-password")','Generated locmem link must pass the real backend capability check')
    assert.equal(await js('location.hash'), '')
    assert.equal(await js('location.search'), '')
    assert.equal(await js('localStorage.length+sessionStorage.length'),0)
    assert(posts('password-reset/check').length>=1)
    checks.push('Real email capability opens the password form, is checked by Django and is removed from the address without browser storage')
    const confirm = async password => {
      await fill('#recovery-new-password',password); await fill('#recovery-confirm-password',password); await click('#recovery-confirm-submit')
    }
    await confirm('123')
    await wait('document.querySelector("#recovery-new-error").textContent.length > 0 && !document.querySelector("#recovery-confirm-submit").disabled','Native backend password validation must be visible')
    await confirm(oldPassword)
    await wait('document.querySelector("#recovery-new-error").textContent.includes("berbeda") && !document.querySelector("#recovery-confirm-submit").disabled','Reusing current password must be rejected')
    checks.push('Real native password validators reject weak passwords and reuse of the current password with safe field messages')
    await fill('#recovery-new-password',newPassword); await fill('#recovery-confirm-password',newPassword)
    const beforeConfirm=posts('password-reset/confirm').length
    await js('document.querySelector("#recovery-confirm-form").requestSubmit();document.querySelector("#recovery-confirm-form").requestSubmit()')
    await wait('document.querySelector("#recovery-login")','Actual confirm must complete on a committed backend response')
    assert.equal(posts('password-reset/confirm').length,beforeConfirm+1)
    assert.equal(await js('document.querySelectorAll("input[autocomplete=new-password]").length'),0)
    assert.equal(await js('Boolean(document.querySelector("#session-user"))'),false)
    await browser.screenshot(path.join(output,'complete.png'))
    checks.push('Actual confirmation commits once, clears the password inputs and never auto-logs-in')
    assert(oldSession?.httpOnly, 'Initial session must be HttpOnly')
    await send('Network.setCookie',{name:'sessionid',value:oldSession.value,url:backend,path:'/',httpOnly:true,sameSite:'Lax'})
    assert.equal(await js(`fetch(${JSON.stringify(backend+'/api/auth/session/')},{credentials:'include'}).then(r=>r.json()).then(b=>b.authenticated)`),false)
    checks.push('Separate browser control proves replay of the pre-reset session is anonymous after password replacement')
    await click('#recovery-login'); await loginReady(); await login(oldPassword)
    await wait('document.querySelector("#form-status").textContent.includes("tidak valid") && !document.querySelector("#login-submit").disabled','Old password must fail through Login form')
    await login(newPassword)
    await wait('document.querySelector("#session-user")?.textContent === "integration-admin"','New password with preserved whitespace must log in through actual form')
    assert.equal(await js('document.querySelector("#password").value.length'),0)
    checks.push('Actual Login form denies the old password and accepts the new password with whitespace preserved')
    await navigate(email.link)
    await wait('document.querySelector("#recovery-new-link")','Consumed token must not reopen the reset form')
    assert.equal(await js('document.querySelectorAll("input[autocomplete=new-password]").length'),0)
    assert.equal(await js('location.hash'), '')
    await browser.screenshot(path.join(output,'replay-denied.png'))
    await send('Page.reload')
    await wait('document.querySelector("#recovery-new-link") && !location.hash','Reload cannot resurrect the capability')
    checks.push('Reused reset link and reload without a fragment cannot recreate a valid password form')
    await navigate(origin+'/admin/forgot-password',390)
    assert.equal(await js('document.documentElement.scrollWidth<=document.documentElement.clientWidth'),true)
    checks.push('Connected recovery page remains usable at a narrow viewport without horizontal overflow')
  }
  assert.equal(await js('localStorage.length+sessionStorage.length'),0)
  assert.deepEqual(browser.runtimeErrors,[])
  for(const response of browser.responses.filter(item=>item.method==='POST'&&item.path.startsWith('/api/auth/password-reset/'))){
    assert(Object.entries(response.headers).some(([key,value])=>key.toLowerCase()==='cache-control'&&value.includes('no-store')))
    assert(Object.entries(response.headers).some(([key,value])=>key.toLowerCase()==='referrer-policy'&&value==='no-referrer'))
  }
} catch(error) {
  failure={name:error.name,message:error.message}
  process.exitCode=1
} finally {
  input?.close()
  if(browser){await browser.close();profileRemoved=true}
  if(app)await app.close()
  const receipt={scope:'Actual React application forms against real Django; synthetic accounts, in-memory test DB and locmem mail only',scenario,checks,failure,runtimeErrors:browser?.runtimeErrors||[],responses:browser?.responses.filter(item=>item.path.startsWith('/api/auth/'))||[],interception:false,capabilitiesPersisted:false,realCredentialsUsed:false,profileRemoved}
  await writeFile(path.join(output,scenario+'-receipt.json'),JSON.stringify(receipt,null,2))
  console.log(JSON.stringify({scenario,checks:checks.length,failure,profileRemoved}))
}
