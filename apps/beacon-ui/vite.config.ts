import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'node:path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    dedupe: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime'],
  },
  server: {
    port: 5177,
    strictPort: true,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // V0: route /api/* requests through installer-backend-proxy
        // which fans out to beacon-control-plane internally.
        target: process.env.VITE_API_URL ?? 'http://localhost:8030',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/beacon/v1'),
      },
    },
  },
  build: {
    target: 'es2022',
    sourcemap: true,
    outDir: 'dist',
    emptyOutDir: true,
  },
});
