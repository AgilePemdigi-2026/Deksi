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
import { SourceDataPage } from './components/SourceDataPage'
import { AdminSourcesPage } from './components/AdminSourcesPage'
import './features/indicators/features.css'

const recoveryClient=createRecoveryClient(authOrigin())
export default function App({pathname=typeof window==='undefined'?'/':window.location.pathname,search=typeof window==='undefined'?'':window.location.search,resetService=recoveryClient}:{pathname?:string;search?:string;resetService?:RecoveryService}={}) {
  const path=pathname.replace(/\/+$/,'')||'/'
  if(path==='/admin/login')return <LoginPage/>
  if(path==='/admin/forgot-password')return <ForgotPasswordPage service={resetService}/>
  if(path==='/admin/reset-password')return <ResetPasswordPage service={resetService}/>
  // Fitur 9: halaman daftar sumber data publik.
  if(path==='/sumber-data'){
    const params=new URLSearchParams(search)
    return <SourceDataPage selection={{
      sourceId: params.get('source') || undefined,
      indicator: params.get('indicator') || undefined,
      period: params.get('period') || undefined,
    }}/>
  }
  // Fitur 10: halaman kelola sumber data (Admin, session auth + staf).
  if(path==='/admin/sumber-data' || path==='/admin/sumber')return <AdminSourcesPage/>
  const route=parseRoute(path,search)
  if(route.kind==='dashboard')return <Dashboard/>
  if(route.kind==='detail')return <DetailScreen route={route}/>
  if(route.kind==='source')return <SourceTraceScreen route={route}/>
  return <FeatureUnavailable/>
}
