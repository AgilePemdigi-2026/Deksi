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
})

test('review panel labels source and does not imply publication', async () => {
  const { default: CandidateReview } = await vite.ssrLoadModule('/src/features/candidates/CandidateReview.tsx')
  const html = renderToStaticMarkup(createElement(CandidateReview, { sourceId: 'BPS', onClose() {} }))
  assert.match(html, /Kandidat sumber BPS/)
  assert.match(html, /Kandidat belum menjadi data publik/)
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
