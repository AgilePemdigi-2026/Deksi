import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'

const cacheDir = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH || tmpdir(), 'deksi-review-vite-'))
const vite = await createServer({ configFile: false, plugins: [react()], cacheDir, server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(async () => { await vite.close(); await rm(cacheDir, { recursive: true, force: true }) })
const api = await vite.ssrLoadModule('/src/api.ts')

test('candidate review API provides explicit source-bound operations', () => {
  assert.equal(typeof api.fetchReviewCandidates, 'function')
  assert.equal(typeof api.submitCandidateReview, 'function')
  assert.equal(typeof api.fetchAdminAnalysisResults, 'function')
  assert.equal(typeof api.submitAdminAnalysisDecision, 'function')
})

test('candidate list exposes a safe permission-specific message for revoked review access', async () => {
  const original = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ error: 'untrusted detail' }), { status: 403 })
  try {
    await assert.rejects(api.fetchReviewCandidates('BPS', 1), error =>
      error.kind === 'forbidden' && error.message.includes('izin review') && !error.message.includes('untrusted detail'))
  } finally { globalThis.fetch = original }
})

test('review panel labels source and does not imply publication', async () => {
  const { default: CandidateReview } = await vite.ssrLoadModule('/src/features/candidates/CandidateReview.tsx')
  const html = renderToStaticMarkup(createElement(CandidateReview, { sourceId: 'BPS', onClose() {} }))
  assert.match(html, /Kandidat sumber BPS/)
  assert.match(html, /Kandidat yang menunggu review belum menjadi data publik/)
  assert.doesNotMatch(html, /Kandidat belum menjadi data publik/)
  assert.doesNotMatch(html, /Ya, konfirmasi/)
})

test('review POST includes CSRF and binds source, candidate, fingerprint, and decision', async () => {
  const calls = []
  const original = globalThis.fetch
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options })
    return calls.length === 1
      ? new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' }))
      : new Response(JSON.stringify({ id: 7, status: 'published' }))
  }
  try {
    await api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', '')
    assert.equal(calls.length, 2)
    assert.equal(calls[1].url, '/api/admin/sources/BPS/candidates/7/review/')
    assert.equal(calls[1].options.headers.get('X-CSRFToken'), 'synthetic-csrf')
    assert.deepEqual(JSON.parse(calls[1].options.body), { decision: 'publish', fingerprint: 'x'.repeat(64), notes: '' })
  } finally { globalThis.fetch = original }
})

test('publication decision POST includes CSRF, version fingerprint, decision, and notes', async () => {
  const calls = []
  const original = globalThis.fetch
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options })
    return calls.length === 1
      ? new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' }))
      : new Response(JSON.stringify({ id: 8, status: 'needs_revision' }))
  }
  try {
    await api.submitAdminAnalysisDecision(
      { id: 8, fingerprint: 'y'.repeat(64) },
      'needs_revision',
      'Perlu verifikasi ulang',
    )
    assert.equal(calls.length, 2)
    assert.equal(calls[1].url, '/api/admin/analysis-results/8/decision/')
    assert.equal(calls[1].options.headers.get('X-CSRFToken'), 'synthetic-csrf')
    assert.deepEqual(JSON.parse(calls[1].options.body), {
      decision: 'needs_revision',
      fingerprint: 'y'.repeat(64),
      notes: 'Perlu verifikasi ulang',
    })
  } finally { globalThis.fetch = original }
})

test('network failure does not repeat review POST', async () => {
  let calls = 0
  const original = globalThis.fetch
  globalThis.fetch = async () => {
    calls++
    if (calls === 1) return new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' }))
    throw new Error('synthetic disconnect')
  }
  try {
    await assert.rejects(api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', ''))
    assert.equal(calls, 2)
  } finally { globalThis.fetch = original }
})

test('review failures preserve safe conflict and session/permission classifications', async () => {
  const original = globalThis.fetch
  try {
    for (const [status, kind] of [[409, 'conflict'], [401, 'unauthenticated'], [403, 'forbidden']]) {
      let calls = 0
      globalThis.fetch = async () => ++calls === 1
        ? new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' }))
        : new Response(JSON.stringify({ error: 'untrusted text' }), { status })
      await assert.rejects(api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', ''),
        error => error.kind === kind && !error.message.includes('untrusted text'))
      assert.equal(calls, 2)
    }
  } finally { globalThis.fetch = original }
})

test('a stalled CSRF bootstrap times out and cannot send a late review', async () => {
  const original = globalThis.fetch
  let resolveBootstrap, calls = 0, signal
  globalThis.fetch = async (_url, options) => {
    calls++; signal = options.signal
    return new Promise(resolve => { resolveBootstrap = resolve })
  }
  try {
    const request = api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', '', { timeoutMs: 20 })
    const outcome = await Promise.race([request.then(() => 'success', () => 'timed-out'), new Promise(resolve => setTimeout(() => resolve('hung'), 150))])
    assert.equal(outcome, 'timed-out')
    assert.equal(signal?.aborted, true)
    resolveBootstrap(new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' })))
    await new Promise(resolve => setTimeout(resolve, 20))
    assert.equal(calls, 1, 'late bootstrap completion must not send the POST')
  } finally { globalThis.fetch = original }
})

test('a late CSRF body cannot dispatch a POST after the deadline', async () => {
  const original = globalThis.fetch
  let resolveBody, calls = 0
  globalThis.fetch = async () => {
    calls++
    return { ok: true, json: () => new Promise(resolve => { resolveBody = resolve }) }
  }
  try {
    const request = api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', '', { timeoutMs: 20 })
    await assert.rejects(request)
    resolveBody({ csrfToken: 'synthetic-csrf' })
    await new Promise(resolve => setTimeout(resolve, 20))
    assert.equal(calls, 1)
  } finally { globalThis.fetch = original }
})

test('stalled POST or candidate readback body times out even if transport ignores abort', async () => {
  const original = globalThis.fetch
  try {
    let count = 0, postSignal
    globalThis.fetch = async (_url, options) => {
      count++
      if (count === 1) return new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' }))
      postSignal = options.signal
      return new Promise(() => {})
    }
    const post = api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', '', { timeoutMs: 20 })
    assert.equal(await Promise.race([post.then(() => 'success', () => 'timed-out'), new Promise(r => setTimeout(() => r('hung'), 150))]), 'timed-out')
    assert.equal(postSignal?.aborted, true)
    assert.equal(count, 2, 'no application retry')
    let readSignal
    globalThis.fetch = async (_url, options) => {
      readSignal = options.signal
      return { ok: true, json: () => new Promise(() => {}) }
    }
    const read = api.fetchReviewCandidate('BPS', 7, { timeoutMs: 20 })
    assert.equal(await Promise.race([read.then(() => 'success', () => 'timed-out'), new Promise(r => setTimeout(() => r('hung'), 150))]), 'timed-out')
    assert.equal(readSignal?.aborted, true)
    count = 0
    globalThis.fetch = async (_url, options) => {
      if (++count === 1) return new Response(JSON.stringify({ csrfToken: 'synthetic-csrf' }))
      postSignal = options.signal
      return { ok: true, status: 200, json: () => new Promise(() => {}) }
    }
    const postBody = api.submitCandidateReview('BPS', { id: 7, fingerprint: 'x'.repeat(64) }, 'publish', '', { timeoutMs: 20 })
    assert.equal(await Promise.race([postBody.then(() => 'success', () => 'timed-out'), new Promise(r => setTimeout(() => r('hung'), 150))]), 'timed-out')
    assert.equal(postSignal?.aborted, true)
    assert.equal(count, 2)
  } finally { globalThis.fetch = original }
})
