import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
const vite = await createServer({ configFile: false, plugins: [react()], cacheDir: '.artifacts/threshold-unit', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const api = await vite.ssrLoadModule('/src/api.ts')

test('validateThresholdInput menolak kosong, non-angka, satuan salah, dan di luar rentang', () => {
  assert.equal(api.validateThresholdInput('', '0', '20', '%', '%'), 'Nilai threshold wajib diisi.')
  assert.equal(api.validateThresholdInput('abc', '0', '20', '%', '%'), 'Nilai threshold harus berupa angka.')
  assert.equal(api.validateThresholdInput('6', 'Rp triliun', '0', '20', '%'), "Satuan harus '%' sesuai definisi parameter.")
  assert.match(api.validateThresholdInput('-10', '0', '20', '%', '%'), /di luar rentang yang diperbolehkan/)
  assert.match(api.validateThresholdInput('25', '0', '20', '%', '%'), /Periksa kembali nilai dan satuan/)
})

test('validateThresholdInput menerima nilai dalam rentang', () => {
  assert.equal(api.validateThresholdInput('6', '0', '20', '%', '%'), null)
  assert.equal(api.validateThresholdInput('0', '0', '20', '%', '%'), null)
  assert.equal(api.validateThresholdInput('20', '0', '20', '%', '%'), null)
})
