import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { engineFixture } from './economic-engine-fixtures.mjs'

const vite = await createServer({ configFile: false, plugins: [react()], cacheDir: '.artifacts/vite-engine',
  server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const component = await vite.ssrLoadModule('/src/features/dashboard/EconomicEngine.tsx')
const client = await vite.ssrLoadModule('/src/features/dashboard/economicEngineClient.ts')
const render = props => renderToStaticMarkup(createElement(component.EconomicEngineView, {
  data: null, loading: false, error: false, navigating: false, traceStatus: '', onRetry() {}, onOpenTrace() {}, ...props }))

test('readable overview keeps results and named formulas outside closed audit disclosures', () => {
  const html = render({ data: client.parseGdp(engineFixture()) })
  const overview = html.replace(/<details\b[\s\S]*?<\/details>/g, '')
  assert.match(overview, /30,00/)
  assert.match(overview, /55,00/)
  assert.match(overview, /Triwulan I 2025/)
  assert.match(overview, /Pembentukan Modal Tetap Bruto/)
  assert.match(overview, /PMTB dibagi total PDB, dikali 100 persen/)
  assert.match(overview, /Konsumsi rumah tangga dibagi total PDB, dikali 100 persen/)
  assert.match(overview, /Status revisi belum diketahui; angka dapat direvisi/)
  assert.match(overview, /Tanggal rilis: Belum tersedia/)
  assert.doesNotMatch(overview, /pmtb_nominal|konsumsi_rumah_tangga|bps-gdp-shares|checksum/i)
  assert.match(html, /<summary>Lihat angka pembentuk dan sumber<\/summary>/)
  assert.match(html, /<summary>Detail teknis perhitungan<\/summary>/)
  assert.doesNotMatch(html, /<details[^>]*\bopen/)
})

test('local narrative preview has a visible loading panel while preserving both engine values', () => {
  const html = render({ data: client.parseGdp(engineFixture()), previewNarrativeEnabled: true })
  assert.match(html, /Penjelasan Gemini/)
  assert.match(html, /Memuat penjelasan tersimpan/)
  assert.match(html, /30,00/)
  assert.match(html, /55,00/)
})

test('engine rejects malformed runtime DTO instead of trusting a TypeScript cast', () => {
  assert.equal(typeof client.parseGdp, 'function', 'Runtime GDP parser is missing')
  assert.throws(() => client.parseGdp({ metrics: { pmtb_share: { available: 'yes', value: 30 } } }))
})

test('qualified decimal strings and unknown release dates survive parsing without arithmetic', () => {
  const data = client.parseGdp(engineFixture())
  assert.equal(data.metrics.pmtb_share.value, '30.00')
  assert.equal(data.metrics.household_consumption_share.value, '55.00')
  assert.equal(data.metrics.pmtb_share.inputs.pmtb_nominal.publicationDate, null)
})

test('input presentation removes only trailing fractional zeros without changing the source packet', () => {
  for (const [value, formatted] of [
    ['1588439.580000', '1.588.439,58'],
    ['1588439.580004000', '1.588.439,580004'],
    ['9007199254740993.1200340000', '9.007.199.254.740.993,120034'],
    ['0.000000', '0'],
  ]) {
    const payload = engineFixture(), input = payload.metrics.pmtb_share.inputs.pmtb_nominal
    input.value = input.trace.value = value
    const before = JSON.stringify(payload)
    const parsed = client.parseGdp(payload)
    const html = render({ data: parsed })
    assert(html.includes(`<td>${formatted}</td>`), `Expected exact input presentation for ${value}`)
    assert.equal(parsed.metrics.pmtb_share.inputs.pmtb_nominal.value, value)
    assert.equal(JSON.stringify(payload), before)
    assert.match(html, /30,00/)
  }
})

test('readable periods and release metadata follow each packet instead of a fixed example', () => {
  for (const [period, date, label] of [
    ['Q2 2024', '2024-06-30', 'Triwulan II 2024'],
    ['Q3 2025', '2025-09-30', 'Triwulan III 2025'],
    ['Q4 2023', '2023-12-31', 'Triwulan IV 2023'],
  ]) {
    const payload = engineFixture()
    for (const metric of Object.values(payload.metrics)) {
      metric.period = period; metric.observationDate = date
      for (const input of Object.values(metric.inputs)) {
        input.period = input.trace.period = period
        input.observationDate = input.trace.observationDate = date
        input.publicationDate = input.trace.publicationDate = '2026-01-01'
      }
    }
    const html = render({ data: client.parseGdp(payload) })
    assert(html.includes(label))
    assert.match(html, /Tanggal rilis: 2026-01-01/)
    assert.doesNotMatch(html, /Triwulan I 2025|Tanggal rilis: Belum tersedia/)
  }
})

test('malformed versions, identity, arithmetic fields, period and evidence fail closed', () => {
  const mutations = [
    p => { p.methodVersion = 'future' }, p => { p.metrics.pmtb_share.id = 'other' },
    p => { p.metrics.pmtb_share.available = 'yes' }, p => { p.metrics.pmtb_share.value = 30 },
    p => { p.metrics.pmtb_share.value = 'NaN' }, p => { p.metrics.pmtb_share.value = null },
    p => { p.metrics.pmtb_share.inputs.pmtb_nominal.value = false },
    p => { p.metrics.pmtb_share.inputs.pmtb_nominal.trace.value = '301' },
    p => { p.metrics.pmtb_share.inputs.pmtb_nominal.trace.rawFile.checksumSha256 = 'd'.repeat(64) },
    p => { p.metrics.pmtb_share.inputs.pmtb_nominal.bindingStatus = 'mismatch' },
    p => { p.metrics.pmtb_share.inputs.pmtb_nominal.observationDate = '2025-06-30' },
    p => { p.metrics.pmtb_share.observationDate = '2025-02-31' },
    p => { p.metrics.pmtb_share.formula = 'template frontend' },
    p => { p.metrics.pmtb_share.priceBasis = null },
    p => { p.metrics.pmtb_share.resultDigest = 'unqualified' },
    p => { delete p.metrics.household_consumption_share },
  ]
  for (const mutation of mutations) { const payload = engineFixture(); mutation(payload); assert.throws(() => client.parseGdp(payload)) }
})

test('missing inputs remain unavailable rather than being converted to a zero', () => {
  const payload = engineFixture()
  Object.assign(payload.metrics.pmtb_share, { available: false, value: null, reason: 'RAW belum cocok',
    reasonCode: 'input_evidence_unqualified', inputs: {}, priceBasis: null })
  const data = client.parseGdp(payload)
  assert.equal(data.metrics.pmtb_share.value, null)
  assert.match(render({ data }), /Belum tersedia|RAW belum cocok/)
})

test('legitimate zero remains an available value', () => {
  const payload = engineFixture(), metric = payload.metrics.pmtb_share
  metric.value = '0.00'; metric.inputs.pmtb_nominal.value = '0'; metric.inputs.pmtb_nominal.trace.value = '0'
  assert.match(render({ data: client.parseGdp(payload) }).replace(/<[^>]*>/g, ''), /0,00%/)
})

test('an empty response requires a version and an explicit missing reason', () => {
  const payload = engineFixture(); payload.metrics = {}; payload.reason = 'PDB belum direview'
  assert.deepEqual(client.parseGdp(payload), { metrics: {}, reason: payload.reason })
  delete payload.reason; assert.throws(() => client.parseGdp(payload))
})

test('transport uses the public route, omits credentials and disables caching', async () => {
  const calls = []
  const data = await client.fetchGdp(undefined, async (url, options) => {
    calls.push({ url, options }); return new Response(JSON.stringify(engineFixture()))
  })
  assert.equal(data.metrics.pmtb_share.value, '30.00'); assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/api/economic-engine/gdp/')
  assert.equal(calls[0].options.credentials, 'omit'); assert.equal(calls[0].options.cache, 'no-store')
})

test('HTTP and invalid JSON failures do not return fixtures or stale success data', async () => {
  await assert.rejects(client.fetchGdp(undefined, async () => new Response('', { status: 503 })), /503/)
  await assert.rejects(client.fetchGdp(undefined, async () => new Response('not json')))
})

test('the deadline covers a stalled transport and a stalled JSON body', async () => {
  for (const fetcher of [async () => new Promise(() => {}), async () => ({ ok: true, json: () => new Promise(() => {}) })]) {
    await assert.rejects(client.fetchGdp(undefined, fetcher, 25), error => error.name === 'TimeoutError')
  }
})

test('a pre-aborted request never invokes transport', async () => {
  const controller = new AbortController(); controller.abort()
  await assert.rejects(client.fetchGdp(controller.signal, () => assert.fail('Unexpected request')), error => error.name === 'AbortError')
})

test('caller cancellation wins even when the old transport ignores it', async () => {
  const controller = new AbortController(); let finish
  const old = client.fetchGdp(controller.signal, async () => ({ ok: true, json: () => new Promise(resolve => { finish = resolve }) }))
  await new Promise(resolve => setTimeout(resolve, 0))
  controller.abort(); await assert.rejects(old, error => error.name === 'AbortError')
  finish(engineFixture())
  const fresh = await client.fetchGdp(undefined, async () => new Response(JSON.stringify(engineFixture())))
  assert.equal(fresh.metrics.pmtb_share.value, '30.00')
})

test('source matching binds the original precision, release and checksum', () => {
  const input = client.parseGdp(engineFixture()).metrics.pmtb_share.inputs.pmtb_nominal
  assert(client.matchesInput('pmtb_nominal', input, { ...input.trace, value: '300.000000' }))
  assert(!client.matchesInput('pmtb_nominal', input, { ...input.trace, publicationDate: '2025-04-01' }))
  assert(!client.matchesInput('pmtb_nominal', input, { ...input.trace, rawFile: { ...input.trace.rawFile, checksumSha256: 'd'.repeat(64) } }))
})

test('rendered method, source controls and unverified limitations are explicit', () => {
  const html = render({ data: client.parseGdp(engineFixture()) })
  assert.match(html, /bps-gdp-shares\.v3/); assert.match(html, /harga berlaku/i)
  assert.match(html, /Source Trace PMTB/); assert.match(html, /data-input-code="pmtb_nominal"/)
  assert.match(html, /Tanggal rilis: Belum tersedia/)
  assert.match(html, /bukan bukti kebenaran angka/); assert.match(html, /Perdagangan barang/)
  assert.match(html, /Belum tersedia: kesesuaian metodologi/)
})

test('revision uncertainty is visible and an unsupported final status is refused', () => {
  const payload = engineFixture()
  const html = render({ data: client.parseGdp(payload) })
  assert.match(html, /Status revisi belum diketahui; angka dapat direvisi\./)
  payload.metrics.pmtb_share.revisionStatus = 'final'
  assert.throws(() => client.parseGdp(payload))
})

test('loading, retry and source strings render safely without raw HTML', () => {
  assert.match(render({ loading: true }), /Memuat perhitungan/)
  assert.match(render({ error: true }), /Coba lagi/)
  const payload = engineFixture(); payload.metrics.pmtb_share.note = '<img src=x onerror=alert(1)>'
  const html = render({ data: client.parseGdp(payload) })
  assert.match(html, /&lt;img/); assert.doesNotMatch(html, /<img/)
})
