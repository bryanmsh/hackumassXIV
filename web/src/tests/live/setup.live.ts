/** Setup for `npm run test:live`: real HTTP to LIVE_API_URL, no mocks. */
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll } from 'vitest';
import { installTestBridges } from '../fetchBridge';

/**
 * The live site sits behind Caddy Basic Auth. A browser asks for the password
 * itself; this Node test process needs it from LIVE_API_AUTH=user:password.
 * Test-only; never in VITE_ variables or app code.
 */
function addBasicAuth() {
  const auth = process.env.LIVE_API_AUTH;
  if (!auth) return;
  const header = `Basic ${Buffer.from(auth).toString('base64')}`;
  const inner = globalThis.fetch;
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
    inner(input, { ...init, headers: { ...(init?.headers as Record<string, string>), Authorization: header } });
}

beforeAll(() => {
  addBasicAuth();
  installTestBridges();
});
afterEach(() => cleanup());
