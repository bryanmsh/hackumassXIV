/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite';
import { configDefaults } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// API_PROXY_TARGET (not VITE_-prefixed, so it never reaches the browser) lets
// `npm run dev` forward same-origin /api requests to Andrew's server, e.g. the
// live site behind Caddy. Pair it with VITE_API_URL=/ to turn mocks off.
// API_PROXY_AUTH=user:password adds the site's Basic Auth to proxied requests,
// in the dev server process only; it is never part of the app bundle.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.API_PROXY_TARGET?.trim();
  const proxyAuth = env.API_PROXY_AUTH?.trim();

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: true,
      proxy: proxyTarget
        ? { '/api': { target: proxyTarget, changeOrigin: true, secure: true, ...(proxyAuth ? { auth: proxyAuth } : {}) } }
        : undefined,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/tests/setup.ts'],
      // Live-server smoke tests run only via `npm run test:live`.
      exclude: [...configDefaults.exclude, 'src/tests/live/**'],
      css: false,
      restoreMocks: true,
    },
  };
});
