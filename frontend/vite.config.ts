import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Explicit local reverse proxy keeps public POST CSRF same-origin. No providers or ingestion.
export default defineConfig(() => {
  const publicTarget=process.env.DEKSI_PUBLIC_API_TARGET
  const authTarget=process.env.DEKSI_AUTH_API_TARGET
  const proxy: Record<string,{target:string;changeOrigin:boolean}>= {}
  if(authTarget)proxy['/api/auth/']={target:authTarget,changeOrigin:false}
  if(publicTarget)proxy['/api/']={target:publicTarget,changeOrigin:false}
  return {plugins:[react()],cacheDir:'.artifacts/vite',server:{host:'127.0.0.1',strictPort:true,proxy}}
})
