import React from 'react'
import { createRoot } from 'react-dom/client'
import SyncHistoryPage from '../src/features/sync-history/SyncHistoryPage'
import '../src/index.css'

const calls = []
window.fixture = { calls }
const loadHistory = (query, { signal }) => new Promise((resolve, reject) => {
  calls.push({ query, signal, resolve, reject })
})
createRoot(document.getElementById('root')).render(<SyncHistoryPage loadHistory={loadHistory} />)
