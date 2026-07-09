import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// =============================================================================
// Vite Configuration
// =============================================================================
//
// HOW VITE CONFIG WORKS:
//   - `plugins`:     Adds React Fast Refresh (hot reload in dev)
//   - `server`:      Development server settings (only used during `npm run dev`)
//   - `server.proxy`: Forwards /api/* requests to FastAPI (avoids CORS in dev)
//   - `build`:       Production build settings (used during `npm run build`)
//   - `define`:      Injects compile-time constants into the bundle
//
// DEVELOPMENT vs PRODUCTION:
//   Development:
//     - `npm run dev` starts Vite at http://localhost:5173
//     - /api/* requests are proxied to http://localhost:8000
//     - No CORS issues because the proxy handles it
//
//   Production:
//     - `npm run build` creates dist/ with optimised static files
//     - No proxy — the built files are served by FastAPI itself (single container)
//     - React calls /api/* directly, which FastAPI handles (same origin = no CORS)
// =============================================================================

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // Proxy API requests to FastAPI so we avoid CORS issues in development.
    // Any request starting with /api gets forwarded to http://localhost:8000
    // Example: fetch('/api/auth/login') → FastAPI at localhost:8000/auth/login
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Strip the /api prefix: /api/auth/login → /auth/login
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },

  build: {
    // Output directory for production build
    outDir: 'dist',

    // Generate source maps for production debugging (optional — disable for smaller builds)
    sourcemap: false,

    // Chunk size warning limit (in kB)
    // Our bundles are expected to be ~300kB with React + Router + dependencies
    chunkSizeWarningLimit: 600,

    rollupOptions: {
      output: {
        // Split vendor dependencies into a separate chunk
        // This improves caching: app code changes more often than vendor libs
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui:     ['axios', 'react-hot-toast', 'lucide-react'],
        },
      },
    },
  },
})
