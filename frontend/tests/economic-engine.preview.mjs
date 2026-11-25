// Isolated human preview only. No application fixtures or providers are injected into production code.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

const root = fileURLToPath(new URL('../', import.meta.url))
const scratch = process.env.HERMES_TEST_SCRATCH, state = process.env.ENGINE_PREVIEW_STATE
assert(scratch && state && path.isAbsolute(scratch) && path.isAbsolute(state))
for (const target of [root, state]) {
  const relative = path.relative(scratch, target)
  assert(relative && !relative.startsWith('..') && !path.isAbsolute(relative), 'Preview writes must remain in owned scratch')
}
const context = JSON.parse(await readFile(path.join(state, 'backend-runtime.json'), 'utf8'))
const target = new URL(context.backendOrigin)
assert(target.protocol === 'http:' && target.hostname === '127.0.0.1' && target.port && target.origin === context.backendOrigin)
assert(context.realSourceNumbers === true && context.workflowStateSimulated === true && context.humanApproval === false)
const remaining = Date.parse(context.expiresAt) - Date.now()
assert(remaining > 0 && remaining <= 3_600_000)
const escape = text => String(text).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char])
const message = `PREVIEW LOKAL — sampel BPS riil ${context.quarter}. Review disimulasikan; bukan publikasi. ${context.catalogueNote} Indikator lain bisa belum tersedia.`
const server = await createServer({ root, configFile: false, plugins: [react(), {
  name: 'isolated-preview-label',
  transformIndexHtml(html) {
    return { html, tags: [{ tag: 'aside', attrs: { id: 'isolated-preview-banner', role: 'note',
      style: 'padding:14px 24px;background:#fff1bd;color:#322600;border-bottom:2px solid #b08516;font:600 14px/1.6 system-ui;position:relative;z-index:100' },
      children: escape(message), injectTo: 'body-prepend' }] }
  },
}], define: { 'import.meta.env.VITE_ENGINE_NARRATIVE_PREVIEW': JSON.stringify(context.hasNarrativePreview ? '1' : '0') },
cacheDir: path.join(root, '.artifacts/vite-human-preview'),
server: { host: '127.0.0.1', port: 0, strictPort: true, proxy: { '/api': { target: context.backendOrigin, changeOrigin: true } } } })
await server.listen()
const origin = `http://127.0.0.1:${server.httpServer.address().port}`
const runtime = { frontendOrigin: origin, previewUrl: origin + '/#economic-engine', pid: process.pid,
  backendOrigin: context.backendOrigin, backendPid: context.pid, expiresAt: context.expiresAt,
  realSourceNumbers: true, workflowStateSimulated: true, humanApproval: false, productionPublication: false,
  hasNarrativePreview: context.hasNarrativePreview === true }
await writeFile(path.join(state, 'frontend-runtime.json'), JSON.stringify(runtime, null, 2) + '\n')
console.log('PREVIEW_READY ' + JSON.stringify(runtime))
let closing = false
async function close() {
  if (closing) return
  closing = true
  await writeFile(path.join(state, 'stop'), 'stop')
  await server.close()
}
const timer = setTimeout(() => { void close() }, remaining)
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => { clearTimeout(timer); void close() })
