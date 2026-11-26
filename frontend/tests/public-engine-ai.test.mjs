import test from 'node:test'
import assert from 'node:assert/strict'
import * as client from '../src/features/dashboard/publicEngineAIClient.ts'

const key = '0f6c8cb8-4a5c-4f8f-8e23-5b277165f9c0'
const request = { requestKey: key, status: 'queued', period: 'Q1 2025' }

test('approved narrative requires exact matching current metric identities', () => {
  const data = { metrics: { pmtb_share: { available: true, inputDigest: 'a'.repeat(64), resultDigest: 'b'.repeat(64) },
    household_consumption_share: { available: false } } }
  const bindings = { pmtb_share: { inputDigest: 'a'.repeat(64), resultDigest: 'b'.repeat(64) } }
  assert.equal(client.matchesMetricBindings(bindings, data), true)
  assert.equal(client.matchesMetricBindings({ pmtb_share: { ...bindings.pmtb_share, resultDigest: 'c'.repeat(64) } }, data), false)
  assert.equal(client.matchesMetricBindings({}, data), false)
  assert.equal(client.matchesMetricBindings({ ...bindings, household_consumption_share: bindings.pmtb_share }, data), false)
})

test('explicit public request posts quarter and UUID with anonymous CSRF-protected transport', async () => {
  const calls = []
  const result = await client.createPublicEngineAIRequest('2025-03-31', async (url, init) => {
    calls.push({ url, init })
    return new Response(JSON.stringify({ request }), { status: 202 })
  }, async () => 'csrf-token', () => key)
  assert.equal(result.requestKey, key)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/api/public-engine-ai/requests/')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), { requestKey: key, quarter: '2025-03-31' })
  assert.equal(calls[0].init.headers['X-CSRFToken'], 'csrf-token')
  assert.equal(calls[0].init.credentials, 'include')
})

test('existing shared request may have a different key from the new visitor', async () => {
  const shared = 'deff8cb8-4a5c-4f8f-8e23-5b277165f9c0'
  const result = await client.createPublicEngineAIRequest('2025-03-31', async () =>
    new Response(JSON.stringify({ request: { ...request, requestKey: shared } })), async () => 'csrf', () => key)
  assert.equal(result.requestKey, shared)
})

test('an existing approved request returns metadata before its read-only content lookup', async () => {
  const result = await client.createPublicEngineAIRequest('2025-03-31', async () =>
    new Response(JSON.stringify({ request: { ...request, status: 'approved' } })), async () => 'csrf', () => key)
  assert.equal(result.status, 'approved')
  await assert.rejects(client.getPublicEngineAIRequest(key, async () =>
    new Response(JSON.stringify({ request: { ...request, status: 'approved' } }))), /Narasi/)
})

test('retry reads the existing request and validates statuses without creating another', async () => {
  const calls = []
  const result = await client.getPublicEngineAIRequest(key, async (url, init) => {
    calls.push({ url, init }); return new Response(JSON.stringify({ request: { ...request, status: 'approved', resultDigest: 'a'.repeat(64), narrative: '<script>untrusted</script>' } }))
  })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `/api/public-engine-ai/requests/${key}/`)
  assert.equal(calls[0].init.method, 'GET')
  assert.equal(result.status, 'approved')
  assert.equal(result.narrative, '<script>untrusted</script>')
})

test('malformed request identity and unknown status fail closed', async () => {
  await assert.rejects(client.getPublicEngineAIRequest('bad', fetch), /identitas/i)
  await assert.rejects(client.getPublicEngineAIRequest(key, async () => new Response(JSON.stringify({ request: { ...request, status: 'maybe' } }))), /respons/i)
})

test('HTTP errors preserve stale/conflict and permission distinctions', async () => {
  for (const status of [400, 403, 404, 409, 429, 503]) {
    await assert.rejects(client.createPublicEngineAIRequest('2025-03-31', async () => new Response('{}', { status }), async () => 'csrf-token', () => key))
  }
})

test('admin queue uses the authenticated route and review posts only the captured content digest', async () => {
  const digest = 'a'.repeat(64)
  const item = { id: 17, period: 'Q1 2025', resultDigest: 'b'.repeat(64), contentDigest: digest,
    snapshot: { period: 'Q1 2025' }, narrative: { summary: 'untrusted <script>text</script>' } }
  const queueCalls = []
  const queued = await client.fetchPublicEngineAIReviews(async (url, init) => {
    queueCalls.push({ url, init }); return new Response(JSON.stringify({ items: [item] }))
  })
  assert.equal(queued[0].contentDigest, digest)
  assert.equal(queueCalls[0].url, '/api/admin/public-engine-ai/')
  assert.equal(queueCalls[0].init.credentials, 'include')

  const reviewCalls = []
  await client.submitPublicEngineAIReview(item, 'approved', 'Sudah diperiksa', async (url, init) => {
    reviewCalls.push({ url, init })
    return new Response(JSON.stringify({ id: item.id, status: 'approved', contentDigest: digest }))
  }, async () => 'admin-csrf')
  assert.equal(reviewCalls[0].url, `/api/admin/public-engine-ai/${item.id}/review/`)
  assert.equal(reviewCalls[0].init.headers['X-CSRFToken'], 'admin-csrf')
  assert.deepEqual(JSON.parse(reviewCalls[0].init.body), { contentDigest: digest, decision: 'approved', notes: 'Sudah diperiksa' })
})

test('a changed snapshot and malformed review response never confirm a decision', async () => {
  const item = { id: 8, period: 'Q2 2025', resultDigest: 'b'.repeat(64), contentDigest: 'a'.repeat(64), snapshot: {}, narrative: 'review' }
  await assert.rejects(client.submitPublicEngineAIReview(item, 'approved', '', async () => new Response(JSON.stringify({ code: 'review_conflict' }), { status: 409 }), async () => 'csrf'), /Snapshot berubah/)
  await assert.rejects(client.submitPublicEngineAIReview(item, 'approved', '', async () => new Response(JSON.stringify({ id: 99, status: 'approved', contentDigest: item.contentDigest })), async () => 'csrf'), /Respons review tidak cocok/)
})

test('request retry can reuse an idempotency key rather than dispatching a fresh request identity', async () => {
  const calls = []
  await client.createPublicEngineAIRequest('2025-03-31', async (url, init) => {
    calls.push(JSON.parse(init.body)); return new Response(JSON.stringify({ request: { requestKey: key, status: 'queued', period: 'Q1 2025' } }), { status: 200 })
  }, async () => 'csrf', () => assert.fail('Should keep the original request key'), key)
  assert.equal(calls[0].requestKey, key)
})
