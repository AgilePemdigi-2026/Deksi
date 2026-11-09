import { useEffect, useState } from 'react'
import { createFeedbackClient } from './client'
import type { FeedbackCategory, FeedbackPayload } from './client'
import { errorMessage } from './model'
export type { FeedbackPayload } from './client'
export interface FeedbackResult {id:number|null;status:'idle'|'loading'|'success'|'error';message:string}
const client=createFeedbackClient()
export function useFeedbackCategories() {
  const [categories,setCategories]=useState<FeedbackCategory[]>([])
  const [error,setError]=useState<string|null>(null)
  const [attempt,setAttempt]=useState(0)
  useEffect(()=>{
    const controller=new AbortController()
    void client.categories(controller.signal).then(rows=>{if(!controller.signal.aborted){setCategories(rows);setError(null)}}).catch(reason=>{if(!controller.signal.aborted){setCategories([]);setError(errorMessage(reason))}})
    return ()=>controller.abort()
  },[attempt])
  return {categories,error,retry:()=>setAttempt(n=>n+1)}
}
export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackResult> {
  try {
    // Refresh a token for the current cookie before each explicit submission; never retry a POST.
    await client.categories()
    const response=await client.submit(payload)
    return {id:response.id,status:'success',message:response.message}
  } catch(error) {return {id:null,status:'error',message:errorMessage(error)}}
}
