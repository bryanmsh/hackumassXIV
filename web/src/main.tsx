import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import '@fontsource/atkinson-hyperlegible/400.css';
import '@fontsource/atkinson-hyperlegible/700.css';
import './index.css';
import { App } from './App';
import { MOCKS_ENABLED } from './config';

async function boot() {
  // Mocks only in `vite dev` with no VITE_API_URL. import.meta.env.DEV is
  // statically false in production builds, so this import is dropped there.
  if (import.meta.env.DEV && MOCKS_ENABLED) {
    const { startMocks } = await import('./mocks/browser');
    await startMocks();
  }
  const root = document.getElementById('root');
  if (!root) throw new Error('Missing #root element');
  createRoot(root).render(
    <StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrictMode>,
  );
}

void boot();
