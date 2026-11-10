import './App.css'
import Dashboard from './features/dashboard/Dashboard'
import LoginPage from './features/admin/LoginPage'
import ForgotPasswordPage from './features/admin/ForgotPasswordPage'
import ResetPasswordPage from './features/admin/ResetPasswordPage'
import type { RecoveryService } from './features/admin/recovery'
import { createRecoveryClient } from './features/admin/recoveryClient'
import { authOrigin } from './features/admin/auth'
import { parseRoute } from './features/indicators/data'
import { DetailScreen, FeatureUnavailable } from './features/indicators/DetailPage'
import { SourceTraceScreen } from './features/indicators/SourceTracePage'
import './features/indicators/features.css'
import { SourceDataPage, type SourcePageSelection } from './components/SourceDataPage'
import { AdminSourcesPage } from './components/AdminSourcesPage'
import { AdminFeedbackPage } from './components/AdminFeedbackPage'

const recoveryClient = createRecoveryClient(authOrigin())

function parseSourceHash(): SourcePageSelection | null {
  if (typeof window === 'undefined') return null
  const hash = window.location.hash || ''
  if (!hash.startsWith('#/sumber-data')) return null
  const query = hash.includes('?') ? hash.split('?')[1] : ''
  const params = new URLSearchParams(query)
  return {
    sourceId: params.get('source') || undefined,
    indicator: params.get('indicator') || undefined,
    period: params.get('period') || undefined,
  }
}

function isAdminHashRoute(): boolean {
  if (typeof window === 'undefined') return false
  return (window.location.hash || '').startsWith('#/admin/sumber')
}

function isAdminFeedbackHashRoute(): boolean {
  if (typeof window === 'undefined') return false
  const hash = window.location.hash || ''
  return hash.startsWith('#/admin/feedback') || hash.startsWith('#/admin/umpan-balik')
}

export default function App({ pathname = typeof window === 'undefined' ? '/' : window.location.pathname, search = typeof window === 'undefined' ? '' : window.location.search, resetService = recoveryClient }: { pathname?: string; search?: string; resetService?: RecoveryService } = {}) {
  const sourceSelection = parseSourceHash()
  if (sourceSelection) return <SourceDataPage selection={sourceSelection} />
  if (isAdminFeedbackHashRoute()) return <AdminFeedbackPage />
  if (isAdminHashRoute()) return <AdminSourcesPage />

  const path = pathname.replace(/\/+$/, '') || '/'
  if (path === '/admin/login') return <LoginPage />
  if (path === '/admin/forgot-password') return <ForgotPasswordPage service={resetService} />
  if (path === '/admin/reset-password') return <ResetPasswordPage service={resetService} />
  if (path === '/sumber-data') {
    const params = new URLSearchParams(search)
    return <SourceDataPage selection={{ sourceId: params.get('source') || undefined, indicator: params.get('indicator') || undefined, period: params.get('period') || undefined }} />
  }
  if (path === '/admin/sumber' || path === '/admin/sumber-data') return <AdminSourcesPage />
  if (path === '/admin/feedback' || path === '/admin/umpan-balik') return <AdminFeedbackPage />
  const route = parseRoute(path, search)
  if (route.kind === 'dashboard') return <Dashboard />
  if (route.kind === 'detail') return <DetailScreen route={route} />
  if (route.kind === 'source') return <SourceTraceScreen route={route} />
  return <FeatureUnavailable />
}
