import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import net from 'net'

async function isPortFree(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const tester = net
      .createServer()
      .once('error', () => resolve(false))
      .once('listening', () => {
        tester.close(() => resolve(true))
      })
      .listen(port, '0.0.0.0')
  })
}

async function pickPort(start: number, end: number): Promise<number> {
  for (let p = start; p <= end; p++) {
    // eslint-disable-next-line no-await-in-loop
    if (await isPortFree(p)) return p
  }
  throw new Error(`No free port in range ${start}-${end}`)
}

export default defineConfig(async () => {
  const port = await pickPort(5190, 5199)
  return {
    plugins: [
      react()
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: true,
      port,
      strictPort: false,
      proxy: {
        '/api': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
