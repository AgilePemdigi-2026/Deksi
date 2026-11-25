import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { engineFixture } from './economic-engine-fixtures.mjs'

const vite = await createServer({ configFile: false, plugins: [react()], cacheDir: '.artifacts/vite-narrative-tests',
  server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const client = await vite.ssrLoadModule('/src/features/dashboard/engineNarrativePreviewClient.ts')
const engine = await vite.ssrLoadModule('/src/features/dashboard/economicEngineClient.ts')
const component = await vite.ssrLoadModule('/src/features/dashboard/EngineNarrativePreview.tsx')
function fixture() {
  const packet = engineFixture(), data = engine.parseGdp(packet)
  return { data, body: { schemaVersion: 'deksi.local-engine-narrative.v1', status: 'draft_preview',
    humanApproval: false, productionPublication: false, workflowStateSimulated: true,
    period: 'Q1 2025', model: 'gemini-synthetic-test', requestSha256: 'd'.repeat(64), responseSha256: 'e'.repeat(64),
    metricsBinding: Object.fromEntries(Object.entries(data.metrics).map(([id, metric]) => [id, {
      value: metric.value, unit: metric.unit, inputDigest: metric.inputDigest, resultDigest: metric.resultDigest }])),
    narrative: { summary: 'SYNTHETIC QA ONLY: porsi terhadap PDB, bukan pertumbuhan.',
      meaning: 'SYNTHETIC QA ONLY: perbandingan komponen dengan total PDB.', comparison: null,
      limitations: 'SYNTHETIC QA ONLY: review disimulasikan dan revisi belum diketahui.',
      factRefs: ['metrics.pmtb_share', 'metrics.household_consumption_share'] } } }
}
const render = props => renderToStaticMarkup(createElement(component.EngineNarrativePreviewView, {
  narrative: null, loading: false, error: false, onRetry() {}, ...props }))

test('matching snapshot displays verbatim original fields and draft limitations', () => {
  const { body, data } = fixture()
  const parsed = client.parsePreviewNarrative(body, data)
  const html = render({ narrative: parsed })
  for (const key of ['summary', 'meaning', 'limitations']) assert(html.includes(body.narrative[key]))
  assert.match(html, /Penjelasan Gemini|Draft preview/)
  assert.match(html, /Belum direview/)
  assert.match(html, /tidak memanggil Gemini/)
  assert.match(html, /Alur review simulasi lokal/)
})

test('changed period, either digest, result value and missing engine data reject stale prose', () => {
  for (const change of [
    p => { p.period = 'Q2 2025' },
    p => { p.metricsBinding.pmtb_share.inputDigest = 'f'.repeat(64) },
    p => { p.metricsBinding.household_consumption_share.resultDigest = 'f'.repeat(64) },
    p => { p.metricsBinding.pmtb_share.value = '31.00' },
    p => { p.metricsBinding.pmtb_share.unit = 'Rp' },
    p => { delete p.metricsBinding.household_consumption_share },
  ]) {
    const { body, data } = fixture(); change(body)
    assert.throws(() => client.parsePreviewNarrative(body, data))
  }
  const { body, data } = fixture()
  data.metrics.pmtb_share.available = false
  assert.throws(() => client.parsePreviewNarrative(body, data))
})

test('approval simulation flags and narrative contract are strict at runtime', () => {
  for (const change of [
    p => { p.humanApproval = true }, p => { p.humanApproval = 0 },
    p => { p.productionPublication = true }, p => { p.workflowStateSimulated = 1 },
    p => { p.schemaVersion = 'other' }, p => { p.status = 'published' },
    p => { p.requestSha256 = 'bad' }, p => { p.responseSha256 = 'bad' },
    p => { p.model = 'unsupported' }, p => { p.narrative.comparison = 'naik' },
    p => { p.narrative.summary = '' }, p => { p.narrative.meaning = 'x'.repeat(601) },
    p => { p.narrative.factRefs = ['metrics.pmtb_share', 'metrics.pmtb_share'] },
  ]) {
    const { body, data } = fixture(); change(body)
    assert.throws(() => client.parsePreviewNarrative(body, data))
  }
})

test('untrusted model text is escaped, never interpreted as HTML', () => {
  const { body, data } = fixture()
  body.narrative.summary = '<img src=x onerror=alert(1)>'
  const html = render({ narrative: client.parsePreviewNarrative(body, data) })
  assert.match(html, /&lt;img/)
  assert.doesNotMatch(html, /<img/)
})

test('loading and failure offer feedback and a read-only retry', () => {
  assert.match(render({ loading: true }), /Memuat penjelasan tersimpan/)
  const html = render({ error: true })
  assert.match(html, /Angka Economic Engine tetap tersedia/)
  assert.match(html, /Muat ulang penjelasan/)
})

test('transport only GETs local saved output without credentials or cache', async () => {
  const { body, data } = fixture(); const calls = []
  const result = await client.fetchNarrative(data, undefined, async (url, options) => {
    calls.push({ url, options }); return new Response(JSON.stringify(body))
  })
  assert.equal(result.narrative.summary, body.narrative.summary)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/api/preview-engine-narrative/')
  assert.equal(calls[0].options.method, 'GET')
  assert.equal(calls[0].options.credentials, 'omit')
  assert.equal(calls[0].options.cache, 'no-store')
})

test('HTTP and malformed JSON fail without fabricated or retained narrative', async () => {
  const { data } = fixture()
  await assert.rejects(client.fetchNarrative(data, undefined, async () => new Response('', { status: 503 })))
  await assert.rejects(client.fetchNarrative(data, undefined, async () => new Response('not json')))
})

test('deadline covers stalled transport and stalled response body', async () => {
  const { data } = fixture()
  for (const fetcher of [async () => new Promise(() => {}), async () => ({ ok: true, json: () => new Promise(() => {}) })]) {
    await assert.rejects(client.fetchNarrative(data, undefined, fetcher, 25), error => error.name === 'TimeoutError')
  }
})

test('aborted request never dispatches and late completion cannot overwrite fresh state', async () => {
  const { data, body } = fixture(), controller = new AbortController()
  controller.abort()
  await assert.rejects(client.fetchNarrative(data, controller.signal, () => assert.fail('Unexpected request')),
    error => error.name === 'AbortError')
  const pending = new AbortController(); let finish
  const old = client.fetchNarrative(data, pending.signal, async () => ({ ok: true, json: () => new Promise(resolve => { finish = resolve }) }))
  await new Promise(resolve => setTimeout(resolve, 0))
  pending.abort()
  await assert.rejects(old, error => error.name === 'AbortError')
  finish(body)
})
