/** ⚠️ Dev-only Mock Service Worker setup. Imported dynamically, and only when MOCKS_ENABLED. */
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';
import { resetMockDb, scenarios } from './db';

export const worker = setupWorker(...handlers);

export const mockControls = {
  scenarios,
  reset: () => resetMockDb(),
};

declare global {
  interface Window {
    __miraiMock?: typeof mockControls;
  }
}

export async function startMocks(): Promise<void> {
  await worker.start({
    onUnhandledRequest: 'bypass',
    serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
    quiet: true,
  });
  window.__miraiMock = mockControls;
}
