import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch && path.isAbsolute(scratch), 'Set HERMES_TEST_SCRATCH to the permitted scratch directory')
const chromePath = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const profile = await mkdtemp(path.join(scratch, 'deksi-resync-ui-'))
const vite = await createServer({ root, configFile: false, cacheDir: process.env.DEKSI_TEST_CACHE, server: { host: '127.0.0.1', port: 0, strictPort: true } })
let chrome, ws
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
try {
  await vite.listen()
  const origin = `http://127.0.0.1:${vite.httpServer.address().port}`
  chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let port
  for (let i = 0; i < 120; i++) {
    try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port) break } catch {}
    await delay(100)
  }
  assert(port, 'Disposable Chrome did not start')
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let sequence = 0
  const pending = new Map()
  ws.addEventListener('message', event => {
    const result = JSON.parse(event.data)
    if (!result.id) return
    const entry = pending.get(result.id)
    if (!entry) return
    pending.delete(result.id); clearTimeout(entry.timer)
    if (result.error) entry.reject(new Error(JSON.stringify(result.error)))
    else entry.resolve(result.result)
  })
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)) }, 15000)
    pending.set(id, { resolve, reject, timer })
    ws.send(JSON.stringify({ id, method, params }))
  })
  const evaluate = async expression => {
    const response = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails))
    return response.result.value
  }
  const wait = async expression => {
    for (let i = 0; i < 150; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(50) }
    throw new Error(`Timed out waiting for ${expression}`)
  }
  const key = async (name, code) => {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code: name, windowsVirtualKeyCode: code, ...(name === 'Enter' ? { text: '\r', unmodifiedText: '\r' } : {}) })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code: name, windowsVirtualKeyCode: code })
  }
  await send('Page.enable'); await send('Runtime.enable')
  await send('Page.navigate', { url: `${origin}/tests/resync-action-fixture.html` })
  await wait('document.querySelectorAll(".resync-action button").length === 4')
  await wait('!document.body.innerText.includes("Memeriksa antrean")')
  assert.equal(await evaluate('[...document.querySelectorAll(".resync-action button")].every(button => button.disabled)'), true)
  assert.match(await evaluate('document.querySelectorAll(".resync-action")[2].textContent'), /hanya tersedia untuk sumber BPS/i)
  await evaluate('document.querySelectorAll(".resync-action")[0].querySelector("input").click()')
  await evaluate('document.querySelectorAll(".resync-action button")[0].focus()')
  assert.equal(await evaluate('document.activeElement === document.querySelector(".resync-action button")'), true)
  await key('Enter', 13)
  await wait('document.querySelector(".resync-action button").disabled')
  await wait('window.fixture.calls.length === 1')
  assert.equal(await evaluate('window.fixture.calls[0].path'), '/api/admin/sources/BPS/resync/')
  assert.equal(await evaluate('window.confirmCalls'), 1)
  await key('Enter', 13)
  assert.equal(await evaluate('window.fixture.calls.length'), 1)
  assert.match(await evaluate('document.querySelector(".resync-action").textContent'), /Mengirim/)
  await evaluate('window.fixture.succeed()')
  await wait('document.querySelector(".resync-action").textContent.includes("Berhasil")')
  await evaluate('document.querySelectorAll(".resync-action")[3].querySelector("input").click()')
  await evaluate('document.querySelectorAll(".resync-action")[3].querySelector("button").focus()')
  await key('Enter', 13)
  await wait('window.fixture.calls.length === 2')
  await evaluate('window.fixture.fail()')
  await wait('document.querySelectorAll(".resync-action")[3].querySelector("[role=alert]")')
  const error = await evaluate('document.querySelectorAll(".resync-action")[3].querySelector("[role=alert]").textContent')
  assert.match(error, /tidak diketahui|belum dapat dipastikan/i)
  assert.doesNotMatch(error, /private transport detail/)
  console.log('PASS semantic disabled/disconnected states; keyboard confirmation; duplicate suppression; loading, safe success and safe failure')
} finally {
  ws?.close()
  chrome?.kill()
  await vite.close()
  await delay(300)
  await rm(profile, { recursive: true, force: true, maxRetries: 6, retryDelay: 250 }).catch(error => console.error('Owned profile cleanup:', error.message))
}
