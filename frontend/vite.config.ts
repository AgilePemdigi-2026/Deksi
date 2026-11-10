import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Explicit local reverse proxy keeps public POST CSRF same-origin. No providers or ingestion.
// Default menunjuk backend lokal agar `npm run dev` langsung tersambung
// tanpa harus set env di tiap terminal baru. Override via env bila perlu.
const DEV_API_FALLBACK='http://127.0.0.1:8000'
export default defineConfig(() => {
  const publicTarget=process.env.DEKSI_PUBLIC_API_TARGET ?? DEV_API_FALLBACK
  const authTarget=process.env.DEKSI_AUTH_API_TARGET ?? DEV_API_FALLBACK
  const proxy: Record<string,{target:string;changeOrigin:boolean}>= {}
  if(authTarget)proxy['/api/auth/']={target:authTarget,changeOrigin:false}
  if(publicTarget)proxy['/api/']={target:publicTarget,changeOrigin:false}
  return {plugins:[react()],cacheDir:'.artifacts/vite',server:{host:'127.0.0.1',strictPort:true,proxy}}
})
