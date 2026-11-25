import assert from 'node:assert/strict'
import test, { after } from 'node:test'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { mkdtemp, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch, 'Set HERMES_TEST_SCRATCH to the agent-owned scratch directory')
const cacheDir = await mkdtemp(path.join(scratch, 'deksi-ai-narratives-'))
const vite = await createServer({ root, configFile: false, plugins: [react()], cacheDir,
  server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(async () => { await vite.close(); await rm(cacheDir, { recursive: true, force: true }) })
const api = await vite.ssrLoadModule('/src/features/ai-narratives/api.ts')

const factPackage = {
  schemaVersion: 'deksi.ai-facts.v1', methodVersion: 'pdb-yoy-facts.v1', inputDigest: 'b'.repeat(64),
  selection: { indicatorCode: 'pdb', observationId: 11, comparisonObservationId: null }, derivedMetrics: [],
  facts: { current: { observationId: 11, indicatorCode: 'pdb', indicatorName: 'PDB UJI SINTETIS',
    value: '0.000000', unit: '%', period: 'Q1 2025', observationDate: '2025-03-31', frequency: 'quarterly',
    dataType: 'yoy', publicationDate: null, source: { sourceId: 'BPS', sourceName: 'BPS UJI SINTETIS',
      institution: 'BPS UJI SINTETIS', primaryUrl: null }, publicationStatus: 'reviewed_published',
    officialVerification: 'unassessed', evidence: { status: 'integrity_ok', rawFileId: 7,
      checksumSha256: 'a'.repeat(64), fileSizeBytes: 1, retrievedAt: '2025-04-02T00:00:00+00:00' },
    sourceTracePath: '/api/indicators/pdb/source-trace/?observationDate=2025-03-31&frequency=quarterly&dataType=yoy&sourceId=BPS' }, comparison: null },
  comparisons: [], missingData: [], limitations: ['Nilai historis terbatas'],
}
const draft = { id: 8, requestKey: '10000000-0000-4000-8000-000000000001', generationStatus: 'ready', reviewStatus: 'pending', factPackage, inputDigest: 'b'.repeat(64), contentDigest: 'c'.repeat(64), requestedModel: 'model', reportedModel: null, promptVersion: 'p1', validatorVersion: 'v1', narrative: { summary: '<img src=x onerror=alert(1)>', meaning: 'Makna', comparison: null, limitations: 'Terbatas', factRefs: ['current'] }, errorCode: null, errorMessage: null, createdAt: '2026-04-02', startedAt: null, finishedAt: null, parentId: null, active: true, reconciledAt: null, review: null }
const page = { items: [draft], page: 1, pageSize: 20, total: 1, hasNext: false }
const capabilities = { canRead: true, canGenerate: true, canReview: true, generationConfigured: true }
const uuid = '10000000-0000-4000-8000-000000000001'

function stubFetch(handler, { autoCsrf = true } = {}) {
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, init })
    if (autoCsrf && url === '/api/auth/csrf/') return Response.json({ csrfToken: 'synthetic-csrf' })
    return handler(url, init, calls)
  }
  return { calls, restore: () => { globalThis.fetch = original } }
}

test('GET APIs use exact read-only routes and validate capability and pagination envelopes', async () => {
  const stub = stubFetch(url => url.endsWith('/capabilities/') ? Response.json(capabilities) :
    url.endsWith('/observations/?page=1') ? Response.json({ items: [{ id: 11, value: '0.000000', unit: '%', period: 'Q1 2025', observationDate: '2025-03-31', publicationDate: null }], page: 1, pageSize: 20, total: 1, hasNext: false }) :
    url.endsWith('/lookup/?requestKey=' + uuid) ? Response.json({ draft }) :
    url.endsWith('/8/') ? Response.json({ draft }) : Response.json(page))
  try {
    assert.deepEqual(await api.fetchNarrativeCapabilities(), capabilities)
    assert.equal((await api.fetchNarrativeObservations(1)).items[0].value, '0.000000')
    assert.equal((await api.fetchNarrativeDrafts(1)).items[0].id, 8)
    assert.equal((await api.fetchNarrativeDraft(8)).draft.id, 8)
    assert.equal((await api.lookupNarrativeRequest(uuid)).draft.id, 8)
    assert.deepEqual(stub.calls.map(call => call.url), [
      '/api/admin/ai-narratives/capabilities/', '/api/admin/ai-narratives/observations/?page=1',
      '/api/admin/ai-narratives/?page=1', '/api/admin/ai-narratives/8/',
      `/api/admin/ai-narratives/lookup/?requestKey=${uuid}`,
    ])
    assert(stub.calls.every(call => !call.init.method || call.init.method === 'GET'))
  } finally { stub.restore() }
})

test('generation uses exact payload and request key; accepted response must match it', async () => {
  const stub = stubFetch((url, init) => Response.json({ draft: { ...draft, requestKey: JSON.parse(init.body).requestKey } }, { status: 202 }))
  try {
    const response = await api.requestNarrativeDraft({ requestKey: uuid, observationId: 11, comparisonId: null, parentId: null })
    assert.equal(response.draft.requestKey, uuid)
    const post = stub.calls.find(call => call.init.method === 'POST')
    assert.equal(post.url, '/api/admin/ai-narratives/')
    assert.deepEqual(JSON.parse(post.init.body), { requestKey: uuid, observationId: 11, comparisonId: null, parentId: null })
    assert.equal(new Headers(post.init.headers).get('X-CSRFToken'), 'synthetic-csrf')
  } finally { stub.restore() }
})

test('review and reconcile bind digest, exact decisions, required notes, and never expose server error text', async () => {
  const stub = stubFetch(url => {
    if (url.endsWith('/review/')) return Response.json({ draft: { ...draft, reviewStatus: 'approved', review: { decision: 'approved', notes: '', reviewedAt: '2026-04-03', contentDigest: draft.contentDigest } } })
    if (url.endsWith('/reconcile/')) return Response.json({ draft: { ...draft, generationStatus: 'unknown', reconciledAt: '2026-04-03' } })
    return new Response(JSON.stringify({ code: 'forbidden', error: 'UNTRUSTED SECRET' }), { status: 403 })
  })
  try {
    await api.reviewNarrativeDraft(8, { contentDigest: draft.contentDigest, decision: 'approved', notes: '' })
    await api.reconcileNarrativeDraft(8, { acknowledged: true, notes: 'Sudah diperiksa' })
    assert.deepEqual(JSON.parse(stub.calls.find(call => call.url.endsWith('/review/')).init.body), { contentDigest: draft.contentDigest, decision: 'approved', notes: '' })
    assert.deepEqual(JSON.parse(stub.calls.find(call => call.url.endsWith('/reconcile/')).init.body), { acknowledged: true, notes: 'Sudah diperiksa' })
    await assert.rejects(api.fetchNarrativeCapabilities(), error => !error.message.includes('UNTRUSTED SECRET'))
  } finally { stub.restore() }
  await assert.rejects(api.reviewNarrativeDraft(8, { contentDigest: '', decision: 'needs_revision', notes: ' ' }), /digest|catatan/i)
})

test('malformed DTOs, denied capability, and malformed empty lookup fail closed', async () => {
  let stub = stubFetch(url => url.endsWith('/capabilities/') ? Response.json({ ...capabilities, canGenerate: 'yes' }) : Response.json({ items: [], page: 2, pageSize: 20, total: 0, hasNext: false }))
  try { await assert.rejects(api.fetchNarrativeCapabilities(), /tidak valid/i); await assert.rejects(api.fetchNarrativeDrafts(1), /tidak valid/i) }
  finally { stub.restore() }
  stub = stubFetch(url => url.includes('/lookup/') ? Response.json({ draft: null }) : new Response(null, { status: 403 }))
  try {
    await assert.rejects(api.fetchNarrativeCapabilities(), error => !/UNTRUSTED/.test(error.message))
    assert.deepEqual(await api.lookupNarrativeRequest(uuid), { draft: null })
  } finally { stub.restore() }
})

test('deadline covers response body parsing and does not POST after CSRF bootstrap abort', async () => {
  const stub = stubFetch(async (url, init) => {
    if (url === '/api/auth/csrf/') return new Promise(resolve => init.signal.addEventListener('abort', () => resolve(new Response('{}')), { once: true }))
    return Response.json({ draft })
  }, { autoCsrf: false })
  try {
    await assert.rejects(api.requestNarrativeDraft({ requestKey: uuid, observationId: 11, comparisonId: null, parentId: null }, { timeoutMs: 5 }))
    assert.equal(stub.calls.filter(call => call.init.method === 'POST').length, 0)
  } finally { stub.restore() }
})

test('deadline includes response-body parsing after the POST', async () => {
  const stub = stubFetch((url, init) => ({
    ok: true,
    status: 202,
    json: () => new Promise(resolve => init.signal.addEventListener('abort', () => resolve({ draft }), { once: true })),
  }))
  try {
    await assert.rejects(api.requestNarrativeDraft({ requestKey: uuid, observationId: 11, comparisonId: null, parentId: null }, { timeoutMs: 5 }))
    assert.equal(stub.calls.filter(call => call.init.method === 'POST').length, 1)
  } finally { stub.restore() }
})

test('panel fails closed without an automatic request; narrative text is escaped by React', async () => {
  const { default: Panel, NarrativeText } = await vite.ssrLoadModule('/src/features/ai-narratives/AiNarrativesPanel.tsx')
  let calls = 0
  const previous = globalThis.fetch
  globalThis.fetch = async () => { calls++; throw new Error('unexpected request') }
  try {
    const html = renderToStaticMarkup(createElement(Panel))
    const text = renderToStaticMarkup(createElement(NarrativeText, { value: draft.narrative.summary }))
    assert.match(html, /Narasi AI/)
    assert.match(html, /Izin belum diketahui/)
    assert.equal(calls, 0)
    assert.match(text, /&lt;img src=x onerror=alert\(1\)&gt;/)
    assert.doesNotMatch(text, /<img/)
  } finally { globalThis.fetch = previous }
})
