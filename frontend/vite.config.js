import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite configuration
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,       // dev server port
    // Proxy API requests to FastAPI so we avoid CORS issues in development.
    // Any request starting with /api gets forwarded to http://localhost:8000
    // The frontend code calls /api/auth/login → Vite forwards to FastAPI
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
