export function browserHealthFailures({ consoleErrors = [], responses = [] } = {}) {
  const failures = consoleErrors.map(message => `Unexpected browser console error: ${message}`)
  for (const response of responses) {
    if (response.status < 500 || response.status > 599) continue
    let pathname
    try {
      pathname = new URL(response.url).pathname
    } catch {
      continue
    }
    if (pathname.startsWith('/api/')) {
      failures.push(`API ${response.status}: ${pathname}`)
    }
  }
  return failures
}
