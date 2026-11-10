import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const vite = await createServer({ configFile: false, plugins: [react()], cacheDir: '.artifacts/sync-history-test', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())

test('the disconnected history page explains its state without invented records or actions', async () => {
  assert.ok(existsSync('src/features/sync-history/SyncHistoryPage.tsx'), 'Halaman riwayat perlu tersedia')
  const { default: Page } = await vite.ssrLoadModule('/src/features/sync-history/SyncHistoryPage.tsx')
  const html = renderToStaticMarkup(createElement(Page))
  assert.match(html, /Riwayat Sinkronisasi/)
  assert.match(html, /belum terhubung/i)
  assert.match(html, /hasil akhir belum tercatat/i)
  assert.match(html, /Berlangsung/)
  assert.match(html, /Berhasil/)
  assert.match(html, /Gagal/)
  assert.match(html, /<table/)
  for (const label of ['Waktu mulai', 'Sumber', 'Status', 'Waktu selesai', 'Keterangan']) assert.ok(html.includes(label), label)
  assert.match(html, /Riwayat belum terhubung/)
  assert.doesNotMatch(html, /riwayat lama tetap dipertahankan/i)
  assert.doesNotMatch(html, /<button|<select/i)
})

test('a connected page begins loading rather than disconnected', async () => {
  const { default: Page } = await vite.ssrLoadModule('/src/features/sync-history/SyncHistoryPage.tsx')
  const html = renderToStaticMarkup(createElement(Page, { loadHistory: async () => ({ items: [], pagination: { page: 1, pageSize: 20, total: 0, hasNext: false } }) }))
  assert.match(html, /Memuat riwayat/i)
  assert.doesNotMatch(html, /Riwayat belum terhubung/i)
})
