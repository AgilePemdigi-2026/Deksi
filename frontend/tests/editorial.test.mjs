import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import react from '@vitejs/plugin-react';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
const server = await createServer({configFile:false,plugins:[react()],server:{middlewareMode:true,hmr:false,ws:false},appType:'custom'});
after(() => server.close());
const load = name => server.ssrLoadModule('/src/' + name);
const render = (Component, props = {}) => renderToStaticMarkup(createElement(Component, props));
const meta = {id:'pdb',category:'Uji',name:'Indikator sintetis',value:'0',unit:'Persen',period:'Q1 2000',delta:'Tidak ada pembanding',deltaDirection:'flat',deltaPositive:false,note:'Data uji sintetis, bukan data resmi.',source:'Instansi uji',sourceDate:'1 Jan 2000',sparkline:[0],sparklineColor:'#111'};
test('A single observed history point never produces NaN SVG coordinates', async () => {
  const { IndicatorCard } = await load('components/IndicatorCard.tsx');
  const html = render(IndicatorCard, {meta});
  assert.doesNotMatch(html, /NaN|Infinity/);
});

test('Missing history is explicit and does not invent a zero sparkline', async () => {
  const { IndicatorCard } = await load('components/IndicatorCard.tsx');
  const html = render(IndicatorCard, {meta:{...meta,sparkline:[]}});
  assert.match(html,/Histori belum tersedia/);
  assert.doesNotMatch(html, /<polyline/);
});

test('API observation date is not presented as an official publication release', async () => {
  const { EconomicSummary } = await load('components/EconomicSummary.tsx');
  const card={id:'pdb',available:true,name:'Indikator sintetis',category:'Uji',value:'0',unit:'Persen',period:'Q1 2000',latestPeriod:'Q1 2000',latestYear:2000,hasCurrentYearData:false,note:'Uji sintetis',source:'Instansi uji',delta:null,deltaDirection:'flat',deltaPositive:false,sparkline:[],observationDate:'2000-01-01'};
  const html=render(EconomicSummary,{cards:[card],loading:false,error:null});
  assert.match(html,/Observasi:/);
  assert.doesNotMatch(html,/Rilis:/);
});

test('The application uses the selected editorial landing, not the old dashboard shell', async () => {
  const { default: App } = await load('App.tsx');
  const html = render(App);
  assert.match(html,/class="hero-photo-wrap"/);
  assert.match(html,/class="segmented-nav"/);
  assert.doesNotMatch(html,/Sumber Terverifikasi/);
});

test('An absent source is not promoted to an official verified source', async () => {
  const { EconomicSummary } = await load('components/EconomicSummary.tsx');
  const card={id:'pdb',available:true,name:'Indikator sintetis',category:'Uji',value:null,unit:'Persen',period:'Q1 2000',note:'Uji sintetis',source:'',delta:null,deltaDirection:'flat',deltaPositive:false,sparkline:[]};
  const html=render(EconomicSummary,{cards:[card],loading:false,error:null});
  assert.match(html,/Sumber belum tersedia/);
  assert.doesNotMatch(html,/Sinkronisasi API Resmi/);
});

test('An empty API response remains an explicit empty state', async () => {
  const { EconomicSummary } = await load('components/EconomicSummary.tsx');
  const html=render(EconomicSummary,{cards:[],loading:false,error:null});
  assert.match(html,/Belum ada indikator/);
  assert.doesNotMatch(html,/class="indicator-card"/);
});

test('The foundation does not ship a dead detail anchor before feature 6 integration', async () => {
  const { IndicatorCard } = await load('components/IndicatorCard.tsx');
  const html=render(IndicatorCard,{meta});
  assert.doesNotMatch(html,/href="#detail"/);
  assert.match(html,/fitur 6/);
});

test('The Admin login route renders a separate account-free-public UI, not the dashboard', async () => {
  const { default: App } = await load('App.tsx');
  const html=render(App,{pathname:'/admin/login'});
  assert.match(html,/Masuk Admin\./);
  assert.match(html,/autocomplete="current-password"/i);
  assert.doesNotMatch(html,/class="summary"/);
});

test('Login validation identifies both missing fields', async () => {
  const { validateLogin } = await load('features/admin/validation.ts');
  assert.deepEqual(JSON.parse(JSON.stringify(validateLogin('', ''))), {identifier:'Masukkan email atau nama pengguna.',password:'Masukkan kata sandi.'});
});

test('Login validation rejects a blank identifier without rewriting password policy', async () => {
  const { validateLogin } = await load('features/admin/validation.ts');
  assert.deepEqual(JSON.parse(JSON.stringify(validateLogin('   ', 'SYNTHETIC-FIXTURE'))),{identifier:'Masukkan email atau nama pengguna.'});
  assert.deepEqual(JSON.parse(JSON.stringify(validateLogin('pengelola.contoh', ''))),{password:'Masukkan kata sandi.'});
});
test('Email/username and short or whitespace passwords are not normalized by UI validation', async () => {
  const { validateLogin } = await load('features/admin/validation.ts');
  for (const id of ['pengelola.contoh','admin@example.test']) for (const pw of ['a',' ','SYNTHETIC-FIXTURE']) assert.deepEqual(JSON.parse(JSON.stringify(validateLogin(id,pw))),{});
});
test('Public footer exposes the real frontend Login Admin route', async () => {
  const { EditorialFooter } = await load('components/EditorialInfo.tsx');
  const html=render(EditorialFooter,{onInfo:()=>{}});
  assert.match(html,/href="\/admin\/login"/);
  assert.doesNotMatch(html,/Admin · fitur 1 menyusul/);
});
