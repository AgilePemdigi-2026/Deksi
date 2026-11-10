import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { readFile } from 'node:fs/promises'

const root = fileURLToPath(new URL('../', import.meta.url))
const vite = await createServer({ root, configFile: false, plugins: [react()], cacheDir: process.env.DEKSI_TEST_CACHE, server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const api = await vite.ssrLoadModule('/src/api.ts')
const { labelSyncStatus } = await vite.ssrLoadModule('/src/features/sync-history/SyncHistoryPage.tsx')

test('submits exactly one confirmed BPS request using admin CSRF/session transport and request UUID', async () => {
  const calls = []
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init })
    if (String(url) === '/api/auth/csrf/') return Response.json({ csrfToken: 'offline-csrf' })
    return new Response(JSON.stringify({ id: 'job-1', status: 'queued' }), { status: 202 })
  }
  const result = await api.requestAdminBpsResync('BPS', '00000000-0000-4000-8000-000000000001')
  assert.deepEqual(result, { id: 'job-1', status: 'queued' })
  assert.equal(calls.length, 2)
  assert.equal(calls[1].url, '/api/admin/sources/BPS/resync/')
  assert.equal(calls[1].init.credentials, 'include')
  assert.equal(calls[1].init.headers.get('X-CSRFToken'), 'offline-csrf')
  assert.deepEqual(JSON.parse(calls[1].init.body), { requestId: '00000000-0000-4000-8000-000000000001' })
})

test('unknown reconciliation requires explicit reviewer confirmation and reason via admin CSRF transport', async () => {
  const calls = []
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init })
    if (String(url) === '/api/auth/csrf/') return Response.json({ csrfToken: 'offline-csrf' })
    return Response.json({ id: 'job-1', status: 'unknown' })
  }
  const result = await api.reconcileAdminResyncJob('job-1', { confirmed: true, reason: 'Sudah diperiksa secara manual.' })
  assert.equal(result.status, 'unknown')
  assert.equal(calls[1].url, '/api/admin/resync-jobs/job-1/reconcile/')
  assert.equal(calls[1].init.headers.get('X-CSRFToken'), 'offline-csrf')
  assert.deepEqual(JSON.parse(calls[1].init.body), { confirmed: true, reason: 'Sudah diperiksa secara manual.' })
})

test('unknown has a distinct label, never success or failure', () => {
  assert.equal(labelSyncStatus('unknown'), 'Tidak diketahui')
  assert.notEqual(labelSyncStatus('unknown'), labelSyncStatus('success'))
  assert.notEqual(labelSyncStatus('unknown'), labelSyncStatus('failed'))
})

test('manual reconciliation targets the job ID on a running history row', async () => {
  const source = await readFile(new URL('../src/features/sync-history/SyncHistoryPage.tsx', import.meta.url), 'utf8')
  assert.match(source, /item\.status === 'running' && item\.resyncJobId && <UnknownResolution id=\{item\.resyncJobId\}/)
  assert.doesNotMatch(source, /item\.status === 'unknown' && <UnknownResolution/)
})

test('active job is discovered after reload without submitting a new request', async () => {
  const calls = []
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init })
    return Response.json({ job: { id: '4', sourceId: 'BPS', status: 'queued', requestedAt: '2026-01-01T00:00:00Z', finishedAt: null, runId: null, message: null } })
  }
  const job = await api.fetchActiveAdminResync('BPS')
  assert.equal(job.id, '4')
  assert.equal(job.status, 'queued')
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/api/admin/sources/BPS/resync-active/')
  assert.equal(calls[0].init.method ?? 'GET', 'GET')
})
