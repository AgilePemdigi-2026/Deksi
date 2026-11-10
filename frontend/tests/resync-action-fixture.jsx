import React from 'react'
import { createRoot } from 'react-dom/client'
import ResyncAction from '../src/features/resync/ResyncAction'

const calls = []
let resolveCall
let rejectCall
window.confirmCalls = 0
window.confirm = () => { window.confirmCalls += 1; return true }
window.fixture = {
  calls,
  succeed: () => resolveCall?.(Response.json({ id: '1', status: 'queued' }, { status: 202 })),
  fail: () => rejectCall?.(new Error('private transport detail')),
}
window.fetch = async (url, init = {}) => {
  const path = String(url)
  if (path.endsWith('/resync-active/')) return Response.json({ job: null })
  if (path.endsWith('/auth/csrf/')) return Response.json({ csrfToken: 'synthetic' })
  if (path.endsWith('/resync/')) {
    calls.push({ path, body: JSON.parse(init.body) })
    return new Promise((resolve, reject) => { resolveCall = resolve; rejectCall = reject })
  }
  if (path.endsWith('/resync-jobs/1/')) return Response.json({ id: '1', sourceId: 'BPS', status: 'success', requestedAt: '2026-01-01T00:00:00Z', finishedAt: null, runId: '1', message: null })
  throw new Error('unexpected fixture path')
}
createRoot(document.getElementById('root')).render(
  <>
    <ResyncAction sourceId="BPS" sourceName="Sumber Uji" active supported />
    <ResyncAction sourceId="BPS" sourceName="Sumber Nonaktif" active={false} supported />
    <ResyncAction sourceId="BI" sourceName="Sumber Tidak Didukung" active supported={false} />
    <ResyncAction sourceId="BPS" sourceName="Sumber Gagal" active supported />
  </>,
)