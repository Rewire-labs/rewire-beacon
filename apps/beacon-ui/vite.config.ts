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
      '/v1': {
        // FE-MESSAGING-05: proxy /v1/* to the control-plane in local dev.
        // Set VITE_MESSAGING_URL (empty string = use proxy) or override target.
        target: process.env.VITE_API_URL ?? 'http://localhost:8030',
        changeOrigin: true,
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
