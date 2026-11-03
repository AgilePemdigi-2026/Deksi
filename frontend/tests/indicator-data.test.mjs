import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
const vite = await createServer({configFile:false,cacheDir:'.artifacts/vite-data',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(() => vite.close())
const data = await vite.ssrLoadModule('/src/features/indicators/data.ts')
test('public detail route resolves without an admin session', () => {
  assert.deepEqual(data.parseRoute('/indikator/inflasi'), {kind:'detail',code:'inflasi',selector:null})
})
test('root remains dashboard and malformed/unsupported revision routes never become latest', () => {
  assert.equal(data.parseRoute('/').kind,'dashboard')
  for(const [path,query] of [['/indikator/%ZZ',''],['/indikator/inflasi','?revisi=demo-v1'],['/indikator/inflasi','?tanggal=2000-01-01'],['/random','']])
    assert.equal(data.parseRoute(path,query).kind,'not-found')
})
test('exact decimal formatting preserves zero, null and digits beyond IEEE precision',()=>{
  assert.equal(data.formatDecimal(null),'Belum tersedia')
  assert.equal(data.formatDecimal('0'),'0')
  assert.equal(data.formatDecimal('9007199254740993.125'),'9.007.199.254.740.993,125')
  assert.equal(data.formatDecimal('NaN'),'Belum tersedia')
})
test('source URLs refuse executable, credentialed, malformed and backslash forms',()=>{
  for(const url of ['javascript:alert(1)','data:text/html,x','//example.com',' https://example.com','https://u:p@example.com','https://example.com\\x','https://example.com\n/x',null]) assert.equal(data.safeExternalUrl(url),null)
  assert.equal(data.safeExternalUrl('https://example.com/doc'),'https://example.com/doc')
})
test('ported chart separates missing points, preserves zero and refuses mixed units',()=>{
  const points=[{period:'a',value:'2',unit:'%'},{period:'b',value:null,unit:'%'},{period:'c',value:'0',unit:'%'}]
  const chart=data.chartGeometry(points,'%')
  assert.equal(chart.segments.length,2)
  assert.equal(chart.points[1].value,'0')
  assert.equal(data.chartGeometry(points,'rupiah'),null)
  for(const values of [['0'],['2','2'],[null]]) {
    const result=data.chartGeometry(values.map(value=>({period:'uji',value,unit:'%'})),'%')
    assert(result.points.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)))
  }
})
test('strict context route rejects duplicate query, invalid calendar and arbitrary unknown parameters',()=>{
  const query='tanggal=2000-01-31&tipe=yoy&frekuensi=monthly&sumber=TEST_ONLY&konteks='+'a'.repeat(64)
  assert.equal(data.parseRoute('/indikator/inflasi','?'+query).kind,'detail')
  for(const changed of [query+'&tanggal=2000-01-31',query.replace('2000-01-31','2000-02-31'),query+'&revisi=made-up',query.replace('monthly','invalid')]) assert.equal(data.parseRoute('/indikator/inflasi','?'+changed).kind,'not-found')
})
test('Y scale stays finite for negative, constant, zero, missing and large series',()=>{
 for(const values of [['-2','2'],['0'],['2','2'],[null],['1000000000000','2000000000000']]){
  const chart=data.chartGeometry(values.map(value=>({period:'uji',value,unit:'%'})),'%')
  assert(chart.ticks.every(tick=>Number.isFinite(tick.y)&&!tick.label.includes('NaN')))
  assert.equal(chart.ticks.length,values[0]===null?0:values[0]===values.at(-1)?1:3)
 }
})
test('nearby scale values retain distinct labels without changing source values',()=>{
 for(const values of [['5.000001','5.000002'],['-5.000002','-5.000001'],['1000000000000','1000000000001'],['0.0000001000001','0.0000001000002']]){
  const input=values.map(value=>({period:'uji',value,unit:'%'})),before=JSON.stringify(input)
  const chart=data.chartGeometry(input,'%')
  assert.equal(new Set(chart.ticks.map(tick=>tick.label)).size,3,JSON.stringify(chart.ticks))
  assert.deepEqual(chart.points.map(point=>point.value),values)
  assert.equal(JSON.stringify(input),before)
 }
 assert.deepEqual(data.chartGeometry(['0','2'].map(value=>({period:'uji',value,unit:'%'})),'%').ticks.map(tick=>tick.label),['2','1','0'])
})
