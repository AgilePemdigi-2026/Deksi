import { useEffect, useState } from 'react'
import { fetchDetail } from './api'
import type { DetailData, Route, Selector } from './types'

export function useDetailData(route: Extract<Route, { kind: 'detail' | 'source' }>) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ key: string; data: DetailData | null; error: string | null } | null>(null)
  const selectorKey = JSON.stringify(route.selector)
  const requestKey = `${route.code}:${selectorKey}:${attempt}`
  const current = result?.key === requestKey ? result : null
  useEffect(() => {
    const controller = new AbortController()
    fetchDetail(route.code, JSON.parse(selectorKey) as Selector | null, controller.signal).then(data => {
      if (!controller.signal.aborted) setResult({ key: requestKey, data, error: data.warnings.length === 3 ? 'Backend belum terhubung atau respons belum dapat digunakan. Tidak ada data contoh yang disisipkan.' : null })
    }).catch(() => { if (!controller.signal.aborted) setResult({ key: requestKey, data: null, error: 'Data gagal dimuat. Tidak ada nilai pengganti.' }) })
    return () => controller.abort()
  }, [route.code, selectorKey, requestKey])
  return { data: current?.data ?? null, loading: current === null, error: current?.error ?? null, onRetry: () => setAttempt(value => value + 1) }
}
