import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The build lands inside FastAPI's /static mount, so `base` has to be the URL
// those files are served from — the SPA renders at /, /login, /app and /admin,
// and relative asset paths would resolve differently on each one.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/static/build/',
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  build: {
    outDir: path.resolve(import.meta.dirname, '../static/build'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:3001',
      '/ws': { target: 'ws://127.0.0.1:3001', ws: true },
    },
  },
})
