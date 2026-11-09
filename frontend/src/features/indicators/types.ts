export interface HistoryPoint { period: string; value: string | null; unit: string; observationDate?: string; year?: number; frequency?: string | null; dataType?: string | null; sourceId?: string | null }
export interface SourceReading {
  indicatorCode: string; indicatorName: string | null; value: string | null; unit: string | null
  period: string | null; observationDate: string | null; frequency: string | null; dataType: string | null
  publicationDate: string | null; validationStatus: string | null; reviewedAt: string | null
  source: { sourceId: string | null; sourceName: string | null; institution: string | null; primaryUrl: string | null } | null
  rawFile: { documentName: string | null; sourceUrl: string | null; checksumSha256: string | null; retrievedAt: string | null; periodLabel: string | null; fileSizeBytes: number | null; downloadUrl: string | null } | null
}
export interface Selector { date: string; dataType: string; frequency: string; sourceId: string; guard: string }
export type Route = { kind: 'dashboard' } | { kind: 'detail' | 'source'; code: string; selector: Selector | null } | { kind: 'not-found' }
export interface SummaryReading {
  id: string; available: boolean; name: string | null; category: string | null; value: string | null; unit: string | null
  period: string | null; observationDate: string | null; frequency: string | null; dataType: string | null
  sourceId: string | null; source: string | null; publicationDate: string | null; retrievedAt: string | null
  delta: string | null; note: string | null
}
export interface DetailData {
  summary: SummaryReading | null; selected: SourceReading | null
  options: { reading: SourceReading; guard: string }[]; history: HistoryPoint[]
  warnings: string[]; contextError: string | null
}
