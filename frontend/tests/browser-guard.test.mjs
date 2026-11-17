import test from 'node:test'
import assert from 'node:assert/strict'
import { browserHealthFailures } from './browser-guard.mjs'

test('browser health accepts clean console and API responses', () => {
  assert.deepEqual(browserHealthFailures({
    consoleErrors: [],
    responses: [{ url: 'http://127.0.0.1:56120/api/indicators/', status: 200 }],
  }), [])
})

test('browser health reports unexpected console errors', () => {
  const failures = browserHealthFailures({
    consoleErrors: ['Uncaught TypeError: broken'],
    responses: [],
  })
  assert.equal(failures.length, 1)
  assert.match(failures[0], /console.*Uncaught TypeError: broken/i)
})

test('browser health rejects API 5xx responses even when the console is clean', () => {
  const failures = browserHealthFailures({
    consoleErrors: [],
    responses: [
      { url: 'http://127.0.0.1:56120/api/indicators/', status: 503 },
      { url: 'http://127.0.0.1:56120/assets/app.js', status: 503 },
    ],
  })
  assert.equal(failures.length, 1)
  assert.match(failures[0], /503.*\/api\/indicators\//)
})
