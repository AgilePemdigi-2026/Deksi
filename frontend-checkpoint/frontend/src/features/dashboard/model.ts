import { validDate } from '../indicators/data'
import type { HistoryPoint, SourceReading } from '../indicators/types'

export const codes=['pdb','inflasi','fiskal','investasi','birate','tpt'] as const
export const names: Record<string,string>={pdb:'PDB',inflasi:'Inflasi',fiskal:'Fiskal',investasi:'Investasi',birate:'BI-Rate',tpt:'Pengangguran'}
export function indicatorCode(value: string) {return ({apbn:'fiskal','bi-rate':'birate'} as Record<string,string>)[value]??value}
export function visibleHistory(history: HistoryPoint[], year: string, range: string): HistoryPoint[] {
  let rows=history.filter(row=>!year || (row.observationDate && validDate(row.observationDate) ? Number(row.observationDate.slice(0,4)) : row.year)===Number(year))
  const dates=rows.flatMap(r=>r.observationDate&&validDate(r.observationDate)?[r.observationDate]:[]).sort()
  if(range!=='all' && dates.length){const last=dates.at(-1)!;const start=Number(last.slice(0,4))-Number(range);rows=rows.filter(row=>!!row.observationDate&&validDate(row.observationDate)&&(Number(row.observationDate.slice(0,4))>start || Number(row.observationDate.slice(0,4))===start&&row.observationDate.slice(5)>=last.slice(5)))}
  return rows
}
export function pointMatches(point: HistoryPoint, reading: SourceReading) {
  return point.value===reading.value && point.period===reading.period && point.unit===reading.unit &&
    point.observationDate===reading.observationDate && point.frequency===reading.frequency &&
    point.dataType===reading.dataType && point.sourceId===reading.source?.sourceId
}
export function errorMessage(error: unknown) {return error instanceof Error?error.message:'Permintaan tidak dapat diselesaikan.'}
