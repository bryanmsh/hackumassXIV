/** MSW server for Vitest. Same handlers and state as the browser mocks. */
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
