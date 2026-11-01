import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxy = {
    '/api': {
      target: env.CLASS_PULSE_BACKEND_URL || process.env.CLASS_PULSE_BACKEND_URL || 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  }
  return {
    plugins: [react()],
    server: { proxy: apiProxy },
    preview: { proxy: apiProxy },
  }
})
