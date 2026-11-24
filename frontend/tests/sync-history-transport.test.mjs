import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const vite = await createServer({ configFile: false, plugins: [react()], cacheDir: '.artifacts/sync-history-transport-test', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const { loadAdminSyncHistory } = await vite.ssrLoadModule('/src/api.ts')
const query = { page: 1, pageSize: 20 }
const ok = body => new Response(JSON.stringify(body), { status: 200 })

test('maps 401 session expiry separately from forbidden 403 with safe messages', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async () => new Response('', { status: 401 })
    await assert.rejects(loadAdminSyncHistory(query, { signal: new AbortController().signal }), /Sesi admin telah berakhir atau diperlukan/)
    globalThis.fetch = async () => new Response('', { status: 403 })
    await assert.rejects(loadAdminSyncHistory(query, { signal: new AbortController().signal }), /Anda tidak berwenang/)
  } finally { globalThis.fetch = original }
})

test('uses a single request and rejects non-auth HTTP failures without raw details', async () => {
  const original = globalThis.fetch; let calls = 0
  try {
    globalThis.fetch = async () => { calls++; return new Response('secret diagnostic', { status: 500 }) }
    await assert.rejects(loadAdminSyncHistory(query, { signal: new AbortController().signal }), /Gagal memuat riwayat sinkronisasi/)
    assert.equal(calls, 1)
  } finally { globalThis.fetch = original }
})

test('external abort is forwarded and remains an abort, not a timeout', async () => {
  const original = globalThis.fetch; const controller = new AbortController(); let received
  try {
    globalThis.fetch = (_url, init) => { received = init.signal; return new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true })) }
    const pending = loadAdminSyncHistory(query, { signal: controller.signal }); controller.abort()
    await assert.rejects(pending, error => error.name === 'AbortError')
    assert.ok(received.aborted)
  } finally { globalThis.fetch = original }
})

test('deadline covers response body reading, and fetch errors use safe network wording', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async (_url, init) => new Response(new ReadableStream({ start(controller) { init.signal.addEventListener('abort', () => controller.error(new DOMException('aborted', 'AbortError')), { once: true }) } }), { status: 200 })
    await assert.rejects(loadAdminSyncHistory(query, { signal: new AbortController().signal, timeoutMs: 20 }), /[Ww]aktu tunggu/)
    globalThis.fetch = async () => { throw new TypeError('private network detail') }
    await assert.rejects(loadAdminSyncHistory(query, { signal: new AbortController().signal }), /Koneksi ke layanan riwayat/)
  } finally { globalThis.fetch = original }
})

test('parses a successful response and does not retry', async () => {
  const original = globalThis.fetch; let calls = 0
  try {
    globalThis.fetch = async () => { calls++; return ok({ items: [], pagination: { page: 1, pageSize: 20, total: 0, hasNext: false } }) }
    assert.equal((await loadAdminSyncHistory(query, { signal: new AbortController().signal })).items.length, 0)
    assert.equal(calls, 1)
  } finally { globalThis.fetch = original }
})

test('deadline settles even when a transport ignores abort', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = () => new Promise(() => {})
    const timeout = new Promise((_, reject) => setTimeout(() => reject(Error('deadline did not settle')), 150))
    await assert.rejects(Promise.race([loadAdminSyncHistory(query, { signal: new AbortController().signal, timeoutMs: 20 }), timeout]), /[Ww]aktu tunggu/)
  } finally { globalThis.fetch = original }
})
