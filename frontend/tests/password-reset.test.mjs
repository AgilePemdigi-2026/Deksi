import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const server = await createServer({configFile:false,plugins:[react()],cacheDir:'.artifacts/reset-unit-cache',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(() => server.close())
const load = name => server.ssrLoadModule('/src/' + name)

test('Review contract examples have unique negative cases and do not claim implemented endpoints', async () => {
  const contract = JSON.parse(await readFile(new URL('./fixtures/password-reset.contract.json',import.meta.url),'utf8'))
  assert.equal(contract.status,'CONTRACT_FOR_REVIEW_NOT_IMPLEMENTED')
  assert.deepEqual(contract.endpoints.map(endpoint=>endpoint.path),['/api/auth/password-reset/request/','/api/auth/password-reset/check/','/api/auth/password-reset/confirm/'])
  assert.equal(new Set(contract.negativeCases.map(item=>item.id)).size,16)
  assert.equal(contract.negativeCases.length,16)
  assert.equal(contract.proposedPolicy.automaticLogin,false)
  for(const endpoint of contract.endpoints)assert(Buffer.byteLength(JSON.stringify(endpoint.request))<=contract.proposedPolicy.requestBodyMaxBytes)
})

test('The forgot-password route renders the recovery form instead of the public dashboard', async () => {
  const { default: App } = await load('App.tsx')
  const html = renderToStaticMarkup(createElement(App, {pathname:'/admin/forgot-password'}))
  assert.match(html, /id="recovery-email"/)
  assert.match(html, /Lupa kata sandi\?/)
  assert.match(html, /href="\/admin\/login"/)
  assert.doesNotMatch(html, /class="summary"/)
})

test('Existing Login exposes a real recovery navigation link', async () => {
  const { default: App } = await load('App.tsx')
  const html = renderToStaticMarkup(createElement(App, {pathname:'/admin/login'}))
  assert.match(html, /href="\/admin\/forgot-password"/)
  assert.doesNotMatch(html, /Pemulihan kata sandi belum tersedia melalui halaman ini/)
})

test('Reset without a capability never renders password inputs or invents another page', async () => {
  const { default: App } = await load('App.tsx')
  const html = renderToStaticMarkup(createElement(App, {pathname:'/admin/reset-password/'}))
  assert.match(html, /Tautan tidak dapat digunakan\./)
  assert.match(html, /Minta tautan baru/)
  assert.doesNotMatch(html, /autocomplete="new-password"/i)
})

test('Fragment parsing is bounded, refuses duplicate credentials and does not repair malformed values', async () => {
  const { parseResetCredentials } = await load('features/admin/recovery.ts')
  assert.equal(JSON.stringify(parseResetCredentials('#uid=demo-user&token=demo-token')),JSON.stringify({uid:'demo-user',token:'demo-token'}))
  for(const fragment of ['', '#uid=demo-user', '#uid=a&uid=b&token=c', '#uid=a&token=b&token=c', '#uid=a&token=b&next=elsewhere', '#uid=<script>&token=a', '#uid=a&token=%', '#uid=a&token='+ 'x'.repeat(257), '#uid=a&token='+ 'x'.repeat(2000)])assert.equal(parseResetCredentials(fragment),null)
})

test('Explicitly disconnected recovery never returns a synthetic successful result', async () => {
  const { unavailableRecovery } = await load('features/admin/recovery.ts')
  for(const operation of [()=>unavailableRecovery.request('admin@example.test'),()=>unavailableRecovery.check({uid:'demo',token:'demo'}),()=>unavailableRecovery.confirm({uid:'demo',token:'demo'},'synthetic','synthetic')]){
    await assert.rejects(operation(),error=>error.code==='not_connected')
  }
})
