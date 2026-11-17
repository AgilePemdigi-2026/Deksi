import { validDate } from '../indicators/data'
import type { HistoryPoint, SourceReading } from '../indicators/types'

export const codes=['pdb','inflasi','fiskal','investasi','birate','tpt'] as const
export const names: Record<string,string>={pdb:'PDB',inflasi:'Inflasi',fiskal:'Fiskal',investasi:'Investasi',birate:'BI-Rate',tpt:'Pengangguran'}
export function indicatorCode(value: string) {return ({apbn:'fiskal','bi-rate':'birate'} as Record<string,string>)[value]??value}
export function visibleHistory(history: HistoryPoint[], year: string, range: string): HistoryPoint[] {
  const rowYear=(row:HistoryPoint)=>row.observationDate&&validDate(row.observationDate)?Number(row.observationDate.slice(0,4)):row.year
  let rows=history.filter(row=>!year || rowYear(row)===Number(year))
  const years=rows.map(rowYear).filter((value):value is number=>typeof value==='number'&&Number.isInteger(value))
  if(range!=='all' && years.length){const firstYear=Math.max(...years)-Number(range)+1;rows=rows.filter(row=>{const y=rowYear(row);return typeof y==='number'&&y>=firstYear})}
  return rows
}
export function pointMatches(point: HistoryPoint, reading: SourceReading) {
  return point.value===reading.value && point.period===reading.period && point.unit===reading.unit &&
    point.observationDate===reading.observationDate && point.frequency===reading.frequency &&
    point.dataType===reading.dataType && point.sourceId===reading.source?.sourceId
}
export function errorMessage(error: unknown) {return error instanceof Error?error.message:'Permintaan tidak dapat diselesaikan.'}
