import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'

const vite = await createServer({configFile:false, cacheDir:'.artifacts/source-status-unit', server:{middlewareMode:true, hmr:false, ws:false}, appType:'custom'})
after(() => vite.close())
const api = await vite.ssrLoadModule('/src/api.ts')

test('admin status update bootstraps CSRF and sends it in the mutation header', async () => {
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({url, init})
    return new Response(JSON.stringify(calls.length === 1 ? {csrfToken:'synthetic-csrf'} : {source:{status:'inactive'}}))
  }
  try {
    const result = await api.updateAdminSource('BPS', {status:'inactive', expectedRevision:0})
    assert.equal(result.source.status, 'inactive')
    assert.equal(calls[0].url, '/api/auth/csrf/')
    assert.equal(calls[1].url, '/api/admin/sources/BPS/update/')
    assert.equal(calls[1].init.headers.get('X-CSRFToken'), 'synthetic-csrf')
    assert.deepEqual(JSON.parse(calls[1].init.body), {status:'inactive', expectedRevision:0})
    assert.equal(calls[1].init.credentials, 'include')
    assert.equal(calls.length, 2)
  } finally { globalThis.fetch = original }
})

test('admin status update does not submit when CSRF bootstrap fails', async () => {
  const original = globalThis.fetch
  let calls = 0
  globalThis.fetch = async () => { calls++; return new Response('', {status:500}) }
  try {
    await assert.rejects(api.updateAdminSource('BPS', {status:'inactive', expectedRevision:0}), /Token keamanan/)
    assert.equal(calls, 1)
  } finally { globalThis.fetch = original }
})

test('admin logout fails closed on server failure and never replays the request', async () => {
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({url, init})
    return calls.length === 1
      ? new Response(JSON.stringify({csrfToken:'synthetic-csrf'}))
      : new Response('{}', {status:503})
  }
  try {
    await assert.rejects(api.adminLogout())
    assert.deepEqual(calls.map(call => call.url), ['/api/auth/csrf/', '/api/auth/logout/'])
    assert.equal(calls[1].init.headers['X-CSRFToken'], 'synthetic-csrf')
  } finally { globalThis.fetch = original }
})

test('admin logout confirms server session before reporting success', async () => {
  const original = globalThis.fetch
  const calls = []
  const bodies = [{csrfToken:'synthetic-csrf'}, {authenticated:false,user:null}, {authenticated:true,user:{id:1,username:'synthetic',isAdmin:true}}]
  globalThis.fetch = async (url, init) => {
    calls.push({url, init})
    return new Response(JSON.stringify(bodies.shift()))
  }
  try {
    await assert.rejects(api.adminLogout())
    assert.deepEqual(calls.map(call => call.url), ['/api/auth/csrf/', '/api/auth/logout/', '/api/auth/session/'])
  } finally { globalThis.fetch = original }
})

test('feedback status update still uses the current CSRF bootstrap', async () => {
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({url, init})
    return new Response(JSON.stringify(calls.length === 1 ? {csrfToken:'current-token'} : {feedback:{id:1}, csrfToken:'current-token'}))
  }
  try {
    await api.updateAdminFeedbackStatus(1, {status:'resolved', notes:'', csrfToken:'old-token'})
    assert.equal(calls[1].url, '/api/admin/feedback/1/status/')
    assert.equal(calls[1].init.headers.get('X-CSRFToken'), 'current-token')
    assert.equal(calls[1].init.credentials, 'include')
  } finally { globalThis.fetch = original }
})

test('history loader uses admin endpoint and forwards cancellation and filters', async () => {
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({url, init})
    return new Response(JSON.stringify({items:[],pagination:{page:1,pageSize:20,total:0,hasNext:false}}))
  }
  const controller = new AbortController()
  try {
    const result = await api.loadAdminSyncHistory({page:1,pageSize:20,sourceId:'BPS',status:'failed'}, {signal:controller.signal})
    assert.equal(result.items.length, 0)
    assert.match(calls[0].url, /^\/api\/admin\/sync-history\/\?/)
    assert.match(calls[0].url, /sourceId=BPS/)
    assert.equal(calls[0].init.signal.aborted, false)
    controller.abort()
    assert.equal(calls[0].init.signal.aborted, true)
    assert.equal(calls[0].init.credentials, 'include')
  } finally { globalThis.fetch = original }
})
