// Explicit synthetic DTOs for automated tests only. Never imported by application code.
export const reading = (overrides = {}) => ({
  indicatorCode:'inflasi',indicatorName:'Inflasi UJI SINTETIS',value:'0',unit:'Persen uji',period:'Januari 2000',
  observationDate:'2000-01-31',frequency:'monthly',dataType:'yoy',publicationDate:null,
  validationStatus:'published',reviewedAt:null,
  source:{sourceId:'TEST_ONLY',sourceName:'Publikasi uji sintetis',institution:'INSTANSI UJI SINTETIS',primaryUrl:'https://example.com/test'},
  rawFile:{documentName:'Dokumen uji sintetis',sourceUrl:'https://example.com/test/document',checksumSha256:'a'.repeat(64),retrievedAt:null,periodLabel:'Januari 2000',fileSizeBytes:10,downloadUrl:'/api/indicators/inflasi/raw-file/1/'},
  ...overrides,
})
export const dto = () => ({
  summary:{indicators:[{id:'inflasi',available:true,name:'Inflasi UJI SINTETIS',category:'Kategori uji',value:'0',unit:'Persen uji',period:'Januari 2000',observationDate:'2000-01-31',frequency:'monthly',dataType:'yoy',source:'INSTANSI UJI SINTETIS',sourceId:'TEST_ONLY',publicationDate:null,retrievedAt:null,delta:null,note:'Data uji sintetis, bukan data ekonomi resmi.'}]},
  trend:{id:'inflasi',available:true,unit:'Persen uji',frequency:'monthly',granularity:'Bulanan',points:[{label:'Januari 2000',value:0,unit:'Persen uji',observationDate:'2000-01-31',frequency:'monthly',dataType:'yoy'}]},
  trace:{...reading(),history:[reading()]},
})
export const responder = (payloads, failure = null) => async (input) => {
  const url = new URL(input, 'http://frontend.test')
  const kind = url.pathname.endsWith('/trend/') ? 'trend' : url.pathname.endsWith('/source-trace/') ? 'trace' : 'summary'
  return new Response(JSON.stringify(payloads[kind]),{status:failure === kind ? 503 : 200,headers:{'content-type':'application/json'}})
}
