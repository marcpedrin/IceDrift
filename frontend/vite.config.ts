import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import cesium from 'vite-plugin-cesium';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    cesium(), // Handles Cesium static assets, CESIUM_BASE_URL, Workers
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
    chunkSizeWarningLimit: 5000, // Cesium is large
    rollupOptions: {
      output: {
        manualChunks: {
          cesium: ['cesium'],
          react: ['react', 'react-dom'],
          ui: ['framer-motion', 'recharts'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['cesium', 'resium'],
  },
});
