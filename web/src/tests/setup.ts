import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';
import { resetMockDb, scenarios } from '../mocks/db';
import { server } from '../mocks/node';

// jsdom lacks object URLs; images in tests only need a stable fake.
let urlCounter = 0;
if (!('createObjectURL' in URL)) {
  Object.assign(URL, {
    createObjectURL: () => `blob:mock/${++urlCounter}`,
    revokeObjectURL: () => undefined,
  });
}

/**
 * jsdom's AbortSignal is not the one Node's fetch accepts ("Expected signal to
 * be an instance of AbortSignal"). Bridge it: honor aborts ourselves and pass
 * the request on without the foreign signal. Test environment only.
 */
let mswFetch: typeof fetch;
function bridgeAbortSignal() {
  mswFetch = globalThis.fetch;
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const signal = init?.signal;
    if (!signal) return mswFetch(input, init);
    const { signal: _foreign, ...rest } = init;
    const abortError = () => new DOMException('The operation was aborted.', 'AbortError');
    if (signal.aborted) return Promise.reject(abortError());
    return new Promise<Response>((resolve, reject) => {
      const onAbort = () => reject(abortError());
      signal.addEventListener('abort', onAbort, { once: true });
      mswFetch(input, rest).then(resolve, reject).finally(() => signal.removeEventListener('abort', onAbort));
    });
  };
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
  bridgeAbortSignal();
});
beforeEach(() => {
  resetMockDb();
  scenarios.latencyMs = 0;
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
