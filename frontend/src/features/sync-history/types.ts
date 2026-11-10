export type SyncStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'unknown'

export interface SyncHistoryQuery {
  sourceId?: string
  status?: SyncStatus
  page: number
  pageSize: number
}

export interface SyncHistoryItem {
  id: string
  sourceId: string
  sourceName: string
  status: SyncStatus
  startedAt: string
  finishedAt: string | null
  actor: string | null
  itemCount: number | null
  message: string | null
  resyncJobId?: string | null
  resolvedBy?: string | null
  resolvedAt?: string | null
  resolutionReason?: string | null
}

export interface SyncHistoryResult {
  items: SyncHistoryItem[]
  pagination: { page: number; pageSize: number; total: number; hasNext: boolean }
}

export type LoadSyncHistory = (query: SyncHistoryQuery, options: { signal: AbortSignal }) => Promise<SyncHistoryResult>
