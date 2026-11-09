import { useEffect, useState } from 'react'
import { parseCategories, parseDashboard, parseHistory, requestJson } from './client'
import type { DashboardFilters } from './client'
import { fetchDetail } from '../indicators/api'
import { errorMessage } from './model'

export function useResource<T>(key: string, load: (signal: AbortSignal)=>Promise<T>) {
  const [attempt,setAttempt]=useState(0)
  const requestKey=`${key}:${attempt}`
  const [result,setResult]=useState<{key:string;data:T|null;error:string|null}|null>(null)
  useEffect(()=>{
    const controller=new AbortController()
    void load(controller.signal).then(data=>{if(!controller.signal.aborted)setResult({key:requestKey,data,error:null})}).catch(error=>{if(!controller.signal.aborted)setResult({key:requestKey,data:null,error:errorMessage(error)})})
    return ()=>controller.abort()
    // A stable semantic request key, not callback identity, owns this request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[requestKey])
  const current=result?.key===requestKey?result:null
  return {data:current?.data??null,error:current?.error??null,loading:current===null,retry:()=>setAttempt(n=>n+1)}
}
export function useDashboard(filters: DashboardFilters) {
  const query=new URLSearchParams()
  if(filters.category)query.set('category',filters.category)
  if(filters.year)query.set('year',filters.year)
  const path='/api/indicators/dashboard/'+(query.size?'?'+query:'')
  return useResource(path,async signal=>parseDashboard(await requestJson(path,{},signal)))
}
export function useCategories() {return useResource('categories',async signal=>parseCategories(await requestJson('/api/indicators/categories/',{},signal)))}
export function useHistory(code: string, granularity: string) {
  const path=`/api/indicators/${encodeURIComponent(code)}/trend/`+(granularity==='native'?'':'?'+new URLSearchParams({granularity}))
  return useResource(path,async signal=>parseHistory(await requestJson(path,{},signal),code))
}
export function useTraceOptions(code: string) {return useResource('trace:'+code,signal=>fetchDetail(code,null,signal))}
