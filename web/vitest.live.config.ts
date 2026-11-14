/// <reference types="vitest/config" />
/**
 * Smoke test the web app against a real server (Andrew's API, stand-in or live):
 *   LIVE_API_URL=http://127.0.0.1:8000 npm run test:live
 * Real requests, no Mock Service Worker. It picks one subject and never approves anything.
 * A password-protected site (Caddy Basic Auth) needs LIVE_API_AUTH=user:password,
 * which stays in this Node process and is never part of the app bundle.
 */
import { defineConfig, type UserConfig } from 'vite';
import { configDefaults } from 'vitest/config';
import base from './vite.config';

const target = process.env.LIVE_API_URL?.trim() || 'http://127.0.0.1:8000';

export default defineConfig((env) => {
  const cfg = (typeof base === 'function' ? base(env) : base) as UserConfig;
  return {
    ...cfg,
    test: {
      ...cfg.test,
      // Replaced, not merged: the normal run excludes these files.
      include: ['src/tests/live/**/*.live.test.{ts,tsx}'],
      exclude: [...configDefaults.exclude],
      setupFiles: ['./src/tests/live/setup.live.ts'],
      env: { VITE_API_URL: target },
      testTimeout: 20000,
    },
  };
});
