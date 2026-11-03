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
  assert(calls.every(call=>call.url.startsWith('/api/indicators/') && call.options.credentials==='omit'))
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
test('a stalled source request times out while independent summary and history survive',async()=>{
  let requestSignal
  const fetcher=async(url,options)=>{
    if(url.endsWith('/source-trace/')){requestSignal=options.signal;return new Promise(()=>{})}
    return responder(dto())(url)
  }
  let timer
  try {
    const result=await Promise.race([api.fetchDetail('inflasi',null,undefined,fetcher,20),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Request deadline did not settle')),500)})])
    assert.equal(result.summary.value,'0');assert.equal(result.history.length,1)
    assert.equal(result.selected,null);assert.match(result.warnings.join(' '),/Timeout|waktu/i)
    assert.equal(requestSignal.aborted,true)
  } finally {clearTimeout(timer)}
})
test('a stalled JSON body has the same deadline as the HTTP request',async()=>{
  const result=await api.fetchDetail('inflasi',null,undefined,async()=>({ok:true,json:()=>new Promise(()=>{})}),20)
  assert.equal(result.warnings.length,3);assert.equal(result.summary,null);assert.equal(result.selected,null)
})
test('parent cancellation promptly settles child requests that ignore their abort signal',async()=>{
  const controller=new AbortController(),signals=[]
  const request=api.fetchDetail('inflasi',null,controller.signal,async(_,options)=>{signals.push(options.signal);return new Promise(()=>{})},500)
  controller.abort()
  await assert.rejects(request,error=>error.name==='AbortError')
  assert.equal(signals.length,3);assert(signals.every(signal=>signal.aborted))
})
test('history preserves backend exact decimal strings beyond numeric plot precision',async()=>{
  for(const exact of ['999999999999999999.999999','-9007199254740993.125','0','0.000001']){
    const payload=dto()
    payload.trend.points=[{label:'UJI',observationDate:'2000-01-31',unit:'Rp',value:Number(exact),exactValue:exact}]
    const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
    assert.equal(result.history[0].value,exact)
    assert.equal(payload.trend.points[0].exactValue,exact)
  }
})
test('invalid or conflicting exact history values fail only the history resource',async()=>{
  for(const [numeric,exact] of [[1,'2'],[0,null],[null,'0'],[1,1],[1,'NaN'],[1,'1e0']]){
    const payload=dto();payload.trend.points[0].value=numeric;payload.trend.points[0].exactValue=exact
    const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
    assert.equal(result.history.length,0,JSON.stringify({numeric,exact}))
    assert.equal(result.warnings.length,1)
    assert.equal(result.summary.value,'0')
  }
  const payload=dto();payload.trend.points[0].value=null;payload.trend.points[0].exactValue=null
  assert.equal((await api.fetchDetail('inflasi',null,undefined,responder(payload))).history[0].value,null)
})
test('history keeps source identities so different sources cannot become one chart series',async()=>{
  const payload=dto()
  payload.trend.points=[
    {label:'Jan',observationDate:'2000-01-31',value:1,unit:'%',frequency:'monthly',dataType:'yoy',sourceId:'SOURCE_A'},
    {label:'Feb',observationDate:'2000-02-29',value:2,unit:'%',frequency:'monthly',dataType:'yoy',sourceId:'SOURCE_B'},
  ]
  const result=await api.fetchDetail('inflasi',null,undefined,responder(payload))
  assert.deepEqual(result.history.map(p=>p.sourceId),['SOURCE_A','SOURCE_B'])
  assert.equal(helper.chartGeometry(result.history,'%'),null)
})
