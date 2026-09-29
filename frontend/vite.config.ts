import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // Proxy API calls to the backend so CORS isn't an issue in local dev.
    // The frontend fetches /v1/… and Vite forwards them to the FastAPI server.
    proxy: {
      '/v1': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },

  build: {
    // Output to dist/ — Firebase Hosting serves this directory.
    outDir: 'dist',
    sourcemap: true,
  },
});
