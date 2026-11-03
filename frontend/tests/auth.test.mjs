import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'

const server = await createServer({configFile:false,cacheDir:'node_modules/.vite-auth-unit',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(() => server.close())
const { createAuthClient, AuthError } = await server.ssrLoadModule('/src/features/admin/auth.ts')
const admin = {id:1,username:'synthetic-admin',isAdmin:true}
const signedIn = {authenticated:true,user:admin,csrfToken:'rotated-synthetic-csrf-token'}
function replies(...values) {
  const calls = []
  return {calls,fetcher:async (url,options) => {
    calls.push({url,options})
    const value=values.shift()
    assert(value,'Unexpected request')
    return new Response(value.text ?? JSON.stringify(value.body),{status:value.status ?? 200,headers:{'Content-Type':value.text?'text/html':'application/json'}})
  }}
}

test('Native session parsing requires a server-confirmed Admin and credentialed no-store requests', async () => {
  const mock=replies({body:{authenticated:false,user:null}},{body:{authenticated:true,user:admin}})
  const client=createAuthClient('https://auth.example.test',mock.fetcher)
  assert.equal(await client.session(),null)
  assert.equal((await client.session()).username,admin.username)
  for(const call of mock.calls){assert.equal(call.options.credentials,'include');assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');assert.equal(call.options.method,'GET')}
})

test('Login preserves password bytes, rotates CSRF for logout and bootstraps again for a new login', async () => {
  const mock=replies({body:{csrfToken:'initial-synthetic-token'}},{body:signedIn},{body:{authenticated:true,user:admin}},{body:{authenticated:false,user:null}},{body:{authenticated:false,user:null}},{body:{csrfToken:'second-synthetic-token'}},{body:signedIn},{body:{authenticated:true,user:admin}})
  const client=createAuthClient('https://auth.example.test',mock.fetcher)
  await client.login('synthetic-admin','  SYNTHETIC password  ')
  await client.logout()
  await client.login('admin@example.test','fixture')
  assert.equal(JSON.parse(mock.calls[1].options.body).password,'  SYNTHETIC password  ')
  assert.equal(mock.calls[1].options.headers['X-CSRFToken'],'initial-synthetic-token')
  assert.equal(mock.calls.find(call=>call.url.endsWith('/logout/')).options.headers['X-CSRFToken'],'rotated-synthetic-csrf-token')
  assert.equal(mock.calls.filter(call=>call.url.endsWith('/csrf/')).length,2)
  for(const call of mock.calls)assert.equal(new URL(call.url).search,'')
})

test('Credential, permission, validation and throttling errors expose safe messages rather than server text', async () => {
  for(const [status,code]of [[401,'invalid_credentials'],[403,'forbidden'],[400,'invalid_request'],[429,'rate_limited']]){
    const mock=replies({status,body:{code,error:'UNTRUSTED-SERVER-CONTENT <script>example</script>'}})
    await assert.rejects(createAuthClient('',mock.fetcher).session(),error=>error instanceof AuthError&&error.code===code&&error.status===status&&!error.message.includes('UNTRUSTED'))
  }
})

test('Invalid success payloads never invent an authenticated user', async () => {
  for(const body of [{},{authenticated:true,user:{...admin,isAdmin:false}},{authenticated:true,user:{...admin,id:'1'}},{authenticated:false,user:admin},{authenticated:true,user:{...admin,username:''}}]){
    await assert.rejects(createAuthClient('',replies({body}).fetcher).session(),error=>error.code==='invalid_response')
  }
})

test('HTML errors and network failures never become fake credential rejection or success', async () => {
  await assert.rejects(createAuthClient('',replies({status:500,text:'<h1>Private upstream error</h1>'}).fetcher).session(),error=>error.code==='invalid_response'&&!error.message.includes('Private'))
  await assert.rejects(createAuthClient('',async()=>{throw new TypeError('Private network URL')}).session(),error=>error.code==='unavailable'&&!error.message.includes('Private'))
})

test('CSRF rejection clears only the cached token and never automatically replays login', async () => {
  const mock=replies({body:{csrfToken:'old-token'}},{status:403,body:{code:'csrf_failed'}},{body:{csrfToken:'new-token'}},{body:signedIn},{body:{authenticated:true,user:admin}})
  const client=createAuthClient('',mock.fetcher)
  await assert.rejects(client.login('synthetic','fixture'),error=>error.code==='csrf_failed')
  assert.equal(mock.calls.length,2)
  await client.login('synthetic','fixture')
  assert.equal(mock.calls[2].url,'/api/auth/csrf/')
  assert.equal(mock.calls[3].options.headers['X-CSRFToken'],'new-token')
})

test('A missing CSRF bootstrap token prevents credential transmission', async () => {
  const mock=replies({body:{}})
  await assert.rejects(createAuthClient('',mock.fetcher).login('synthetic','fixture'),error=>error.code==='invalid_response')
  assert.equal(mock.calls.length,1)
})

test('A false logout response never claims that an authenticated session ended', async () => {
  const mock=replies({body:{csrfToken:'synthetic'}},{body:signedIn})
  await assert.rejects(createAuthClient('',mock.fetcher).logout(),error=>error.code==='invalid_response')
})

test('Unsafe auth-origin configuration fails closed without making a request', async () => {
  for(const origin of ['javascript:example','https://user:fixture@auth.example.test','https://@auth.example.test','https:auth.example.test','https://auth.example.test\\',' https://auth.example.test','https://auth.example.test/?token=fixture','https://auth.example.test/path','https://auth.example.test/#fragment']){
    let requested=false
    const client=createAuthClient(origin,async()=>{requested=true;return new Response(JSON.stringify({authenticated:false,user:null}))})
    await assert.rejects(client.session(),error=>error.code==='invalid_configuration')
    assert.equal(requested,false)
  }
})

test('A server failure carrying a credential-error code is not mistaken for wrong credentials', async () => {
  await assert.rejects(createAuthClient('',replies({status:500,body:{code:'invalid_credentials'}}).fetcher).session(),error=>error.code==='invalid_response'&&error.status===500)
})

test('Cancellation reaches fetch without leaving an uncancelled request', async () => {
  const controller=new AbortController()
  const client=createAuthClient('',async(_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true})))
  const pending=client.session(controller.signal)
  controller.abort()
  await assert.rejects(pending,error=>error.code==='unavailable')
})

test('Login is not confirmed when the browser does not retain the server session', async () => {
  const mock=replies({body:{csrfToken:'synthetic'}},{body:signedIn},{body:{authenticated:false,user:null}})
  await assert.rejects(createAuthClient('',mock.fetcher).login('synthetic','fixture'),error=>error.code==='invalid_response')
})

test('Logout confirmation rejects a server session that is still authenticated', async () => {
  const mock=replies({body:{csrfToken:'synthetic'}},{body:{authenticated:false,user:null}},{body:{authenticated:true,user:admin}})
  await assert.rejects(createAuthClient('',mock.fetcher).logout(),error=>error.code==='invalid_response')
})
