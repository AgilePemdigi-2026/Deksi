import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
const vite=await createServer({configFile:false,cacheDir:'.artifacts/dashboard-unit',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(()=>vite.close())
const client=await vite.ssrLoadModule('/src/features/dashboard/client.ts')
const data=await vite.ssrLoadModule('/src/features/dashboard/model.ts')
const history=[
 {period:'Desember',observationDate:'2023-12-31',value:'0',unit:'%',frequency:'monthly',dataType:'yoy',sourceId:'A'},
 {period:'Januari',observationDate:'2024-01-31',value:'9007199254740993.125',unit:'%',frequency:'monthly',dataType:'yoy',sourceId:'A'},
 {period:'Maret',observationDate:'2024-03-31',value:null,unit:'%',frequency:'monthly',dataType:'yoy',sourceId:'A'},
 {period:'Januari',observationDate:'2025-01-31',value:'9',unit:'%',frequency:'monthly',dataType:'yoy',sourceId:'A'}]
test('filter keeps dates/exact strings and never substitutes another year or invents missing values',()=>{
 const before=JSON.stringify(history)
 assert.deepEqual(data.visibleHistory(history,'2024','all').map(p=>p.value),['9007199254740993.125',null])
 assert.deepEqual(data.visibleHistory(history,'2022','all'),[])
 assert.equal(data.visibleHistory(history,'','3').length,4)
 assert.equal(JSON.stringify(history),before)
 assert.equal(data.indicatorCode('apbn'),'fiskal');assert.equal(data.indicatorCode('bi-rate'),'birate')
})
test('summary parser accepts unavailable partial metadata and retains zero and measurement semantics',()=>{
 const rows=client.parseDashboard({indicators:[{id:'pdb',available:false,value:null},{id:'inflasi',available:true,value:'0',unit:'%',period:'UJI',frequency:'monthly',dataType:'yoy',sourceId:'A'}]})
 assert.equal(rows.indicators[0].value,null);assert.equal(rows.indicators[1].value,'0')
 assert.throws(()=>client.parseDashboard({indicators:[{id:'pdb',available:true,value:0}]}))
 assert.throws(()=>client.parseDashboard({indicators:[{id:'pdb',available:false,value:'0'}]}))
})
test('feedback uses same-origin csrf bootstrap, preserves cookie credentials, and never persists tokens',async()=>{
 const calls=[],responses=[{categories:[{value:'data',label:'Data'}],csrfToken:'synthetic-csrf'}, {id:4,status:'pending',message:'Diterima'}]
 const c=client.createFeedbackClient(async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(responses.shift()),{status:calls.length===2?201:200})})
 await c.categories();const r=await c.submit({category:'data',description:'UJI valid description'})
 assert.equal(r.status,'pending');assert.equal(calls[0].url,'/api/feedback/categories/')
 assert.equal(calls[1].options.headers['X-CSRFToken'],'synthetic-csrf')
 assert(calls.every(c=>c.options.credentials==='same-origin'))
 assert(calls.every(c=>c.options.cache==='no-store'))
})
test('feedback rejects html csrf errors honestly, never retries a POST or pretends success',async()=>{
 let n=0;const c=client.createFeedbackClient(async()=>{n++;return n===1?new Response(JSON.stringify({categories:[],csrfToken:'test'})):new Response('<h1>Forbidden</h1>',{status:403})})
 await c.categories();await assert.rejects(c.submit({category:'data',description:'UJI valid description'}),/403|keamanan/)
 assert.equal(n,2)
})
test('deadlines cover body parsing even when transport ignores cancellation',async()=>{
 await assert.rejects(client.requestJson('/api/test',{},undefined,async()=>({ok:true,json:()=>new Promise(()=>{})}),10),/waktu|Timeout/)
})
test('native selection binds an exact historical source, not the current summary',async()=>{
 const reading={indicatorCode:'inflasi',indicatorName:'UJI',value:'0',unit:'%',period:'Desember',observationDate:'2023-12-31',frequency:'monthly',dataType:'yoy',source:{sourceId:'A'}}
 assert(data.pointMatches(history[0],reading));assert(!data.pointMatches(history[1],reading))
})
test('year filter retains annual aggregates without inventing an observation date',()=>{
 const result=client.parseHistory({id:'inflasi',available:true,granularities:['Bulanan','Tahunan'],points:[
  {label:'2024',year:2024,value:2.62,exactValue:'2.62',unit:'%',sourceId:'A',frequency:'annual',dataType:'yoy'},
  {label:'2025',year:2025,value:0,exactValue:'0',unit:'%',sourceId:'A',frequency:'annual',dataType:'yoy'}]},'inflasi')
 assert.deepEqual(data.visibleHistory(result.points,'2024','all').map(p=>p.value),['2.62'])
 assert.equal(result.points[0].observationDate,undefined)
 assert.deepEqual(data.visibleHistory(result.points,'2022','all'),[])
})
