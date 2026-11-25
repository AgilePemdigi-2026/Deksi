export interface NarrativeObservation {
  id: number
  value: string
  unit: '%'
  period: string
  observationDate: string
  publicationDate: string | null
}

export interface NarrativePage<T> {
  items: T[]
  page: number
  pageSize: 20
  total: number
  hasNext: boolean
}

export interface NarrativeCapabilities {
  canRead: boolean
  canGenerate: boolean
  canReview: boolean
  generationConfigured: boolean
}

export interface Fact {
  observationId: number
  indicatorCode: 'pdb'
  indicatorName: string
  value: string
  unit: string
  period: string
  observationDate: string
  frequency: string
  dataType: string
  publicationDate: string | null
  source: { sourceId: string; sourceName: string; institution: string; primaryUrl: string | null }
  publicationStatus: string
  officialVerification: 'unassessed'
  evidence: {
    status: string
    rawFileId: number | null
    checksumSha256: string | null
    fileSizeBytes: number | null
    retrievedAt: string | null
  }
  sourceTracePath: string
}

export interface NarrativeFactPackage {
  schemaVersion: 'deksi.ai-facts.v1'
  methodVersion: 'pdb-yoy-facts.v1'
  inputDigest: string
  selection: { indicatorCode: 'pdb'; observationId: number; comparisonObservationId: number | null }
  derivedMetrics: []
  facts: { current: Fact; comparison: Fact | null }
  comparisons: { id: 'yoy_rate_difference'; formula: 'current - previous'; formulaVersion: '1'; inputObservationIds: number[]; value: string; unit: 'percentage_point'; note: string }[]
  missingData: string[]
  limitations: string[]
}

export interface AiNarrative {
  summary: string
  meaning: string
  comparison: string | null
  limitations: string
  factRefs: string[]
}

export type GenerationStatus = 'queued' | 'running' | 'ready' | 'failed' | 'unknown'
export type ReviewStatus = 'pending' | 'approved' | 'needs_revision' | 'rejected'
export type NarrativeDecision = 'approved' | 'needs_revision' | 'rejected'

export interface NarrativeReview {
  decision: NarrativeDecision
  notes: string
  reviewedAt: string
  contentDigest: string
}

export interface NarrativeDraft {
  id: number
  requestKey: string
  generationStatus: GenerationStatus
  reviewStatus: ReviewStatus
  factPackage: NarrativeFactPackage
  inputDigest: string
  contentDigest: string | null
  requestedModel: string
  reportedModel: string | null
  promptVersion: string
  validatorVersion: string
  narrative: AiNarrative | null
  errorCode: string | null
  errorMessage: string | null
  createdAt: string
  startedAt: string | null
  finishedAt: string | null
  parentId: number | null
  active: boolean
  reconciledAt: string | null
  review: NarrativeReview | null
}

export interface NarrativeDraftEnvelope { draft: NarrativeDraft }

export interface NarrativeRequest {
  requestKey: string
  observationId: number
  comparisonId: number | null
  parentId: number | null
}
