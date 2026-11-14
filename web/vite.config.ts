/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// API_PROXY_TARGET (not VITE_-prefixed, so it never reaches the browser) lets
// `npm run dev` forward same-origin /api requests to Andrew's server, e.g. the
// live stand-in at hour 3. Pair it with VITE_API_URL=/ to turn mocks off.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.API_PROXY_TARGET?.trim();

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: true,
      proxy: proxyTarget
        ? { '/api': { target: proxyTarget, changeOrigin: true, secure: true } }
        : undefined,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/tests/setup.ts'],
      css: false,
      restoreMocks: true,
    },
  };
});
