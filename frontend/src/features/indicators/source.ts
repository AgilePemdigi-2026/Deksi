import type { DetailData } from './types'
import { API_BASE } from '../../api'

// Guard for navigation only; this is not a backend snapshot or revision identifier.
export function boundContext(data: DetailData | null) {
  if (!data?.selected || data.contextError) return null
  const selected = JSON.stringify(data.selected)
  const matches = data.options.filter(option => JSON.stringify(option.reading) === selected)
  return matches.length === 1 ? matches[0] : null
}

export function rawDownloadHref(raw: string | null | undefined, code: string): string | null {
  if (!raw || !/^[a-z][a-z0-9_-]{0,31}$/.test(code) || !new RegExp(`^/api/indicators/${code}/raw-file/[1-9][0-9]*/$`).test(raw)) return null
  return new URL(raw, new URL(API_BASE).origin).href
}
