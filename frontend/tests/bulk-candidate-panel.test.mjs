import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdtemp, rm } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const scratch = process.env.HERMES_TEST_SCRATCH
assert(scratch, 'Set HERMES_TEST_SCRATCH to the agent-owned scratch directory')
const cache = await mkdtemp(path.join(scratch, 'deksi-bulk-ui-'))
const app = await createServer({ configFile: false, root: path.resolve('.'), cacheDir: cache,
  server: { middlewareMode: true, hmr: false, ws: false } })
after(async () => { await app.close(); await rm(cache, { recursive: true, force: true }) })
const { default: CandidateReview } = await app.ssrLoadModule('/src/features/candidates/CandidateReview.tsx')

test('candidate panel offers an explicitly scoped batch preview, not blind approval', () => {
  const html = renderToStaticMarkup(React.createElement(CandidateReview, {
    sourceId: 'BPS', onClose: () => {}, onBusyChange: () => {},
  }))
  assert.match(html, /Pratinjau kandidat yang memenuhi syarat/)
  assert.doesNotMatch(html, /Setujui semua pending/)
})
