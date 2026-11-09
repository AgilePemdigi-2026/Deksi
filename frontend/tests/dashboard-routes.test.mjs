import test, {after} from 'node:test'
import assert from 'node:assert/strict'
import {createServer} from 'vite'
import react from '@vitejs/plugin-react'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
const vite=await createServer({configFile:false,plugins:[react()],cacheDir:'.artifacts/routes-unit',server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'})
after(()=>vite.close())
const {default:App}=await vite.ssrLoadModule('/src/App.tsx')
const source=await vite.ssrLoadModule('/src/features/indicators/source.ts')
const transport=await vite.ssrLoadModule('/src/api.ts')
test('all Sprint1 routes coexist, public root has full donor sections and no invented data',()=>{
 const root=renderToStaticMarkup(createElement(App,{pathname:'/'}))
 for(const id of ['hero','statement','economic-overview','economic-indicators','economic-trend','economic-insights','economic-sources','trust','feedback-section'])assert(root.includes(`id="${id}"`),id)
 assert(!root.includes('5,05%'));assert(!root.includes('2,58%'));assert(!root.includes('4,82%'))
 for(const [path,heading] of [['/admin/login','Masuk Admin.'],['/admin/forgot-password','Lupa kata sandi'],['/admin/reset-password','kata sandi']]){
  const html=renderToStaticMarkup(createElement(App,{pathname:path}));assert(html.toLowerCase().includes(heading.toLowerCase()),path);assert(!html.includes('id="economic-trend"'))
 }
 for(const path of ['/indikator/inflasi','/indikator/inflasi/sumber']){
  const html=renderToStaticMarkup(createElement(App,{pathname:path}));assert(!html.includes('id="economic-overview"'));assert(html.includes('feature-content'))
 }
 const sources=renderToStaticMarkup(createElement(App,{pathname:'/sumber-data'}));assert(sources.includes('Sumber Data'))
 const adminSources=renderToStaticMarkup(createElement(App,{pathname:'/admin/sumber-data'}));assert(adminSources.includes('Kelola Sumber'))
 const unknown=renderToStaticMarkup(createElement(App,{pathname:'/rute-tidak-ada-xyz'}));assert(unknown.includes('Halaman tidak ditemukan'))
})
test('public API and RAW stay same origin, no hardcoded shared test port',()=>{
 assert.equal(transport.API_BASE,'/api')
 assert.equal(source.rawDownloadHref('/api/indicators/pdb/raw-file/4/','pdb'),'/api/indicators/pdb/raw-file/4/')
 assert.equal(source.rawDownloadHref('https://example.test/raw','pdb'),null)
})
