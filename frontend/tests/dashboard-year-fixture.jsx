import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import DashboardTrend from '../src/features/dashboard/DashboardTrend'

// Synthetic fetch is installed by the disposable browser runner before import.
export function App() {
  const [year, setYear] = useState('2026')
  return <><button id="select-2025" onClick={() => setYear('2025')}>2025</button>
    <DashboardTrend year={year} allowedCodes={['birate']} /></>
}
createRoot(document.getElementById('root')).render(<App />)
