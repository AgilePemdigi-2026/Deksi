import test,{after} from 'node:test'
import assert from 'node:assert/strict'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'
import react from '@vitejs/plugin-react'
import {dto,responder} from './indicator-fixtures.mjs'
const vite=await createServer({configFile:false,plugins:[react()],cacheDir:'.artifacts/vite-pages',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(()=>vite.close())
const {DetailPage}=await vite.ssrLoadModule('/src/features/indicators/DetailPage.tsx')
const {fetchDetail}=await vite.ssrLoadModule('/src/features/indicators/api.ts')
const render=(data,extra={})=>renderToStaticMarkup(createElement(DetailPage,{code:'inflasi',selector:null,data,loading:false,onRetry(){},...extra}))
test('detail renders actual selected zero and unit, with F7 honestly unavailable',async()=>{
 const data=await fetchDetail('inflasi',null,undefined,responder(dto())),html=render(data)
 assert.match(html,/Inflasi UJI SINTETIS/)
 assert.match(html,/class="fd-metric">0</)
 assert.match(html,/Persen uji/)
 assert.match(html,/Source Trace/)
 assert.doesNotMatch(html,/href="[^"]*\/sumber/)
 assert.doesNotMatch(html,/Tervalidasi Resmi|Sumber Terverifikasi|demo-v1/)
})
test('unreachable backend retains layout, missing value, error and working retry affordance',()=>{
 const html=render(null,{error:'Backend belum terhubung.'})
 assert.match(html,/Backend belum terhubung/)
 assert.match(html,/Coba lagi/)
 assert.match(html,/Histori indikator/)
 assert.match(html,/Belum tersedia/)
 assert.doesNotMatch(html,/<polyline/)
})
test('a direct detail URL mounts the feature instead of the dashboard',async()=>{
 const previous=globalThis.window
 try {
  globalThis.window={location:{pathname:'/indikator/inflasi',search:''}}
  const {default:App}=await vite.ssrLoadModule('/src/App.tsx')
  const html=renderToStaticMarkup(createElement(App))
  assert.match(html,/06 \/ DETAIL INDIKATOR EKONOMI/)
  assert.doesNotMatch(html,/class="hero-photo-wrap"/)
 } finally {if(previous===undefined)delete globalThis.window;else globalThis.window=previous}
})
test('dashboard card exposes a real indicator link, not a disabled placeholder',async()=>{
 const {IndicatorCard}=await vite.ssrLoadModule('/src/components/IndicatorCard.tsx')
 const html=renderToStaticMarkup(createElement(IndicatorCard,{meta:{id:'inflasi',name:'UJI',category:'Uji',value:'0',unit:'%',period:'Uji',delta:'',deltaDirection:'flat',deltaPositive:false,note:'Uji sintetis',source:'Uji',sourceDate:'',sparkline:[],sparklineColor:'#111'}}))
 assert.match(html,/href="\/indikator\/inflasi"/)
})
test('invalid pinned context does not render the latest value as its replacement',async()=>{
 const data=await fetchDetail('inflasi',null,undefined,responder(dto()))
 data.selected=null;data.contextError='Konteks tidak tersedia.'
 const html=render(data,{selector:{guard:'missing'}})
 assert.match(html,/Konteks tidak tersedia/)
 assert.doesNotMatch(html,/class="fd-metric">0</)
 assert.match(html,/fd-missing/)
})
test('a missing requested guard keeps the period placeholder selected, not another available period',async()=>{
 const data=await fetchDetail('inflasi',null,undefined,responder(dto()))
 data.selected=null;data.contextError='Konteks berubah.'
 const html=render(data,{selector:{guard:'b'.repeat(64)}})
 assert.match(html,/<option value=""[^>]*selected/)
})
test('source strings are escaped, unsafe URLs inert, and date-only release is not invented',async()=>{
 const payload=dto();payload.trace.source.institution='<img src=x onerror=alert(1)>';payload.summary.indicators=[]
 payload.trace.source.primaryUrl='javascript:alert(1)';payload.trace.history=[]
 const data=await fetchDetail('inflasi',null,undefined,responder(payload)),html=render(data)
 assert.match(html,/&lt;img/)
 assert.doesNotMatch(html,/<img|href="javascript:|T00:00:00/)
})
test('loading, empty and unit-mismatch chart states stay explicit',async()=>{
 assert.match(render(null,{loading:true}),/Memuat data indikator/)
 const data=await fetchDetail('inflasi',null,undefined,responder(dto()))
 data.history.push({period:'B',unit:'rupiah',value:'3'})
 const html=render(data)
 assert.match(html,/Satuan histori tidak konsisten/)
 assert.doesNotMatch(html,/<polyline/)
 assert.match(html,/<table>/)
})
