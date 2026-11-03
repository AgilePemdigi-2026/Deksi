import { createServer } from 'vite'
import { fileURLToPath } from 'node:url'

export const root = fileURLToPath(new URL('../../', import.meta.url))
export async function startRecoveryPreview(port = 0) {
  const server = await createServer({
    root, cacheDir:'.artifacts/reset-preview-cache',
    server:{host:'127.0.0.1',port,strictPort:true,headers:{'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Robots-Tag':'noindex, nofollow'}},
    plugins:[{
      name:'test-only-recovery-preview-entry',
      configureServer(app){
        app.middlewares.use((request,_response,next)=>{
          const route=new URL(request.url,'http://127.0.0.1').pathname.replace(/\/+$/,'')
          if(['/admin/login','/admin/forgot-password','/admin/reset-password'].includes(route))request.url='/tests/recovery-preview/index.html'
          next()
        })
      },
    }],
  })
  await server.listen()
  return server
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const server=await startRecoveryPreview(Number(process.env.DEKSI_RESET_PREVIEW_PORT || 62944))
  console.log('SYNTHETIC PREVIEW ONLY: http://127.0.0.1:'+server.httpServer.address().port+'/admin/forgot-password')
  const close=async()=>{await server.close();process.exit(0)}
  process.once('SIGINT',close);process.once('SIGTERM',close)
}
