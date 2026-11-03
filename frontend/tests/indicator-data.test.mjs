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
