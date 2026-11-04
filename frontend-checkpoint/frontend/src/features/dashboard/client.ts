import type { HistoryPoint } from '../indicators/types'
import { decimalPattern } from '../indicators/data'

export interface DashboardFilters { category: string; year: string }
export interface DashboardCard {
  id: string; available: boolean; name: string; category: string; value: string | null; unit: string | null;
  period: string | null; observationDate: string | null; frequency: string | null; dataType: string | null;
  sourceId: string | null; source: string | null; publicationDate: string | null; retrievedAt: string | null;
  note: string | null; delta: string | null; changeValue: string | null; changeUnit: string | null;
  sparkline: number[];
}
export interface DashboardPayload {
  indicators: DashboardCard[]; updatedAtFormatted: string | null;
  activeFilters: { category?: string; year?: number };
}
export interface Category { category: string; codes: string[] }
export interface FeedbackCategory { value: string; label: string }
export interface FeedbackPayload {
  category: string; description: string; sender_name?: string; sender_email?: string;
  related_indicator_code?: string; related_period?: string;
}
export function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Format respons API tidak sesuai.')
  return value as Record<string, unknown>
}
export function text(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value !== 'string') throw new Error('Format metadata API tidak sesuai.')
  return value
}
function decimal(value: unknown) {
  const result=text(value)
  if (result !== null && (result.length > 80 || !decimalPattern.test(result))) throw new Error('Format angka API tidak sesuai.')
  return result
}
export async function requestJson(path: string, options: RequestInit = {}, signal?: AbortSignal, fetcher: typeof fetch = fetch, timeoutMs=10000): Promise<unknown> {
  if (!path.startsWith('/api/') || path.startsWith('//')) throw new Error('Jalur API tidak diizinkan.')
  const controller=new AbortController()
  const abort=()=>controller.abort(signal?.reason ?? new DOMException('Dibatalkan','AbortError'))
  if (signal?.aborted) abort()
  signal?.addEventListener('abort',abort,{once:true})
  let rejectAbort: () => void = ()=>{}
  const cancelled=new Promise<never>((_,reject)=>{rejectAbort=()=>reject(controller.signal.reason);controller.signal.addEventListener('abort',rejectAbort,{once:true})})
  const timer=setTimeout(()=>controller.abort(new DOMException('Batas waktu request terlampaui.','TimeoutError')),timeoutMs)
  try {
    if (controller.signal.aborted) throw controller.signal.reason
    return await Promise.race([cancelled,(async()=>{
      const response=await fetcher(path,{...options,credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal})
      if (!response.ok) throw new Error(response.status===403?'Pemeriksaan keamanan ditolak (HTTP 403). Muat ulang kategori dan coba lagi.':`Request gagal (HTTP ${response.status}).`)
      return response.json()
    })()])
  } finally {clearTimeout(timer);signal?.removeEventListener('abort',abort);controller.signal.removeEventListener('abort',rejectAbort)}
}
export function parseDashboard(raw: unknown): DashboardPayload {
  const body=object(raw)
  if (!Array.isArray(body.indicators)) throw new Error('Daftar indikator belum tersedia.')
  const indicators=body.indicators.map(value=>{
    const row=object(value)
    const id=text(row.id)
    if (!id || !/^[a-z][a-z0-9_-]{0,31}$/.test(id) || typeof row.available!=='boolean') throw new Error('Identitas indikator tidak sesuai.')
    const amount=decimal(row.value)
    if ((!row.available && amount!==null) || (row.available && amount===null)) throw new Error('Ketersediaan angka tidak konsisten.')
    const card: DashboardCard={id,available:row.available,name:text(row.name)??id,category:text(row.category)??'',value:amount,
      unit:text(row.unit),period:text(row.period),observationDate:text(row.observationDate),frequency:text(row.frequency),dataType:text(row.dataType),
      sourceId:text(row.sourceId),source:text(row.source),publicationDate:text(row.publicationDate),retrievedAt:text(row.retrievedAt),
      note:text(row.dataAvailabilityNote)??text(row.note),delta:text(row.delta),changeValue:decimal(row.changeValue),changeUnit:text(row.changeUnit),
      sparkline:Array.isArray(row.sparkline)?row.sparkline.map(v=>{if(typeof v!=='number'||!Number.isFinite(v))throw new Error('Sparkline tidak sesuai.');return v}):[]}
    return card
  })
  if(new Set(indicators.map(r=>r.id)).size!==indicators.length)throw new Error('Indikator ringkasan ambigu.')
  return {indicators,updatedAtFormatted:text(body.updatedAtFormatted),activeFilters:body.activeFilters?object(body.activeFilters):{}}
}
export function parseCategories(raw: unknown): Category[] {
  const body=object(raw)
  if(!Array.isArray(body.categories))throw new Error('Kategori tidak tersedia.')
  return body.categories.map(value=>{const row=object(value);if(typeof row.category!=='string'||!Array.isArray(row.codes)||row.codes.some(x=>typeof x!=='string'))throw new Error('Kategori tidak sesuai.');return {category:row.category,codes:row.codes as string[]}})
}
export function parseHistory(raw: unknown, code: string) {
  const body=object(raw)
  if(body.id!==code)throw new Error('Identitas histori tidak cocok.')
  const granularities=Array.isArray(body.granularities)?body.granularities.filter((x):x is string=>typeof x==='string'):[]
  if(body.available===false)return {points:[] as HistoryPoint[],granularities,note:text(body.note)}
  if(!Array.isArray(body.points))throw new Error('Histori tidak sesuai.')
  const points=body.points.map(value=>{
    const row=object(value);const exact=decimal(row.exactValue)
    if(row.value!=null&&(typeof row.value!=='number'||!Number.isFinite(row.value)))throw new Error('Geometri histori tidak sesuai.')
    if((row.value==null)!==(exact===null)||(exact!==null&&Number(exact)!==row.value))throw new Error('Presisi histori tidak konsisten.')
    const unit=text(row.unit)??text(body.unit),period=text(row.label)
    if(!unit||!period)throw new Error('Metadata histori tidak lengkap.')
    if(row.year!=null && (!Number.isInteger(row.year) || Number(row.year)<1 || Number(row.year)>9999))throw new Error('Tahun histori tidak sesuai.')
    return {period,unit,value:exact,year:typeof row.year==='number'?row.year:undefined,observationDate:text(row.observationDate)??undefined,sourceId:text(row.sourceId),frequency:text(row.frequency)??text(body.frequency),dataType:text(row.dataType)??text(body.dataType)}
  })
  return {points,granularities,note:text(body.note)}
}
export function createFeedbackClient(fetcher: typeof fetch=fetch) {
  let csrfToken=''
  return {
    async categories(signal?: AbortSignal): Promise<FeedbackCategory[]> {
      const body=object(await requestJson('/api/feedback/categories/',{},signal,fetcher))
      if(typeof body.csrfToken!=='string'||!body.csrfToken||!Array.isArray(body.categories))throw new Error('Token keamanan atau kategori belum tersedia.')
      csrfToken=body.csrfToken
      return body.categories.map(value=>{const row=object(value);if(typeof row.value!=='string'||typeof row.label!=='string')throw new Error('Kategori feedback tidak sesuai.');return {value:row.value,label:row.label}})
    },
    async submit(payload: FeedbackPayload,signal?: AbortSignal) {
      if(!csrfToken)throw new Error('Muat kategori untuk memperoleh token keamanan terlebih dahulu.')
      const body=object(await requestJson('/api/feedback/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify(payload)},signal,fetcher))
      if(body.status!=='pending'||!Number.isSafeInteger(body.id)||typeof body.message!=='string')throw new Error('Konfirmasi penyimpanan belum valid. Jangan kirim ulang sebelum memeriksa hasil.')
      return {id:body.id as number,status:'pending' as const,message:body.message}
    },
  }
}
