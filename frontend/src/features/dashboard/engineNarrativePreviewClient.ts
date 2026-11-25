import type { Gdp } from './economicEngineClient'

export type PreviewNarrative = { period: string; model: string;
  narrative: { summary: string; meaning: string; limitations: string } }
const ids = ['pmtb_share', 'household_consumption_share']
const hash = /^[a-f0-9]{64}$/
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Format narasi tidak sesuai')
  return value as Record<string, unknown>
}
function text(value: unknown, max = 600): string {
  if (typeof value !== 'string' || !value.trim() || value.length > max) throw new Error('Teks narasi tidak sesuai')
  return value
}
export function parsePreviewNarrative(raw: unknown, data: Gdp): PreviewNarrative {
  const row = object(raw), bindings = object(row.metricsBinding), narrative = object(row.narrative)
  if (row.schemaVersion !== 'deksi.local-engine-narrative.v1' || row.status !== 'draft_preview' ||
      row.humanApproval !== false || row.productionPublication !== false || row.workflowStateSimulated !== true ||
      typeof row.model !== 'string' || !/^gemini-[A-Za-z0-9_.-]{1,100}$/.test(row.model) ||
      typeof row.requestSha256 !== 'string' || !hash.test(row.requestSha256) ||
      typeof row.responseSha256 !== 'string' || !hash.test(row.responseSha256) ||
      Object.keys(bindings).length !== 2 || Object.keys(data.metrics).length !== 2 ||
      narrative.comparison !== null || Object.keys(narrative).length !== 5 ||
      !Array.isArray(narrative.factRefs) || narrative.factRefs.length !== 2 ||
      [...narrative.factRefs].sort().join('|') !== ids.map(id => `metrics.${id}`).sort().join('|')) {
    throw new Error('Narasi bukan draft preview yang didukung')
  }
  for (const id of ids) {
    const metric = data.metrics[id], binding = object(bindings[id])
    if (!metric?.available || row.period !== metric.period || binding.unit !== '%' ||
        binding.value !== metric.value || binding.resultDigest !== metric.resultDigest ||
        binding.inputDigest !== metric.inputDigest) throw new Error('Narasi tidak cocok dengan perhitungan')
  }
  return { model: row.model, period: text(row.period, 32), narrative: {
    summary: text(narrative.summary), meaning: text(narrative.meaning), limitations: text(narrative.limitations) } }
}
export async function fetchNarrative(data: Gdp, signal?: AbortSignal,
  fetcher: typeof fetch = fetch, timeoutMs = 15_000): Promise<PreviewNarrative> {
  if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError')
  const controller = new AbortController()
  const cancel = () => controller.abort(new DOMException('Request cancelled', 'AbortError'))
  let rejectAbort: () => void = () => {}
  const aborted = new Promise<never>((_, reject) => {
    rejectAbort = () => reject(controller.signal.reason)
    controller.signal.addEventListener('abort', rejectAbort, { once: true })
  })
  signal?.addEventListener('abort', cancel, { once: true })
  const timer = setTimeout(() => controller.abort(new DOMException('Batas waktu narasi terlampaui', 'TimeoutError')), timeoutMs)
  try {
    return await Promise.race([aborted, (async () => {
      const response = await fetcher('/api/preview-engine-narrative/', {
        method: 'GET', signal: controller.signal, credentials: 'omit', cache: 'no-store' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const result = parsePreviewNarrative(await response.json(), data)
      if (controller.signal.aborted) throw controller.signal.reason
      return result
    })()])
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', cancel)
    controller.signal.removeEventListener('abort', rejectAbort)
  }
}
