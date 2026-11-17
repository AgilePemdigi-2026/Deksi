import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdtemp, rm } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'vite'

const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch, 'Set HERMES_TEST_SCRATCH to the agent-owned scratch directory')
const cache = await mkdtemp(path.join(scratch, 'deksi-bulk-api-'))
const app = await createServer({ configFile: false, root: path.resolve('.'), cacheDir: cache,
  server: { middlewareMode: true, hmr: false, ws: false } })
after(async () => { await app.close(); await rm(cache, { recursive: true, force: true }) })
const api = await app.ssrLoadModule('/src/api.ts')

const preview = { id: 'a0000000-0000-4000-8000-000000000001', status: 'preview',
  expiresAt: '2026-11-17T14:00:00Z', total: 2, eligible: 1, excluded: 1, items: [
    { id: 1, fingerprint: 'a'.repeat(64), indicator: 'uji', indicatorName: 'Uji', sourceId: 'BPS',
      period: 'Jan', value: '1.000000', unit: '%', publicationDate: '2024-01-01', rawFileId: 1,
      eligible: true, exclusionReason: null },
    { id: 2, fingerprint: 'b'.repeat(64), indicator: 'uji', indicatorName: 'Uji', sourceId: 'BPS',
      period: 'Feb', value: '2.000000', unit: '%', publicationDate: null, rawFileId: null,
      eligible: false, exclusionReason: 'RAW dan tanggal rilis tidak tersedia' },
  ] }
const result = { id: preview.id, status: 'completed', items: [
  { id: 1, status: 'published', reason: null }, { id: 2, status: 'excluded', reason: 'RAW dan tanggal rilis tidak tersedia' }],
  counts: { total: 2, eligible: 1, excluded: 1, published: 1, skipped: 0, pending: 0, unknown: 0 } }

test('preview and confirmed batch are source-bound with CSRF; status is read-only', async () => {
  const calls = []
  const previous = globalThis.fetch
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, init })
    if (url === '/api/auth/csrf/') return Response.json({ csrfToken: 'synthetic-token' })
    if (url.endsWith('/bulk-preview/')) return Response.json(preview)
    if (url.endsWith('/confirm/')) return Response.json(result)
    if (url.endsWith('/active/')) return Response.json({ batch: result })
    if (url.endsWith(`/${preview.id}/`)) return Response.json(result)
    throw new Error(`unexpected synthetic request: ${url}`)
  }
  try {
    assert.deepEqual(await api.createBulkPreview('BPS'), preview)
    assert.deepEqual(await api.confirmBulkReview('BPS', preview.id), result)
    assert.deepEqual(await api.fetchBulkReview('BPS', preview.id), result)
    assert.deepEqual(await api.fetchActiveBulkReview('BPS'), result)
    assert.equal(calls.filter(c => c.url === '/api/auth/csrf/').length, 2)
    assert.deepEqual(calls.filter(c => c.init.method === 'POST').map(c => JSON.parse(c.init.body || '{}')), [{}, { confirmed: true }])
    assert(calls.every(c => c.init.credentials === 'include'))
    assert(calls.filter(c => c.init.method === 'POST').every(c => new Headers(c.init.headers).get('X-CSRFToken') === 'synthetic-token'))
  } finally { globalThis.fetch = previous }
})

test('mismatched snapshot identity is rejected before the UI can confirm it', async () => {
  const previous = globalThis.fetch
  globalThis.fetch = async url => url === '/api/auth/csrf/' ? Response.json({ csrfToken: 'synthetic-token' }) :
    Response.json({ ...preview, items: preview.items.map(item => ({ ...item, sourceId: 'OTHER' })) })
  try { await assert.rejects(api.createBulkPreview('BPS'), /tidak valid/i) }
  finally { globalThis.fetch = previous }
})

test('source conflict does not tell Admin to blindly recreate a preview', async () => {
  const previous = globalThis.fetch
  globalThis.fetch = async url => url === '/api/auth/csrf/' ? Response.json({ csrfToken: 'synthetic-token' }) :
    new Response(null, { status: 409 })
  try {
    await assert.rejects(api.confirmBulkReview('BPS', preview.id), error =>
      error.kind === 'conflict' && /operasi sumber/i.test(error.message) && !/Muat ulang/i.test(error.message))
  } finally { globalThis.fetch = previous }
})

test('manual reconciliation is explicit and never replays confirmation', async () => {
  const previous = globalThis.fetch
  const calls = []
  const closed = { ...result, status: 'unknown', resolvedAt: '2026-11-17T15:00:00Z',
    resolvedBy: 'Admin', resolutionReason: 'Diperiksa manual' }
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, init })
    if (url === '/api/auth/csrf/') return Response.json({ csrfToken: 'synthetic-token' })
    if (url.endsWith('/reconcile/')) return Response.json(closed)
    throw new Error(`unexpected request: ${url}`)
  }
  try {
    assert.deepEqual(await api.reconcileBulkReview('BPS', preview.id, 'Diperiksa manual'), closed)
    assert.deepEqual(calls.filter(call => call.init.method === 'POST').map(call => JSON.parse(call.init.body)),
      [{ acknowledged: true, reason: 'Diperiksa manual' }])
    assert(calls.every(call => !call.url.endsWith('/confirm/')))
  } finally { globalThis.fetch = previous }
})
