import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'

const vite = await createServer({configFile:false,cacheDir:'.artifacts/vite-batch2',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(() => vite.close())
const data = await vite.ssrLoadModule('/src/features/indicators/data.ts')
const model = await vite.ssrLoadModule('/src/features/dashboard/model.ts')

const p = (date, value='1', frequency='monthly') => ({period:date,observationDate:date,value,unit:'%',frequency,dataType:'level',sourceId:'A'})

test('3/5/10 year ranges include exactly that many calendar years through the latest observed year', () => {
  const history = ['2019-01-31','2020-01-31','2021-01-31','2022-01-31','2023-01-31','2024-01-31','2025-01-31'].map(date=>({...p(date),year:Number(date.slice(0,4))}))
  assert.deepEqual(model.visibleHistory(history,'','3').map(row=>row.observationDate),['2023-01-31','2024-01-31','2025-01-31'])
  assert.deepEqual(model.visibleHistory(history,'','5').map(row=>row.observationDate),['2021-01-31','2022-01-31','2023-01-31','2024-01-31','2025-01-31'])
  assert.deepEqual(model.visibleHistory(history,'','10'),history)
})

test('calendar year filtering composes with ranges and uses the selected year as the range endpoint', () => {
  const history = ['2020-02-29','2021-02-28','2022-02-28','2023-02-28'].map(date=>({...p(date),year:Number(date.slice(0,4))}))
  assert.deepEqual(model.visibleHistory(history,'2023','3').map(row=>row.observationDate),['2023-02-28'])
})

test('year-only aggregated history respects calendar range without inventing dates', () => {
  const history=[2020,2021,2022,2023,2024,2025].map(year=>({period:String(year),year,value:String(year),unit:'%',frequency:'annual',dataType:'level',sourceId:'A'}))
  const before=JSON.stringify(history)
  assert.deepEqual(model.visibleHistory(history,'','3').map(row=>row.year),[2023,2024,2025])
  assert.deepEqual(model.visibleHistory(history,'','5').map(row=>row.year),[2021,2022,2023,2024,2025])
  assert.deepEqual(model.visibleHistory(history,'2022','3').map(row=>row.year),[2022])
  assert.equal(JSON.stringify(history),before)
  assert(history.every(row=>row.observationDate===undefined))
})

test('regular monthly, quarterly, semiannual and annual calendar gaps split chart lines', () => {
  const cases = [
    ['monthly',['2024-01-31','2024-03-31']],
    ['quarterly',['2024-03-31','2024-09-30']],
    ['semiannual',['2024-02-29','2025-02-28']],
    ['annual',['2022-12-31','2024-12-31']],
  ]
  for (const [frequency,dates] of cases) {
    const chart = data.chartGeometry(dates.map((date,i)=>p(date,String(i+1),frequency)),'%')
    assert.equal(chart.segments.length,2,frequency)
    assert.equal(chart.points.length,2,frequency)
  }
})

test('annual year-only aggregates split missing years without inventing dates', () => {
  const rows=[2020,2022].map(year=>({period:String(year),year,value:String(year),unit:'%',frequency:'annual',dataType:'level',sourceId:'A'}))
  const before=JSON.stringify(rows)
  assert.equal(data.chartGeometry(rows,'%').segments.length,2)
  assert.equal(JSON.stringify(rows),before)
})

test('monthly aggregates with year-month labels split missing months without inventing dates', () => {
  const rows=['2024-01','2024-03'].map(period=>({period,year:2024,value:'1',unit:'%',frequency:'monthly',dataType:'level',sourceId:'A'}))
  const before=JSON.stringify(rows)
  assert.equal(data.chartGeometry(rows,'%').segments.length,2)
  assert.equal(JSON.stringify(rows),before)
})

test('monthly aggregate controls validate labels, year, adjacency and year boundary', () => {
  const point=(period,year)=>({period,year,value:'1',unit:'%',frequency:'monthly',dataType:'level',sourceId:'A'})
  for (const [rows,expected] of [
    [[point('2024-01',2024),point('2024-02',2024)],1],
    [[point('2023-12',2023),point('2024-01',2024)],1],
    [[point('2023-12',2023),point('2024-02',2024)],2],
    [[point('2024-00',2024),point('2024-03',2024)],1],
    [[point('2024-13',2024),point('2025-03',2025)],1],
    [[point('2024-01',2023),point('2024-03',2024)],1],
    [[point('2024-1',2024),point('2024-03',2024)],1],
    [[{...point('2024-01',2024),observationDate:'bad'},point('2024-03',2024)],1],
  ]) assert.equal(data.chartGeometry(rows,'%').segments.length,expected,JSON.stringify(rows))
})

test('adjacent regular periods stay connected; daily, adhoc and undated observations do not infer gaps', () => {
  for (const [frequency,dates] of [
    ['monthly',['2024-01-31','2024-02-29']],
    ['quarterly',['2024-03-31','2024-06-30']],
    ['semiannual',['2024-02-29','2024-08-31']],
    ['annual',['2023-12-31','2024-12-31']],
    ['daily',['2024-01-01','2024-02-01']],
    ['adhoc',['2024-01-01','2025-01-01']],
    ['monthly',[undefined,undefined]],
  ]) {
    const chart = data.chartGeometry(dates.map((date,i)=>({...p(date,String(i+1),frequency),...(date?{}:{observationDate:undefined})})),'%')
    assert.equal(chart.segments.length,1,frequency)
    assert.equal(chart.points.length,2,frequency)
  }
})
