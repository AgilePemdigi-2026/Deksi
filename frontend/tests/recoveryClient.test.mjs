import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'

const server = await createServer({configFile:false,cacheDir:'node_modules/.vite-reset-client-unit',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(() => server.close())
const { createRecoveryClient } = await server.ssrLoadModule('/src/features/admin/recoveryClient.ts')
const token = {uid:'synthetic-user',token:'synthetic-token'}
const csrf = {body:{csrfToken:'synthetic-csrf'}}
const accepted = {status:202,body:{code:'reset_request_accepted',accepted:true}}
const complete = {body:{code:'reset_complete',authenticated:false}}
function replies(...items) {
  const calls=[]
  return {calls,fetcher:async(url,options)=>{
    calls.push({url,options})
    const item=items.shift()
    assert(item,'Unexpected transport request')
    if(typeof item==='function')return item(options)
    return new Response(item.text??JSON.stringify(item.body),{status:item.status??200,headers:{'Content-Type':item.type??'application/json'}})
  }}
}

test('Real recovery client uses CSRF and credential cookies for all three POST contracts without password trimming',async()=>{
  const mock=replies(csrf,accepted,{body:{valid:true}},complete)
  const client=createRecoveryClient('https://auth.example.test',mock.fetcher)
  await client.request('admin@example.test'); await client.check(token); await client.confirm(token,'  synthetic password  ','  synthetic password  ')
  assert.equal(mock.calls.length,4)
  assert.deepEqual(mock.calls.map(item=>new URL(item.url).pathname),['/api/auth/csrf/','/api/auth/password-reset/request/','/api/auth/password-reset/check/','/api/auth/password-reset/confirm/'])
  for(const call of mock.calls){assert.equal(call.options.credentials,'include');assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');assert.equal(new URL(call.url).search,'')}
  for(const call of mock.calls.slice(1)){assert.equal(call.options.method,'POST');assert.equal(call.options.headers['X-CSRFToken'],'synthetic-csrf')}
  assert.equal(JSON.parse(mock.calls.at(-1).options.body).newPassword,'  synthetic password  ')
})

test('Request acknowledgment requires both HTTP 202 and the exact success fields',async()=>{
  for(const item of [{status:200,body:accepted.body},{status:201,body:accepted.body},{status:202,body:{accepted:false,code:'reset_request_accepted'}},{status:202,body:{accepted:true}},{status:202,body:{accepted:'true',code:'reset_request_accepted'}}]){
    await assert.rejects(createRecoveryClient('',replies(csrf,item).fetcher).request('unknown@example.test'),error=>error.code==='invalid_response')
  }
})

test('Check and confirm cannot become success from mismatched status or malformed payloads',async()=>{
  for(const item of [{status:202,body:{valid:true}},{body:{valid:false}},{body:{valid:'true'}}])await assert.rejects(createRecoveryClient('',replies(csrf,item).fetcher).check(token),error=>error.code==='invalid_response')
  for(const item of [{status:202,body:complete.body},{body:{code:'reset_complete',authenticated:true}},{body:{authenticated:false}},{body:{code:'reset_complete'}}])await assert.rejects(createRecoveryClient('',replies(csrf,item).fetcher).confirm(token,'a','a'),error=>error.code==='invalid_response')
})

test('Only allowlisted status/code pairs are actionable and server text never becomes a client message',async()=>{
  for(const[status,code]of [[400,'invalid_reset_link'],[400,'invalid_request'],[403,'csrf_failed'],[413,'request_too_large'],[415,'unsupported_media_type'],[429,'rate_limited'],[503,'reset_unavailable']]){
    await assert.rejects(createRecoveryClient('',replies(csrf,{status,body:{code,detail:'UNTRUSTED private content'}}).fetcher).check(token),error=>error.code===code&&!error.message.includes('UNTRUSTED'))
  }
  for(const[status,code]of [[500,'invalid_reset_link'],[503,'password_validation_failed'],[400,'reset_complete'],[403,'constructor']])await assert.rejects(createRecoveryClient('',replies(csrf,{status,body:{code}}).fetcher).check(token),error=>error.code==='invalid_response')
})

test('Password errors retain only bounded allowlisted field codes, not raw server content',async()=>{
  const mock=replies(csrf,{status:400,body:{code:'password_validation_failed',fields:{newPassword:['password_unchanged','constructor','<script>private</script>',null],confirmPassword:['password_mismatch'],email:['private']}}})
  await assert.rejects(createRecoveryClient('',mock.fetcher).confirm(token,'a','a'),error=>{
    assert.equal(error.code,'password_validation_failed')
    assert.equal(JSON.stringify(error.fields),JSON.stringify({newPassword:['password_unchanged','password_invalid','password_invalid','password_invalid'],confirmPassword:['password_mismatch']}))
    return true
  })
})

test('CSRF denial clears its cache and waits for an explicit retry instead of replaying the POST',async()=>{
  const mock=replies(csrf,{status:403,body:{code:'csrf_failed'}},{body:{csrfToken:'fresh-synthetic-csrf'}},accepted)
  const client=createRecoveryClient('',mock.fetcher)
  await assert.rejects(client.request('admin@example.test'),error=>error.code==='csrf_failed')
  assert.equal(mock.calls.length,2)
  await client.request('admin@example.test')
  assert.equal(mock.calls[2].url,'/api/auth/csrf/')
  assert.equal(mock.calls[3].options.headers['X-CSRFToken'],'fresh-synthetic-csrf')
})

test('Missing or wrong-status CSRF bootstrap cannot transmit the recovery payload',async()=>{
  for(const item of [{body:{}},{status:202,body:csrf.body},{body:{csrfToken:''}}]){
    const mock=replies(item)
    await assert.rejects(createRecoveryClient('',mock.fetcher).request('admin@example.test'),error=>error.code==='invalid_response')
    assert.equal(mock.calls.length,1)
  }
})

test('HTML, invalid JSON, non-object JSON, invalid UTF-8 and oversized body all fail closed',async()=>{
  const invalidUtf8=()=>new Response(new Uint8Array([255]),{headers:{'Content-Type':'application/json'}})
  for(const item of [{type:'text/html',text:'<h1>Private failure</h1>'},{text:'not JSON'},{body:[]},{body:null},{text:' '.repeat(16*1024+1)},invalidUtf8])await assert.rejects(createRecoveryClient('',replies(csrf,item).fetcher).check(token),error=>error.code==='invalid_response'&&!error.message.includes('Private'))
})

test('Unsafe API origins fail before any network request',async()=>{
  for(const origin of ['javascript:example','https://user:password@auth.example.test','https://@auth.example.test','https:auth.example.test','https://auth.example.test\\','https://auth.example.test/?token=demo','https://auth.example.test/path','https://auth.example.test/#token',' https://auth.example.test']){
    const mock=replies()
    await assert.rejects(createRecoveryClient(origin,mock.fetcher).request('admin@example.test'),error=>error.code==='invalid_configuration')
    assert.equal(mock.calls.length,0)
  }
})

test('Unicode/escaping byte overflow is rejected before CSRF or credential transmission',async()=>{
  const mock=replies()
  await assert.rejects(createRecoveryClient('',mock.fetcher).confirm(token,'😀'.repeat(4096),'😀'.repeat(4096)),error=>error.code==='request_too_large')
  assert.equal(mock.calls.length,0)
})

test('An already aborted operation never reaches fetch',async()=>{
  const mock=replies()
  const controller=new AbortController();controller.abort()
  await assert.rejects(createRecoveryClient('',mock.fetcher).check(token,controller.signal),error=>error.code==='unavailable')
  assert.equal(mock.calls.length,0)
})

test('Timeout reaches a stalled fetch without automatically retrying it',async()=>{
  const mock=replies(options=>new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true})))
  await assert.rejects(createRecoveryClient('',mock.fetcher,25).check(token),error=>error.code==='unavailable')
  assert.equal(mock.calls.length,1)
})

test('The deadline includes body reads after successful response headers and cancels the stream',async()=>{
  let canceled=false
  const mock=replies(csrf,()=>new Response(new ReadableStream({cancel(){canceled=true}}),{headers:{'Content-Type':'application/json'}}))
  await assert.rejects(createRecoveryClient('',mock.fetcher,25).confirm(token,'a','a'),error=>error.code==='unavailable')
  assert(canceled);assert.equal(mock.calls.length,2)
})

test('Network failure during confirmation is unavailable, never success and never automatic credential replay',async()=>{
  const mock=replies(csrf,()=>{throw new TypeError('Private network location')})
  await assert.rejects(createRecoveryClient('',mock.fetcher).confirm(token,'a','a'),error=>error.code==='unavailable'&&!error.message.includes('Private'))
  assert.equal(mock.calls.length,2)
})

test('A malformed UTF-8 stream is canceled rather than left downloading after rejection',async()=>{
  let canceled=false
  const mock=replies(csrf,()=>new Response(new ReadableStream({start(controller){controller.enqueue(new Uint8Array([255]))},cancel(){canceled=true}}),{headers:{'Content-Type':'application/json'}}))
  await assert.rejects(createRecoveryClient('',mock.fetcher).check(token),error=>error.code==='invalid_response')
  assert(canceled)
})
