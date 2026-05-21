import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Map `@` to the project `src` folder so imports like `@/components` work
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/shared': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/shared/, '/static'),
      },
    },
  },
  build: {
    // Improve code-splitting to avoid a single large bundle
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            const parts = id.split('node_modules/')[1].split('/');
            // Group by top-level package name (scoped packages keep scope)
            const pkg = parts[0].startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
            return `vendor.${pkg}`;
          }
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setupTests.js',
    globals: true,
  },
});
