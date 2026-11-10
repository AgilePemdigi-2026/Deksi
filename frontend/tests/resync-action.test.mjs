import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const vite = await createServer({ root, configFile: false, plugins: [react()], cacheDir: process.env.DEKSI_TEST_CACHE, server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const { default: ResyncAction } = await vite.ssrLoadModule('/src/features/resync/ResyncAction.tsx')
const render = (props = {}) => renderToStaticMarkup(createElement(ResyncAction, { sourceId: 'BPS', sourceName: 'Badan Pusat Statistik', active: true, supported: true, ...props }))

test('requires manual history review before enabling a semantic BPS action', () => {
  const html = render()
  assert.match(html, /<button[^>]*type="button"[^>]*disabled/)
  assert.match(html, /Saya sudah memeriksa riwayat BPS/)
  assert.doesNotMatch(html, /Berhasil|Sukses/)
})

test('inactive, unsupported, and non-BPS sources cannot trigger the action', () => {
  for (const props of [{ active: false }, { supported: false }, { sourceId: 'OTHER' }]) {
    const html = render({ sourceId: 'BPS', ...props })
    assert.match(html, /<button[^>]*disabled/)
  }
})
