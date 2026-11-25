import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, readFile, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH
const python = process.env.ENGINE_PYTHON, backend = process.env.ENGINE_BACKEND
const executable = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
assert(scratch && path.isAbsolute(scratch) && python && backend && existsSync(executable), 'Existing Python, backend and Chrome plus permitted scratch are required')
await mkdir(path.join(root, '.artifacts'), { recursive: true })
const output = await mkdtemp(path.join(root, '.artifacts/economic-engine-browser-'))
console.log('ARTIFACTS ' + output)
const profile = await mkdtemp(path.join(scratch, 'deksi-economic-browser-'))
const checks = [], errors = [], blockedExternal = [], requests = []
const cancelledNetworks = new Set(), interceptionErrors = []
const unrelatedServerFailures = []
const layoutMeasurements = [], contrastMeasurements = [], screenshots = []
let completed = false
let service, chrome, vite, ws, send, backendLog = '', backendExit
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
const check = async (name, action) => { await action(); checks.push(name); console.log('PASS ' + name) }
try {
  service = spawn(python, ['-B', path.join(backend, 'indicators/tests/economic_engine_browser_server.py'),
    '--scratch', scratch, '--state-dir', output], { stdio: ['ignore', 'pipe', 'pipe'] })
  service.stdout.on('data', data => { backendLog += String(data) }); service.stderr.on('data', data => { backendLog += String(data) })
  service.on('error', error => { backendLog += String(error) })
  backendExit = new Promise(resolve => service.once('exit', resolve))
  let serviceState
  for (let i = 0; i < 120; i++) {
    try { serviceState = JSON.parse(await readFile(path.join(output, 'backend.json'), 'utf8')); break } catch {}
    if (service.exitCode !== null) throw new Error('Fixture server failed: ' + backendLog)
    await delay(100)
  }
  assert(serviceState?.synthetic && Number.isInteger(serviceState.port), 'Owned backend did not start: ' + backendLog)
  const backendOrigin = `http://127.0.0.1:${serviceState.port}`
  const setMode = async name => {
    const response = await fetch(`${backendOrigin}/__engine_qa/mode?name=${encodeURIComponent(name)}`)
    assert(response.ok); assert.deepEqual(await response.json(), { mode: name, synthetic: true })
  }
  vite = await createServer({ root, configFile: false, plugins: [react()], cacheDir: path.join(root, '.artifacts/vite-economic-browser'),
    server: { host: '127.0.0.1', port: 0, strictPort: true, proxy: { '/api': { target: backendOrigin, changeOrigin: true } } } })
  await vite.listen()
  const origin = `http://127.0.0.1:${vite.httpServer.address().port}`
  await check('Real Django HTTP packet is accepted by the actual frontend parser', async () => {
    const response = await fetch(backendOrigin + '/api/economic-engine/gdp/')
    assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'no-store')
    const raw = await response.json(), client = await vite.ssrLoadModule('/src/features/dashboard/economicEngineClient.ts')
    const data = client.parseGdp(raw)
    assert.equal(data.metrics.pmtb_share.value, '30.00'); assert.equal(data.metrics.household_consumption_share.value, '55.00')
    await writeFile(path.join(output, 'actual-django-packet.json'), JSON.stringify(raw, null, 2))
  })
  chrome = spawn(executable, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let port
  for (let i = 0; i < 120; i++) { try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {} await delay(100) }
  assert(port, 'Owned disposable browser did not start')
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let sequence = 0
  const pending = new Map()
  send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence, timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout ' + method)) }, 15000)
    pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params }))
  })
  ws.addEventListener('message', event => {
    const result = JSON.parse(event.data)
    if (result.method === 'Network.responseReceived') {
      const response = result.params.response, url = new URL(response.url)
      if (response.status >= 500 && url.pathname.startsWith('/api/') && url.pathname !== '/api/economic-engine/gdp/') {
        unrelatedServerFailures.push({ path: url.pathname, status: response.status })
      }
    }
    if (result.method === 'Runtime.exceptionThrown') errors.push(result.params.exceptionDetails.exception?.description ?? result.params.exceptionDetails.text)
    if (result.method === 'Network.loadingFailed' && result.params.canceled) cancelledNetworks.add(result.params.requestId)
    if (result.method === 'Fetch.requestPaused') {
      const event = result.params, url = new URL(event.request.url)
      requests.push(url.href)
      const allowed = url.origin === origin
      if (!allowed) blockedExternal.push(url.origin)
      void send(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', allowed ? { requestId: event.requestId }
        : { requestId: event.requestId, errorReason: 'BlockedByClient' }).catch(error => interceptionErrors.push({ networkId: event.networkId, error: String(error) }))
    }
    if (!result.id) return
    const entry = pending.get(result.id); if (!entry) return
    pending.delete(result.id); clearTimeout(entry.timer)
    if (result.error) entry.reject(new Error(JSON.stringify(result.error))); else entry.resolve(result.result)
  })
  const js = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  const wait = async expression => { for (let i = 0; i < 150; i++) { if (await js(`Boolean(${expression})`)) return; await delay(80) } throw new Error('Page condition timed out: ' + expression) }
  const section = 'document.querySelector("#economic-engine")'
  const go = async (route = '/#economic-engine') => {
    await js('window.__economicQaOldDocument = true')
    await send('Page.navigate', { url: origin + route })
    await wait('!window.__economicQaOldDocument && document.readyState === "complete"')
  }
  const pointer = async expression => {
    const box = await js(`(() => {
      const element = ${expression}; if (!element) throw new Error('Missing browser control');
      element.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = element.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2, width: r.width, height: r.height };
    })()`)
    assert(box.width > 0 && box.height > 0, 'Control must be visible before clicking')
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1 })
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1 })
  }
  const click = label => pointer(`[...${section}.querySelectorAll('button')].find(button => button.textContent.includes(${JSON.stringify(label)}))`)
  const key = async (name, code, number, text) => {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code, windowsVirtualKeyCode: number,
      ...(text ? { text, unmodifiedText: text } : {}) })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code, windowsVirtualKeyCode: number })
  }
  const openInputs = async () => {
    if (!await js(`${section}.querySelector('.engine-details').open`)) {
      await pointer(`${section}.querySelector('.engine-details summary')`)
    }
    await wait(`${section}.querySelector('.engine-details').open`)
  }
  const capture = async name => {
    const bounds = await js(`(() => { const r = ${section}.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height, scale: 1 }; })()`)
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: bounds })
    await writeFile(path.join(output, name), Buffer.from(shot.data, 'base64')); screenshots.push(name)
  }
  const loaded = value => wait(`${section}?.innerText.includes(${JSON.stringify(value)}) && !${section}?.innerText.includes('Memuat perhitungan')`)
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  await send('Fetch.enable', { patterns: [{ urlPattern: 'http*', requestStage: 'Request' }] })
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await check('Browser dashboard renders backend-calculated shares and source context', async () => {
    await go(); await loaded('30,00%')
    await js('document.fonts.ready.then(() => true)')
    assert(await js(`${section}.innerText.includes('55,00%') && ${section}.innerText.includes('Triwulan I 2025')`))
    assert(!await js(`${section}.innerText.includes('bps-gdp-shares.v3')`))
    assert(await js(`${section}.innerText.includes('Status revisi belum diketahui; angka dapat direvisi.')`))
    assert(await js(`${section}.innerText.includes('Tanggal rilis: Belum tersedia')`))
    assert(await js(`${section}.querySelectorAll('[role="math"][aria-label]').length === 2`))
    await capture('engine-ready-SYNTHETIC.png')
  })
  await check('Keyboard disclosure exposes source inputs and audit without hiding warnings', async () => {
    await js(`${section}.querySelector('.engine-button').focus()`)
    await key('Tab', 'Tab', 9)
    assert.equal(await js('document.activeElement.textContent'), 'Lihat angka pembentuk dan sumber')
    const focus = await js('({ visible: document.activeElement.matches(":focus-visible"), width: getComputedStyle(document.activeElement).outlineWidth, style: getComputedStyle(document.activeElement).outlineStyle })')
    assert(focus.visible && parseFloat(focus.width) >= 2 && focus.style !== 'none', JSON.stringify(focus))
    await key('Enter', 'Enter', 13, '\r')
    await wait(`${section}.querySelector('.engine-details').open`)
    assert(await js(`${section}.innerText.includes('Pembilang') && ${section}.innerText.includes('Penyebut') && ${section}.innerText.includes('1.000')`))
    await key(' ', 'Space', 32, ' ')
    await wait(`!${section}.querySelector('.engine-details').open`)
    await pointer(`${section}.querySelector('.engine-audit summary')`)
    await wait(`${section}.querySelector('.engine-audit').open`)
    assert(await js(`${section}.innerText.includes('bps-gdp-shares.v3') && ${section}.innerText.includes('bukan bukti kebenaran angka')`))
    await pointer(`${section}.querySelector('.engine-audit summary')`)
    await wait(`!${section}.querySelector('.engine-audit').open`)
    const tree = await send('Accessibility.getFullAXTree')
    const math = tree.nodes.filter(node => node.role?.value?.toLowerCase() === 'math').map(node => node.name?.value)
    assert(math.includes('PMTB dibagi total PDB, dikali 100 persen'))
    assert(math.includes('Konsumsi rumah tangga dibagi total PDB, dikali 100 persen'))
  })
  for (const width of [1440, 1280, 768, 390, 320]) {
    await check(`Readable engine reflows at ${width} CSS pixels with closed and expanded details`, async () => {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false })
      for (const expanded of [false, true]) {
        await js(`${section}.querySelectorAll('details').forEach(element => { element.open = ${expanded} })`)
        const measured = await js(`(() => {
          const root = ${section}, grid = root.querySelector('.engine-grid'), card = root.querySelector('.engine-card');
          const visible = element => element.getClientRects().length && element.getBoundingClientRect().width > 0;
          const escaped = [...root.querySelectorAll('*')].filter(element => visible(element) && !element.closest('.engine-table-scroll'))
            .filter(element => { const r = element.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1; })
            .slice(0, 8).map(element => ({ tag: element.tagName, className: element.className, text: element.textContent.slice(0, 80) }));
          return { width: innerWidth, expanded: ${expanded}, pageOverflow: document.documentElement.scrollWidth - innerWidth,
            engineOverflow: root.scrollWidth - root.clientWidth, escaped,
            columns: getComputedStyle(grid).gridTemplateColumns.split(' ').length,
            bodyFont: parseFloat(getComputedStyle(card.querySelector('.engine-definition')).fontSize),
            valueFont: parseFloat(getComputedStyle(card.querySelector('.engine-value')).fontSize),
            labelFont: parseFloat(getComputedStyle(card.querySelector('h3')).fontSize),
            warningFont: parseFloat(getComputedStyle(card.querySelector('.engine-warning')).fontSize),
            tableScrollers: [...root.querySelectorAll('.engine-table-scroll')].map(table => ({ client: table.clientWidth, scroll: table.scrollWidth })) };
        })()`)
        layoutMeasurements.push(measured)
        await writeFile(path.join(output, 'layout-measurements.json'), JSON.stringify(layoutMeasurements, null, 2))
        assert(measured.pageOverflow <= 1 && measured.engineOverflow <= 1 && measured.escaped.length === 0, JSON.stringify(measured))
        assert.equal(measured.columns, width > 960 ? 2 : 1)
        assert(measured.bodyFont >= 16 && measured.warningFont >= 14 && measured.valueFont > measured.labelFont)
        if ((width === 1440 && expanded) || (width === 390 && !expanded) || (width === 320 && expanded)) {
          await capture(`engine-${width}-${expanded ? 'expanded' : 'overview'}-SYNTHETIC.png`)
        }
      }
    })
  }
  await check('Rendered engine text reaches the planned minimum contrast', async () => {
    const samples = await js(`(() => {
      const rgb = color => color.match(/[\\d.]+/g).map(Number);
      const light = color => rgb(color).slice(0, 3).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
        .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
      const background = element => {
        for (let current = element; current; current = current.parentElement) {
          const color = getComputedStyle(current).backgroundColor, values = rgb(color);
          if (values.length === 3 || values[3] === 1) return color;
          if (values[3] !== 0) throw new Error('Partially transparent background needs compositing');
        }
        return 'rgb(255, 255, 255)';
      };
      return [...${section}.querySelectorAll('p,h2,h3,h4,summary,th,td,caption,button,code,small,.engine-fraction > span,.engine-unit')]
        .filter(element => element.getClientRects().length && element.textContent.trim()).map(element => {
          const style = getComputedStyle(element), bg = background(element), a = light(style.color), b = light(bg);
          return { selector: element.className || element.tagName, color: style.color, background: bg,
            ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05),
            required: parseFloat(style.fontSize) >= 24 || (parseFloat(style.fontSize) >= 18.667 && parseInt(style.fontWeight) >= 700) ? 3 : 4.5 };
        });
    })()`)
    contrastMeasurements.push(...samples)
    await writeFile(path.join(output, 'contrast-measurements.json'), JSON.stringify(samples, null, 2))
    assert(samples.length > 20)
    assert.deepEqual(samples.filter(sample => sample.ratio < sample.required), [])
  })
  await check('Text enlargement to 200 percent preserves engine content and controls', async () => {
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 1000, deviceScaleFactor: 1, mobile: false })
    await js(`window.__engineTextSizes = [...${section}.querySelectorAll('*')].map(element => [element, getComputedStyle(element).fontSize]);
      window.__engineTextSizes.forEach(([element, size]) => { element.style.fontSize = (parseFloat(size) * 2) + 'px' })`)
    try {
      const result = await js(`({ pageOverflow: document.documentElement.scrollWidth - innerWidth,
        engineOverflow: ${section}.scrollWidth - ${section}.clientWidth,
        bodyFont: parseFloat(getComputedStyle(${section}.querySelector('.engine-definition')).fontSize),
        summaries: [...${section}.querySelectorAll('summary')].map(element => ({ width: element.clientWidth, scroll: element.scrollWidth })) })`)
      await writeFile(path.join(output, 'text-enlargement-200.json'), JSON.stringify(result, null, 2))
      assert(result.bodyFont >= 32 && result.pageOverflow <= 1 && result.engineOverflow <= 1, JSON.stringify(result))
      assert(result.summaries.every(item => item.scroll <= item.width + 1))
    } finally {
      await js(`window.__engineTextSizes.forEach(([element]) => element.style.removeProperty('font-size')); delete window.__engineTextSizes`)
    }
    await js(`${section}.querySelectorAll('details').forEach(element => { element.open = false })`)
    await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  })
  await check('Missing RAW blocks one ratio without hiding the independent qualified ratio', async () => {
    await setMode('raw-missing'); await click('Perbarui perhitungan'); await loaded('RAW belum cocok')
    assert(!await js(`${section}.innerText.includes('30,00%')`)); assert(await js(`${section}.innerText.includes('55,00%')`))
  })
  await check('A real zero is shown as zero, not unavailable', async () => {
    await setMode('zero'); await click('Perbarui perhitungan'); await loaded('0,00%')
  })
  await check('HTTP failure clears previous success and retry loads fresh real API data', async () => {
    await setMode('error'); await click('Perbarui perhitungan'); await loaded('Perhitungan belum dapat dimuat')
    assert(!await js(`${section}.innerText.includes('0,00%')`))
    await setMode('ready'); await click('Coba lagi'); await loaded('30,00%')
  })
  await check('Malformed response is refused instead of rendering an available numeric card', async () => {
    await setMode('malformed'); await click('Perbarui perhitungan'); await loaded('Perhitungan belum dapat dimuat')
    assert(!await js(`${section}.innerText.includes('30,00%')`))
    await setMode('ready'); await click('Coba lagi'); await loaded('30,00%')
  })
  await check('A changed observation refuses the old Source Trace context', async () => {
    await setMode('changed'); await openInputs()
    await pointer(`${section}.querySelector('[data-input-code="pmtb_nominal"]')`); await loaded('Sumber berubah')
    assert.equal(await js('location.pathname'), '/')
  })
  await check('Refreshing loads the changed result and keyboard opens its exact Source Trace', async () => {
    await click('Perbarui perhitungan'); await loaded('31,00%'); await openInputs()
    await js(`${section}.querySelector('[data-input-code="pmtb_nominal"]').focus()`)
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 })
    await wait('location.pathname === "/indikator/pmtb_nominal/sumber" && document.body.innerText.includes("310")')
    const query = new URLSearchParams(await js('location.search'))
    assert.equal(query.get('tanggal'), '2025-03-31'); assert.equal(query.get('sumber'), 'BPS')
    assert.match(query.get('konteks'), /^[a-f0-9]{64}$/)
  })
  await check('No reviewed GDP remains explicitly missing and goods trade stays gated', async () => {
    await setMode('empty'); await go(); await loaded('PDB nominal yang direview belum tersedia')
    assert(await js(`${section}.innerText.includes('Belum tersedia: kesesuaian metodologi')`))
    assert(!await js(`${section}.innerText.includes('31,00%')`))
  })
  await send('Fetch.disable'); await send('Page.navigate', { url: 'about:blank' }); await delay(150)
  const unexpectedInterception = interceptionErrors.filter(event =>
    !(event.error.includes('Invalid InterceptionId') && cancelledNetworks.has(event.networkId)))
  assert.deepEqual(errors, []); assert.deepEqual(unexpectedInterception, []); assert.deepEqual(blockedExternal, [])
  assert.deepEqual(unrelatedServerFailures, [])
  assert(requests.some(url => url.includes('/api/economic-engine/gdp/')))
  completed = true
  console.log(JSON.stringify({ checks: checks.length, runtimeErrors: errors.length, blockedExternal: blockedExternal.length }))
} finally {
  await writeFile(path.join(output, 'receipt.json'), JSON.stringify({ synthetic: true, completed, checks, layoutMeasurements, contrastMeasurements, screenshots, runtimeErrors: errors, blockedExternal,
    unrelatedServerFailures, interceptionErrors: interceptionErrors.map(event => ({ ...event, cancelled: cancelledNetworks.has(event.networkId) })), requestCount: requests.length }, null, 2))
  await writeFile(path.join(output, 'backend.log'), backendLog)
  if (ws?.readyState === WebSocket.OPEN) { try { await send('Browser.close') } catch {} ws.close() }
  if (chrome && chrome.exitCode === null) { await Promise.race([new Promise(resolve => chrome.once('exit', resolve)), delay(2000)]); if (chrome.exitCode === null) chrome.kill() }
  if (vite) await vite.close()
  if (service && service.exitCode === null) { await writeFile(path.join(output, 'stop'), 'stop'); await Promise.race([backendExit, delay(5000)]); if (service.exitCode === null) service.kill() }
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 250 })
}
