/**
 * The one place that decides where API calls go.
 *
 * VITE_API_URL
 *   ''              dev  -> Mock Service Worker (mock mode, banner shown)
 *                   prod -> same-origin /api behind Caddy. Mocks NEVER run in a production build.
 *   '/'             same-origin /api, mocks off (dev: pair with API_PROXY_TARGET)
 *   'https://host'  that host's /api ('/api' is appended exactly once by api.ts)
 */
const rawBase = (import.meta.env.VITE_API_URL ?? '').trim();

export const API_BASE: string = rawBase;

/** True only in `vite dev` with no API URL. Tests install their own MSW server instead. */
export const MOCKS_ENABLED: boolean =
  import.meta.env.DEV && import.meta.env.MODE !== 'test' && rawBase === '';

/** Short human description of the API target, for the dev status badge. */
export function describeApiTarget(): string {
  if (MOCKS_ENABLED) return 'Mock data';
  if (rawBase === '' || rawBase === '/') return 'Live API (same origin)';
  return `Live API (${rawBase})`;
}
