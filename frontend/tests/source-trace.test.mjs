import test,{after} from 'node:test'
import assert from 'node:assert/strict'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'
import react from '@vitejs/plugin-react'
import {dto,responder,reading} from './indicator-fixtures.mjs'
const vite=await createServer({configFile:false,plugins:[react()],cacheDir:'.artifacts/vite-source-tests',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(()=>vite.close())
const {SourceTracePage}=await vite.ssrLoadModule('/src/features/indicators/SourceTracePage.tsx')
const {fetchDetail}=await vite.ssrLoadModule('/src/features/indicators/api.ts')
const {rawDownloadHref}=await vite.ssrLoadModule('/src/features/indicators/source.ts')
const {contextHref,parseRoute}=await vite.ssrLoadModule('/src/features/indicators/data.ts')
const render=(data,extra={})=>renderToStaticMarkup(createElement(SourceTracePage,{code:'inflasi',selector:null,data,loading:false,onRetry(){},...extra}))
test('source page displays selected zero, exact context return and honest unavailable calculation fields',async()=>{
 const data=await fetchDetail('inflasi',null,undefined,responder(dto())),html=render(data)
 assert.match(html,/class="ft-value">0</)
 assert.match(html,/class="ft-value-period">Januari 2000<\/span>/)
 assert.match(html,/INSTANSI UJI SINTETIS/)
 assert.match(html,/href="\/indikator\/inflasi\?tanggal=2000-01-31/)
 assert.match(html,/Formula belum tersedia/)
 assert.match(html,/Input perhitungan belum disediakan/)
 assert.match(html,/Riwayat revisi belum tersedia/)
 assert.doesNotMatch(html,/Tervalidasi Resmi|DEKSI-Derived Metric|demo-v1/)
})
test('missing source context renders empty/error without a latest detail return link',()=>{
 const html=render(null,{error:'Metadata sumber belum dapat dimuat.'})
 assert.match(html,/Metadata sumber belum dapat dimuat/)
 assert.match(html,/Coba lagi/)
 assert.match(html,/Belum tersedia/)
 assert.doesNotMatch(html,/href="\/indikator\/inflasi\?/)
})
test('RAW links bind the exact indicator path to the configured API origin',()=>{
 assert.equal(rawDownloadHref('/api/indicators/inflasi/raw-file/1/','inflasi'),'http://localhost:8000/api/indicators/inflasi/raw-file/1/')
 for(const url of ['/api/indicators/pdb/raw-file/1/','//evil.test/api/indicators/inflasi/raw-file/1/','https://evil.test/file','/api/indicators/inflasi/raw-file/1/?next=evil','/api/indicators/inflasi/raw-file/../1/','/api/indicators/inflasi/raw-file/0/','/api/indicators/inflasi/raw-file/1/\n',null]) assert.equal(rawDownloadHref(url,'inflasi'),null)
})
test('Detail links only to its exact matching Source Trace context',async()=>{
 const data=await fetchDetail('inflasi',null,undefined,responder(dto()))
 const {DetailPage}=await vite.ssrLoadModule('/src/features/indicators/DetailPage.tsx')
 const html=renderToStaticMarkup(createElement(DetailPage,{code:'inflasi',selector:null,data,loading:false,onRetry(){}}))
 assert.match(html,/href="\/indikator\/inflasi\/sumber\?tanggal=2000-01-31/)
 data.contextError='Konteks tidak cocok'
 const disabled=renderToStaticMarkup(createElement(DetailPage,{code:'inflasi',selector:null,data,loading:false,onRetry(){}}))
 assert.doesNotMatch(disabled,/href="[^"]*\/sumber/)
})
test('source deep-link mounts the implemented F7 page instead of the unavailable placeholder',async()=>{
 const previous=globalThis.window
 try {
  globalThis.window={location:{pathname:'/indikator/inflasi/sumber',search:''}}
  const {default:App}=await vite.ssrLoadModule('/src/App.tsx')
  const html=renderToStaticMarkup(createElement(App))
  assert.match(html,/07 \/ SOURCE TRACE DATA/)
  assert.doesNotMatch(html,/Source Trace belum dipasang/)
 } finally {if(previous===undefined)delete globalThis.window;else globalThis.window=previous}
})
test('historical Source Trace return retains the entire selected query, value, unit and source',async()=>{
 const payload=dto();payload.trace.history.push(reading({value:'2',period:'Desember 1999',observationDate:'1999-12-31',rawFile:null}))
 const initial=await fetchDetail('inflasi',null,undefined,responder(payload))
 const option=initial.options.find(row=>row.reading.value==='2')
 const sourceUrl=new URL(contextHref(option.reading,option.guard,true),'http://localhost')
 const route=parseRoute(sourceUrl.pathname,sourceUrl.search)
 const data=await fetchDetail('inflasi',route.selector,undefined,responder(payload)),html=render(data,{selector:route.selector})
 const back=html.match(/class="ft-actions"><a class="fd-button" href="([^"]+)"/)[1].replaceAll('&amp;','&')
 assert.equal(back,contextHref(option.reading,option.guard))
 assert.match(html,/class="ft-value">2</)
 assert.equal(data.selected.unit,option.reading.unit)
 assert.deepEqual(data.selected.source,option.reading.source)
 assert.equal(data.selected.rawFile,null)
 assert.doesNotMatch(html,/href="https:\/\/example.com\/test\/document"|Unduh RAW dari API/)
})
test('changed value, unit, institution, release or RAW refuses the source guard without a latest return',async()=>{
 const initial=await fetchDetail('inflasi',null,undefined,responder(dto())),option=initial.options[0]
 const url=new URL(contextHref(option.reading,option.guard,true),'http://localhost'),route=parseRoute(url.pathname,url.search)
 for(const change of [row=>row.value='7',row=>row.unit='Unit berubah',row=>row.source.institution='Instansi berubah',row=>row.publicationDate='2000-02-01',row=>row.rawFile.checksumSha256='b'.repeat(64)]){
  const payload=dto();payload.trace.history=[];change(payload.trace)
  const data=await fetchDetail('inflasi',route.selector,undefined,responder(payload)),html=render(data,{selector:route.selector})
  assert.equal(data.selected,null)
  assert.match(html,/Konteks nilai atau sumber telah berubah/)
  assert.doesNotMatch(html,/class="ft-value">0<|Detail indikator<\/a>/)
  assert.match(html,/Tautan kembali ke detail dinonaktifkan/)
 }
})
test('missing and ambiguous source observations do not choose latest as a replacement',async()=>{
 const payload=dto();payload.trace.history.push(reading({value:'3'}))
 const ambiguous=await fetchDetail('inflasi',null,undefined,responder(payload))
 assert.equal(ambiguous.options.length,0)
 assert.match(render(ambiguous),/Ringkasan dan metadata sumber tidak cocok atau konteks berubah/)
 assert.equal(ambiguous.selected,null)
 const selector={date:'1990-01-31',dataType:'yoy',frequency:'monthly',sourceId:'TEST_ONLY',guard:'a'.repeat(64)}
 const missing=await fetchDetail('inflasi',selector,undefined,responder(dto()))
 assert.equal(missing.selected,null)
 assert.doesNotMatch(render(missing,{selector}),/class="ft-value">0<|Detail indikator<\/a>/)
})
test('source failure never borrows the summary value or another record metadata',async()=>{
 const data=await fetchDetail('inflasi',null,undefined,responder(dto(),'trace')),html=render(data)
 assert.equal(data.summary.value,'0')
 assert.match(html,/class="ft-value">Belum tersedia</)
 assert.doesNotMatch(html,/INSTANSI UJI SINTETIS|Dokumen uji sintetis|Unduh RAW dari API/)
})
test('untrusted source strings are escaped; unsafe external and mismatching RAW URLs are inert',async()=>{
 const payload=dto();payload.summary.indicators=[];payload.trace.history=[]
 payload.trace.source.institution='<img src=x onerror=alert(1)>'
 payload.trace.source.primaryUrl='javascript:alert(1)'
 payload.trace.rawFile.sourceUrl='data:text/html,unsafe'
 payload.trace.rawFile.downloadUrl='/api/indicators/pdb/raw-file/1/'
 const html=render(await fetchDetail('inflasi',null,undefined,responder(payload)))
 assert.match(html,/&lt;img/)
 assert.doesNotMatch(html,/<img|href="javascript:|href="data:|Unduh RAW dari API/)
})
test('date-only release stays date-only and valid RAW is a direct API link, not a source fetch',async()=>{
 const payload=dto();payload.summary.indicators=[];payload.trace.history=[];payload.trace.publicationDate='2000-02-01'
 const html=render(await fetchDetail('inflasi',null,undefined,responder(payload)))
 assert.match(html,/2000-02-01 \(tanggal saja\)/)
 assert.doesNotMatch(html,/2000-02-01T00:00:00/)
 assert.match(html,/href="http:\/\/localhost:8000\/api\/indicators\/inflasi\/raw-file\/1\/"/)
})
test('loading, null source and null value remain explicit with no fabricated formulas or references',async()=>{
 assert.match(render(null,{loading:true}),/aria-busy="true"|Memuat metadata sumber/)
 const payload=dto();payload.summary.indicators=[];payload.trace={...reading({value:null,rawFile:null,source:null}),history:[]}
 const html=render(await fetchDetail('inflasi',null,undefined,responder(payload)))
 assert.match(html,/class="ft-value">Belum tersedia</)
 assert.doesNotMatch(html,/href="http:\/\/localhost:8000|class="ft-value">0</)
 assert.match(html,/Daftar referensi terstruktur belum disediakan/)
})
