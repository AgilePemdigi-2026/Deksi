import test, {after} from 'node:test'
import assert from 'node:assert/strict'
import {createServer} from 'vite'
import {dto,responder,reading} from './indicator-fixtures.mjs'
const vite=await createServer({configFile:false,cacheDir:'.artifacts/vite-api',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(()=>vite.close())
const api=await vite.ssrLoadModule('/src/features/indicators/api.ts')
const helper=await vite.ssrLoadModule('/src/features/indicators/data.ts')
test('actual DTO shapes load a zero reading and deduplicate identical current/history without fixtures',async()=>{
  const calls=[],fake=responder(dto())
  const result=await api.fetchDetail('inflasi',null,undefined,async(url,options)=>{calls.push({url,options});return fake(url,options)})
  assert.equal(result.selected.value,'0')
  assert.equal(result.options.length,1)
  assert.equal(result.history[0].value,'0')
  assert.deepEqual(result.warnings,[])
  assert.equal(calls.length,3)
  assert(calls.every(call=>call.url.startsWith('http://localhost:8000/api/indicators/') && call.options.credentials==='omit'))
})
test('a historical selection resolves its exact context, never current latest',async()=>{
  const payload=dto()
  payload.trace.history.push(reading({value:'2',period:'Desember 1999',observationDate:'1999-12-31'}))
  const initial=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  const option=initial.options.find(o=>o.reading.value==='2')
  const url=new URL(helper.contextHref(option.reading,option.guard),'http://localhost')
  const route=helper.parseRoute(url.pathname,url.search)
  const result=await api.fetchDetail('inflasi',route.selector,undefined,responder(payload))
  assert.equal(result.selected.value,'2')
  assert.equal(result.contextError,null)
})
test('a changed source/release context is refused instead of silently showing latest',async()=>{
  const payload=dto(),initial=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  const option=initial.options[0],url=new URL(helper.contextHref(option.reading,option.guard),'http://localhost')
  const route=helper.parseRoute(url.pathname,url.search)
  payload.trace.publicationDate='2000-02-01'
  payload.trace.history=[]
  const result=await api.fetchDetail('inflasi',route.selector,undefined,responder(payload))
  assert.equal(result.selected,null)
  assert.match(result.contextError,/berubah/i)
})
test('summary and trace fetched at different times must not be combined',async()=>{
  const payload=dto();payload.summary.indicators[0].value='99'
  const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  assert.equal(result.selected,null)
  assert.match(result.contextError,/cocok|berubah/i)
})
test('source failure retains independent summary and history, without inventing source records',async()=>{
  const result=await api.fetchDetail('inflasi',null,undefined,responder(dto(),'trace'))
  assert.equal(result.selected,null);assert.equal(result.summary.value,'0');assert.equal(result.history.length,1)
  assert.equal(result.options.length,0);assert.equal(result.warnings.length,1)
})
test('all transport errors return explicit missing states and no demo fallback',async()=>{
  const result=await api.fetchDetail('inflasi',null,undefined,async()=>new Response('',{status:503}))
  assert.equal(result.summary,null);assert.equal(result.selected,null)
  assert.deepEqual(result.history,[]);assert.deepEqual(result.options,[]);assert.equal(result.warnings.length,3)
})
test('empty API bodies stay empty rather than selecting a different indicator',async()=>{
  const result=await api.fetchDetail('inflasi',null,undefined,responder({summary:{indicators:[]},trend:{id:'inflasi',available:false},trace:{indicatorCode:'inflasi',available:false}}))
  assert.equal(result.summary,null);assert.equal(result.selected,null);assert.equal(result.options.length,0);assert.equal(result.history.length,0)
})
test('wrong indicator and malformed number payloads are rejected per resource',async()=>{
  const payload=dto();payload.trace.indicatorCode='pdb';payload.summary.indicators[0].value=0;payload.trend.id='pdb'
  const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  assert.equal(result.selected,null);assert.equal(result.summary,null);assert.equal(result.warnings.length,3)
})
test('conflicting candidates are not offered as an arbitrary period choice',async()=>{
  const payload=dto();payload.trace.history.push(reading({value:'3'}))
  const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  assert.equal(result.selected,null);assert.equal(result.options.length,0);assert.match(result.contextError,/cocok|ambigu/)
})
test('a missing historical context does not fall back to a valid latest reading',async()=>{
  const selector={date:'1999-01-31',frequency:'monthly',dataType:'yoy',sourceId:'TEST_ONLY',guard:'a'.repeat(64)}
  const result=await api.fetchDetail('inflasi',selector,undefined,responder(dto()))
  assert.equal(result.selected,null);assert.match(result.contextError,/tidak tersedia/)
})
test('partial metadata and null values remain missing, not copied from another observation',async()=>{
  const payload=dto();payload.summary.indicators=[];payload.trace={...reading({value:null,rawFile:null,source:null}),history:[]}
  const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  assert.equal(result.selected.value,null);assert.equal(result.selected.rawFile,null);assert.equal(result.selected.source,null);assert.equal(result.options.length,0)
})
test('aborted requests cannot publish a ready result even if an injected transport ignores cancellation',async()=>{
  const controller=new AbortController();controller.abort()
  await assert.rejects(api.fetchDetail('inflasi',null,controller.signal,responder(dto())),error=>error.name==='AbortError')
})
