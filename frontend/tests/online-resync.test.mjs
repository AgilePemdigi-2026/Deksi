import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { mkdtemp, rm } from 'node:fs/promises'
import path from 'node:path'

const scratch = await mkdtemp(path.join(process.env.HERMES_TEST_SCRATCH, 'deksi-online-ssr-'))
const server = await createServer({ configFile: false, envDir: scratch, cacheDir: path.join(scratch, 'vite'),
  plugins: [react()], server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(async () => { await server.close(); await rm(scratch, { recursive: true, force: true }) })
const { default: Action } = await server.ssrLoadModule('/src/features/resync/ResyncAction.tsx')
for (const sourceId of ['BPS', 'BI', 'BKPM', 'BIS', 'KEMENKEU']) {
  test(`Online ${sourceId} uses source-specific confirmation when server advertises support`, () => {
    const html = renderToStaticMarkup(createElement(Action, { sourceId, sourceName: sourceId, active: true, supported: true }))
    assert.match(html, /type="checkbox"/)
    assert.match(html, new RegExp(`riwayat ${sourceId}`))
    assert.doesNotMatch(html, /hanya tersedia untuk sumber BPS/)
  })
}
test('Unknown capability or local-file mode cannot submit online sync', () => {
  const html = renderToStaticMarkup(createElement(Action, { sourceId: 'BI', sourceName: 'BI', active: true, supported: false }))
  assert.match(html, /disabled=""/)
  assert.doesNotMatch(html, /type="checkbox"/)
})
