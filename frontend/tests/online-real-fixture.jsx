import React from 'react'
import { createRoot } from 'react-dom/client'
import ResyncAction from '../src/features/resync/ResyncAction'

// Loaded only by the disposable real-backend browser test after actual test login.
createRoot(document.getElementById('root')).render(<>
  <p>Uji integrasi: provider sintetis, PostgreSQL disposable, bukan data resmi.</p>
  <ResyncAction sourceId="BI" sourceName="BI Uji Integrasi" active supported />
  <ResyncAction sourceId="BKPM" sourceName="BKPM Uji Integrasi" active supported />
  <ResyncAction sourceId="BIS" sourceName="BIS Uji Integrasi" active supported />
  <ResyncAction sourceId="KEMENKEU" sourceName="KEMENKEU Uji Integrasi" active supported />
</>)
