import React from 'react'
import { createRoot } from 'react-dom/client'
import { AdminSourcesPage } from '../src/components/AdminSourcesPage'

// Actual Admin page; only the backend and provider fixtures are disposable.
createRoot(document.getElementById('root')).render(<AdminSourcesPage />)
