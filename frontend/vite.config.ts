import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import cesium from 'vite-plugin-cesium';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // vite-plugin-cesium: copies Cesium static assets, sets CESIUM_BASE_URL,
    // externalizes 'cesium' → window.Cesium, and injects Cesium.js + widgets.css into HTML
    cesium(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 5000,
    rollupOptions: {
      output: {
        // cesium is externalized by vite-plugin-cesium → do NOT list it here
        manualChunks: {
          react: ['react', 'react-dom'],
          ui: ['framer-motion', 'recharts'],
        },
      },
    },
  },
  // Let Vite pre-bundle everything it can (cesium is external, so this is moot for it)
  optimizeDeps: {
    include: ['resium'],
  },
});
