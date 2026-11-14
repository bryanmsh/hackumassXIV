import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';
import { resetMockDb, scenarios } from '../mocks/db';
import { server } from '../mocks/node';
import { installTestBridges } from './fetchBridge';
import './pointerEvents';

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
  installTestBridges();
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
